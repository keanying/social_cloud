"""首页解析需登录 + 一键下载中转。"""
import os
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from werkzeug.security import generate_password_hash

from app import create_app
from src.api.access import rate_limiter
from src.db import get_db

VIDEO_URL = "https://cdn.example.com/media/video.mp4"
IMAGE_URL = "https://cdn.example.com/media/cover.jpg"
PUBLIC_ADDRINFO = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


def fake_parser():
    parser = Mock()
    parser.terminal_error = None
    parser.no_media_in_content = False
    parser.cookie_required = False
    parser.get_title_content.return_value = "海边日落"
    parser.get_description.return_value = None
    parser.get_real_video_url.return_value = VIDEO_URL
    parser.get_video_list.return_value = []
    parser.get_image_list.return_value = [IMAGE_URL]
    parser.get_cover_photo_url.return_value = IMAGE_URL
    parser.get_author_info.return_value = {"nickname": "阿木"}
    parser.get_audio_url.return_value = None
    parser.get_subtitles.return_value = None
    return parser


class FakeUpstream:
    def __init__(self, status=200, body=b"video-bytes", headers=None):
        self.status_code = status
        self.headers = {"Content-Type": "video/mp4", "Content-Length": str(len(body))}
        self.headers.update(headers or {})
        self.is_redirect = False
        self._body = body

    def iter_content(self, _size):
        yield self._body

    def close(self):
        pass


class LoginRequiredParseTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": os.path.join(self.temp_dir.name, "test.db"),
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            rate_limiter.reset()
            db = get_db()
            db.execute(
                "INSERT INTO users(username, password_hash, role, qps_limit, created_at) VALUES (?, ?, 'user', 2, '2026-01-01')",
                ("amu", generate_password_hash("secret-123")),
            )
            db.commit()
            self.user_id = db.execute("SELECT id FROM users WHERE username='amu'").fetchone()["id"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

    def parse(self):
        with patch("src.api.parse.WebFetcher.fetch_redirect_url", return_value="https://www.douyin.com/video/1"), \
                patch("src.api.parse.ParserFactory.create_parser", return_value=fake_parser()):
            return self.client.post("/api/parse", json={"text": "https://v.douyin.com/abc/"})

    # ---- 解析需登录 ----
    def test_anonymous_parse_requires_login(self):
        response = self.parse()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error_code"], "LOGIN_REQUIRED")

    def test_logged_in_parse_succeeds_and_grants_media(self):
        self.login()
        response = self.parse()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["video_url"], VIDEO_URL)
        with self.app.app_context():
            urls = {r["url"] for r in get_db().execute("SELECT url FROM media_grants WHERE user_id=?", (self.user_id,))}
        self.assertEqual(urls, {VIDEO_URL, IMAGE_URL})

    def test_page_parse_does_not_consume_credits(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET credits = 10 WHERE id = ?", (self.user_id,))
            db.commit()
        self.login()
        self.assertEqual(self.parse().status_code, 200)
        self.assertEqual(self.parse().status_code, 200)
        with self.app.app_context():
            credits = get_db().execute("SELECT credits FROM users WHERE id = ?", (self.user_id,)).fetchone()["credits"]
        self.assertEqual(credits, 10)

    def test_login_requirement_can_be_disabled(self):
        with patch("src.api.parse.demo_login_required", return_value=False):
            response = self.parse()
        self.assertEqual(response.status_code, 200)

    # ---- 一键下载 ----
    def test_download_requires_login(self):
        response = self.client.get("/api/download", query_string={"url": VIDEO_URL})
        self.assertEqual(response.status_code, 401)

    def test_download_rejects_urls_not_from_own_parse(self):
        self.login()
        response = self.client.get("/api/download", query_string={"url": "https://evil.example.com/a.mp4"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error_code"], "DOWNLOAD_EXPIRED")

    def test_download_streams_granted_media_as_attachment(self):
        self.login()
        self.parse()
        with patch("src.api.download.socket.getaddrinfo", return_value=PUBLIC_ADDRINFO), \
                patch("src.api.download.requests.Session.get", return_value=FakeUpstream()) as upstream:
            response = self.client.get("/api/download", query_string={"url": VIDEO_URL, "name": "海边日落"})
            body = response.get_data()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body, b"video-bytes")
        disposition = response.headers["Content-Disposition"]
        self.assertIn("attachment", disposition)
        self.assertIn("filename*=UTF-8''%E6%B5%B7%E8%BE%B9%E6%97%A5%E8%90%BD.mp4", disposition)
        self.assertFalse(upstream.call_args.kwargs["allow_redirects"])

    def test_download_check_validates_grant_without_upstream(self):
        self.login()
        self.parse()
        with patch("src.api.download.requests.Session.get") as upstream:
            ok = self.client.get("/api/download", query_string={"url": VIDEO_URL, "check": "1"})
            missing = self.client.get("/api/download", query_string={"url": "https://x.example.com/a.mp4", "check": "1"})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.get_json()["succ"])
        self.assertEqual(missing.status_code, 403)
        upstream.assert_not_called()

    def test_download_blocks_private_network_targets(self):
        self.login()
        self.parse()
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))]
        with patch("src.api.download.socket.getaddrinfo", return_value=private), \
                patch("src.api.download.requests.Session.get") as upstream:
            response = self.client.get("/api/download", query_string={"url": VIDEO_URL})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error_code"], "DOWNLOAD_FORBIDDEN")
        upstream.assert_not_called()

    def test_download_rechecks_redirect_targets(self):
        self.login()
        self.parse()
        redirect = FakeUpstream(status=302, headers={"Location": "http://169.254.169.254/latest/meta-data"})
        redirect.is_redirect = True

        def resolve(host, *_args, **_kwargs):
            ip = "169.254.169.254" if host == "169.254.169.254" else "93.184.216.34"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

        with patch("src.api.download.socket.getaddrinfo", side_effect=resolve), \
                patch("src.api.download.requests.Session.get", return_value=redirect):
            response = self.client.get("/api/download", query_string={"url": VIDEO_URL})
        self.assertEqual(response.status_code, 403)

    # ---- 本页播放（内联中转） ----
    def test_media_requires_login(self):
        response = self.client.get("/api/media", query_string={"url": VIDEO_URL})
        self.assertEqual(response.status_code, 401)

    def test_media_passes_range_for_seeking(self):
        self.login()
        self.parse()
        partial = FakeUpstream(status=206, body=b"part", headers={"Content-Range": "bytes 0-3/100", "Accept-Ranges": "bytes"})
        with patch("src.api.download.socket.getaddrinfo", return_value=PUBLIC_ADDRINFO), \
                patch("src.api.download.requests.Session.get", return_value=partial) as upstream:
            response = self.client.get("/api/media", query_string={"url": VIDEO_URL}, headers={"Range": "bytes=0-3"})
            body = response.get_data()
        self.assertEqual(response.status_code, 206)
        self.assertEqual(body, b"part")
        self.assertEqual(response.headers["Content-Range"], "bytes 0-3/100")
        self.assertNotIn("Content-Disposition", response.headers)
        self.assertEqual(upstream.call_args.kwargs["headers"]["Range"], "bytes=0-3")
        self.assertIn("sandbox", response.headers["Content-Security-Policy"])

    def test_media_never_serves_html_inline(self):
        self.login()
        self.parse()
        html = FakeUpstream(body=b"<script>alert(1)</script>", headers={"Content-Type": "text/html"})
        with patch("src.api.download.socket.getaddrinfo", return_value=PUBLIC_ADDRINFO), \
                patch("src.api.download.requests.Session.get", return_value=html):
            response = self.client.get("/api/media", query_string={"url": VIDEO_URL})
        self.assertEqual(response.mimetype, "application/octet-stream")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    # ---- 首页登录弹窗的 JSON 登录 ----
    def test_fetch_login_returns_json(self):
        self.client.get("/auth/login")
        with self.client.session_transaction() as sess:
            token = sess["csrf_token"]
        headers = {"X-Requested-With": "fetch"}
        bad = self.client.post("/auth/login", data={"csrf_token": token, "username": "amu", "password": "wrong"}, headers=headers)
        self.assertEqual(bad.status_code, 401)
        self.assertFalse(bad.get_json()["ok"])
        ok = self.client.post("/auth/login", data={"csrf_token": token, "username": "amu", "password": "secret-123"}, headers=headers)
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.get_json()["ok"])
        self.assertEqual(self.parse().status_code, 200)


if __name__ == "__main__":
    unittest.main()
