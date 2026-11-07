"""跨平台启动入口。

- Linux / macOS：使用 gunicorn（多 worker，与 Docker 镜像一致）
- Windows：gunicorn 不支持 Windows，改用 waitress（纯 Python 的生产级 WSGI 服务器）

环境变量：
    WEB_HOST  监听地址，默认 0.0.0.0
    WEB_PORT  监听端口，默认 8051
"""
import os
import sys


def main():
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8051"))
    print(f"[media-parser] listening on http://{host}:{port}/ ({sys.platform})", flush=True)

    if os.name == "nt":
        from waitress import serve
        from app import app

        serve(app, host=host, port=port, threads=8)
        return

    args = [
        sys.executable, "-m", "gunicorn",
        "--workers", os.getenv("WEB_WORKERS", "2"),
        "--threads", "4",
        "--worker-class", "gthread",
        "--timeout", "120",
        "--keep-alive", "5",
        "--bind", f"{host}:{port}",
        "app:app",
    ]
    os.execv(sys.executable, args)


if __name__ == "__main__":
    main()
