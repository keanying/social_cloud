"""一键下载：由服务端中转媒体文件并以附件形式返回。

平台 CDN 普遍有防盗链和跨域限制，浏览器无法直接以 `download` 方式保存，因此由服务端中转。
为避免中转接口被滥用为 SSRF 跳板：
- 只允许下载「当前登录用户」在近期解析结果中得到的地址（media_grants 表，2 小时有效）；
- 每一跳（含重定向）都会校验目标主机解析出的 IP 必须是公网地址；
- 单个文件有大小上限，超过即中断。
"""
import ipaddress
import mimetypes
import os
import re
import socket
import time
from urllib.parse import quote, urljoin, urlparse

import requests
from flask import Response, g, request, stream_with_context

from configs.logging_config import get_logger
from src.api.response import make_response
from src.db import get_db

logger = get_logger(__name__)

GRANT_TTL_SECONDS = 2 * 3600
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_DOWNLOAD_BYTES", str(1024 ** 3)))
MAX_REDIRECTS = 5
CHUNK_SIZE = 64 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# 部分 CDN 校验 Referer，按主机关键字补充来源页
REFERER_RULES = (
    (("bilivideo", "hdslb", "bilibili", "akamaized"), "https://www.bilibili.com/"),
    (("xhscdn", "xiaohongshu"), "https://www.xiaohongshu.com/"),
    (("douyin", "byteimg", "douyinvod", "douyinpic", "zjcdn"), "https://www.douyin.com/"),
    (("kuaishou", "yximgs", "kwimgs", "kwaicdn"), "https://www.kuaishou.com/"),
    (("sinaimg", "weibocdn", "weibo"), "https://weibo.com/"),
)


def _error(status, message, code):
    return make_response(status, message, None, False, code), status


class DownloadRejected(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def collect_media_urls(data):
    """从解析结果中提取可下载的媒体地址。"""
    urls = []
    for key in ("video_url", "audio_url", "cover_url"):
        if data.get(key):
            urls.append(data[key])
    urls.extend(data.get("video_list") or [])
    for item in data.get("image_list") or []:
        if isinstance(item, dict):
            urls.extend(u for u in (item.get("url"), item.get("live_photo_url")) if u)
        elif item:
            urls.append(item)
    return [u for u in dict.fromkeys(urls) if isinstance(u, str) and u.lower().startswith(("http://", "https://"))]


def grant_media_urls(user_id, data):
    """记录用户本次解析得到的地址，供后续下载校验。失败不影响解析结果。"""
    urls = collect_media_urls(data)
    if not user_id or not urls:
        return
    now = time.time()
    db = get_db()
    db.execute("DELETE FROM media_grants WHERE expires_at < ?", (now,))
    db.executemany(
        "INSERT OR REPLACE INTO media_grants(user_id, url, platform, expires_at) VALUES (?, ?, ?, ?)",
        [(user_id, url, data.get("platform"), now + GRANT_TTL_SECONDS) for url in urls],
    )
    db.commit()


def _is_granted(user_id, url):
    row = get_db().execute(
        "SELECT 1 FROM media_grants WHERE user_id = ? AND url = ? AND expires_at >= ?",
        (user_id, url, time.time()),
    ).fetchone()
    return row is not None


def _assert_public_host(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise DownloadRejected(400, "INVALID_URL", "下载地址无效")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        raise DownloadRejected(502, "DOWNLOAD_FAILED", "无法连接到资源服务器，请稍后重试")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise DownloadRejected(403, "DOWNLOAD_FORBIDDEN", "该地址不允许下载")


def _referer_for(url):
    host = (urlparse(url).hostname or "").lower()
    for keywords, referer in REFERER_RULES:
        if any(k in host for k in keywords):
            return referer
    return None


def _open_upstream(url):
    """逐跳跟随重定向，每一跳都做公网校验。"""
    session = requests.Session()
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        _assert_public_host(current)
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        referer = _referer_for(current)
        if referer:
            headers["Referer"] = referer
        resp = session.get(current, headers=headers, stream=True, allow_redirects=False, timeout=(6, 30))
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                break
            current = urljoin(current, location)
            continue
        return session, resp
    session.close()
    raise DownloadRejected(502, "DOWNLOAD_FAILED", "资源地址跳转次数过多")


_SAFE_NAME = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _filename(name, url, content_type):
    base = _SAFE_NAME.sub(" ", (name or "").strip())[:80].strip() or "社媒云下载"
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if not re.fullmatch(r"\.[a-z0-9]{2,5}", ext or ""):
        ext = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ""
    if ext == ".jpe":
        ext = ".jpg"
    return base if base.lower().endswith(ext) else base + ext


def download():
    user = g.get("user")
    if user is None:
        return _error(401, "请先登录后再下载", "LOGIN_REQUIRED")
    url = (request.args.get("url") or "").strip()
    if not url or len(url) > 4096:
        return _error(400, "缺少下载地址", "INVALID_URL")
    if not _is_granted(user["id"], url):
        return _error(403, "下载链接已过期，请重新解析后再下载", "DOWNLOAD_EXPIRED")
    if request.args.get("check") == "1":
        # 前端预检：只校验登录与授权，不访问上游，便于给出明确提示
        return make_response(200, "可以下载", None, True), 200

    try:
        session, upstream = _open_upstream(url)
    except DownloadRejected as exc:
        return _error(exc.status, exc.message, exc.code)
    except requests.RequestException:
        logger.warning("下载中转连接失败")
        return _error(502, "资源服务器暂时无法访问，请稍后重试", "DOWNLOAD_FAILED")

    if upstream.status_code >= 400:
        upstream.close(); session.close()
        return _error(502, "资源已失效或被平台拒绝，请重新解析后再试", "DOWNLOAD_FAILED")
    length = upstream.headers.get("Content-Length")
    if length and length.isdigit() and int(length) > MAX_DOWNLOAD_BYTES:
        upstream.close(); session.close()
        return _error(413, "文件过大，请复制链接后自行下载", "DOWNLOAD_TOO_LARGE")

    content_type = upstream.headers.get("Content-Type") or "application/octet-stream"
    filename = _filename(request.args.get("name"), url, content_type)

    def generate():
        sent = 0
        try:
            for chunk in upstream.iter_content(CHUNK_SIZE):
                sent += len(chunk)
                if sent > MAX_DOWNLOAD_BYTES:
                    break
                yield chunk
        finally:
            upstream.close()
            session.close()

    headers = {
        "Content-Disposition": f"attachment; filename=\"download{os.path.splitext(filename)[1]}\"; filename*=UTF-8''{quote(filename)}",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if length and length.isdigit():
        headers["Content-Length"] = length
    return Response(stream_with_context(generate()), status=200, headers=headers, content_type=content_type)
