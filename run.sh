#!/bin/bash
# ZenTray 开发态快速启动

set -euo pipefail
cd "$(dirname "$0")"

if [ -f ".env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env | xargs) || true
fi

if [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "未找到 Python3，请先安装。"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "初始化虚拟环境..."
    "$PYTHON_CMD" -m venv venv
    # shellcheck disable=SC1091
    source venv/bin/activate
    echo "安装依赖..."
    pip install -e ".[dev]"
else
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

echo "清理旧进程..."
pkill -f "zentray/main.py" 2>/dev/null || true
pkill -f "[Zz]enTray" 2>/dev/null || true
pkill -f "linux_tray_bridge.py" 2>/dev/null || true
sleep 0.3

echo "启动 ZenTray..."
exec venv/bin/python zentray/main.py
