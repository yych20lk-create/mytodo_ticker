#!/usr/bin/env bash
# ZenTray 脚本公共库（被其他 scripts 源入）
# shellcheck disable=SC2034

set -euo pipefail

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_NAME="ZenTray"
PKG_NAME="zentray"   # deb 包名（小写）

# 用户级安装 / 数据路径（与 installer + config 对齐）
USER_INSTALL_DIR="${HOME}/.local/bin/${APP_NAME}"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/${APP_NAME}"
USER_DATA_DIR_LEGACY="${XDG_DATA_HOME:-$HOME/.local/share}/zentray"
USER_AUTOSTART="${HOME}/.config/autostart/${APP_NAME}.desktop"
USER_DESKTOP_FILE=""
# 桌面目录（兼容中文「桌面」）
for d in "${HOME}/Desktop" "${HOME}/桌面"; do
    if [[ -d "$d" ]]; then
        USER_DESKTOP_FILE="${d}/${APP_NAME}.desktop"
        break
    fi
done
USER_APPS_DESKTOP="${HOME}/.local/share/applications/${APP_NAME}.desktop"
USER_APPS_DESKTOP_LC="${HOME}/.local/share/applications/${PKG_NAME}.desktop"

# deb 系统路径（packaging 约定）
DEB_OPT_DIR="/opt/${PKG_NAME}"
DEB_BIN_LINK="/usr/bin/${PKG_NAME}"
DEB_DESKTOP="/usr/share/applications/${PKG_NAME}.desktop"
DEB_ICON_DIR="/usr/share/icons/hicolor/256x256/apps"

section() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━ $1 ━━━${NC}"
}

info()  { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}→${NC} $*"; }
err()   { echo -e "  ${RED}✗${NC} $*" >&2; }

get_version() {
    local py="${PROJECT_DIR}/venv/bin/python"
    if [[ -x "$py" ]]; then
        "$py" -c "from zentray.config import VERSION; print(VERSION)" 2>/dev/null && return
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:$PYTHONPATH}" \
            python3 -c "from zentray.config import VERSION; print(VERSION)" 2>/dev/null && return
    fi
    echo "0.0.0"
}

is_deb_installed() {
    dpkg -s "$PKG_NAME" &>/dev/null
}

kill_app_processes() {
    # 结束主程序 / 安装器 / 托盘桥（忽略失败）
    pkill -f "[Zz]enTray" 2>/dev/null || true
    pkill -f "linux_tray_bridge" 2>/dev/null || true
    pkill -f "zentray/main.py" 2>/dev/null || true
    sleep 0.3
}
