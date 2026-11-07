"""跨平台（Windows / Linux / macOS）启动验证脚本，只依赖标准库。

用法：
    python scripts/verify.py --spawn            # 用临时数据库自动启动服务并验证，结束后关闭
    python scripts/verify.py --url http://127.0.0.1:8051   # 验证一个已经在运行的服务

只访问本机服务，不会向任何外部平台发起解析请求。
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def request(base, path, method="GET", body=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")


def check_json(expected_status, expected):
    def _check(status, text):
        if status != expected_status:
            return f"HTTP {status}, 期望 {expected_status}"
        payload = json.loads(text)
        for key, value in expected.items():
            if payload.get(key) != value:
                return f"{key}={payload.get(key)!r}, 期望 {value!r}"
        return None
    return _check


def check_html(marker):
    def _check(status, text):
        if status != 200:
            return f"HTTP {status}, 期望 200"
        if marker not in text:
            return f"页面中未找到 {marker!r}"
        return None
    return _check


CHECKS = [
    ("健康检查 /api/health", "GET", "/api/health", None, check_json(200, {"status": "ok"})),
    ("首页 /", "GET", "/", None, check_html("<html")),
    ("管理员初始化页 /auth/setup", "GET", "/auth/setup", None, check_html("<form")),
    ("登录页 /auth/login", "GET", "/auth/login", None, check_html("<form")),
    ("注册页 /auth/register", "GET", "/auth/register", None, check_html("<html")),
    ("静态资源 /static/css/console.css", "GET", "/static/css/console.css", None,
     lambda s, t: None if s == 200 else f"HTTP {s}"),
    ("API 未带 Key 时拒绝", "GET", "/api/v1/parse?url=https://example.com", None,
     check_json(401, {"error_code": "API_KEY_REQUIRED", "succ": False})),
    ("首页解析未登录时要求登录", "POST", "/api/parse", {"text": "https://v.douyin.com/abc/"},
     check_json(401, {"error_code": "LOGIN_REQUIRED", "succ": False})),
    ("一键下载未登录时要求登录", "GET", "/api/download?url=https://example.com/a.mp4", None,
     check_json(401, {"error_code": "LOGIN_REQUIRED", "succ": False})),
]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(base, proc, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"服务进程提前退出，退出码 {proc.returncode}")
        try:
            status, _ = request(base, "/api/health")
            if status == 200:
                return
        except (urllib.error.URLError, ConnectionError, socket.timeout):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{timeout}s 内服务未就绪")


def spawn_server(port, data_dir):
    env = dict(os.environ)
    env.update({
        "WEB_HOST": "127.0.0.1",
        "WEB_PORT": str(port),
        "WEB_WORKERS": "1",
        "DATABASE_PATH": os.path.join(data_dir, "verify.db"),
        "API_ONLY": "false",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    })
    return subprocess.Popen([sys.executable, os.path.join(ROOT, "run.py")], cwd=ROOT, env=env)


def stop_server(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="已运行服务的地址，例如 http://127.0.0.1:8051")
    parser.add_argument("--spawn", action="store_true", help="自动用临时数据库启动服务后再验证")
    args = parser.parse_args()
    if not args.url and not args.spawn:
        args.spawn = True

    proc = None
    tmp = None
    if args.spawn:
        tmp = tempfile.TemporaryDirectory(prefix="media-parser-verify-", ignore_cleanup_errors=True)
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        print(f"[verify] 启动服务: {base} (平台: {sys.platform}, Python {sys.version.split()[0]})")
        proc = spawn_server(port, tmp.name)
    else:
        base = args.url.rstrip("/")

    failures = 0
    try:
        wait_ready(base, proc)
        for name, method, path, body, check in CHECKS:
            try:
                status, text = request(base, path, method, body)
                problem = check(status, text)
            except Exception as exc:  # noqa: BLE001 - 报告任何失败原因
                problem = f"{type(exc).__name__}: {exc}"
            mark = "PASS" if problem is None else "FAIL"
            print(f"  [{mark}] {name}" + ("" if problem is None else f" -> {problem}"))
            failures += problem is not None
    except RuntimeError as exc:
        print(f"[verify] 失败: {exc}")
        failures += 1
    finally:
        if proc is not None:
            stop_server(proc)
        if tmp is not None:
            tmp.cleanup()

    total = len(CHECKS)
    print(f"[verify] {'全部通过' if failures == 0 else f'{failures} 项失败'} ({total} 项检查)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
