#!/usr/bin/env bash
# Linux / macOS 一键启动与验证
#   ./scripts/start.sh          创建 .venv、安装依赖并启动服务（默认端口 8051）
#   ./scripts/start.sh verify   运行单元测试 + 启动验证
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
if [ ! -x ".venv/bin/python" ]; then
    echo "[setup] 创建虚拟环境 .venv ..."
    "$PY" -m venv .venv
fi
echo "[setup] 安装依赖 ..."
.venv/bin/python -m pip install -q -r requirements.txt

if [ "${1:-}" = "verify" ]; then
    .venv/bin/python -m pip install -q pytest
    echo "[verify] 运行单元测试 ..."
    .venv/bin/python -m pytest -q
    echo "[verify] 启动验证 ..."
    exec .venv/bin/python scripts/verify.py --spawn
fi

exec .venv/bin/python run.py
