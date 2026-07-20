#!/usr/bin/env bash
# ============================================================================
# ZenTray 用户配置 / 缓存清理脚本
#
# 清理内容（不卸载二进制本身）:
#   - 用户数据目录 ~/.local/share/ZenTray
#     （active_tasks.json、settings.json、archive、icons、reviews、.env、.setup_done…）
#   - 历史小写目录 ~/.local/share/zentray
#   - 开发态项目内 zentray.log / dist 下日志（可选）
#
# 用法:
#   ./scripts/clean_config.sh           # 交互确认后清理
#   ./scripts/clean_config.sh --yes     # 跳过确认
#   ./scripts/clean_config.sh --dry-run # 只列出将删除的路径
#   ./scripts/clean_config.sh -h
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_common.sh
source "${SCRIPT_DIR}/lib_common.sh"

YES=false
DRY_RUN=false
ALSO_DEV_LOGS=false

usage() {
    cat <<EOF
用法: $0 [选项]

清理 ZenTray 用户配置与缓存（任务、设置、图标缓存等）。
不会卸载已安装的 deb / 可执行文件。

选项:
  --yes, -y       跳过确认
  --dry-run       只打印将删除的路径
  --dev-logs      同时清理项目内 dist/zentray.log 等开发日志
  -h, --help      显示帮助

示例:
  # 测完安装流程后重置「首次向导 / 空任务」状态
  ./scripts/clean_config.sh --yes

  # 完全重装测试
  ./scripts/uninstall.sh --yes
  ./scripts/clean_config.sh --yes
  sudo apt install -y ./dist/releases/zentray_*_amd64.deb
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y) YES=true ;;
        --dry-run) DRY_RUN=true ;;
        --dev-logs) ALSO_DEV_LOGS=true ;;
        -h|--help) usage; exit 0 ;;
        *) err "未知选项: $1"; usage; exit 1 ;;
    esac
    shift
done

# 待清理路径列表
TARGETS=(
    "$USER_DATA_DIR"
    "$USER_DATA_DIR_LEGACY"
)

if $ALSO_DEV_LOGS; then
    TARGETS+=(
        "${PROJECT_DIR}/dist/zentray.log"
        "${PROJECT_DIR}/zentray.log"
        "${PROJECT_DIR}/zentray/zentray.log"
    )
fi

section "ZenTray 配置/缓存清理"
echo "  将处理:"
for t in "${TARGETS[@]}"; do
    if [[ -e "$t" ]]; then
        echo -e "    ${YELLOW}存在${NC}  $t"
    else
        echo -e "    ${CYAN}无${NC}    $t"
    fi
done

if $DRY_RUN; then
    section "dry-run：未删除任何文件"
    exit 0
fi

if ! $YES; then
    echo ""
    read -r -p "确认删除以上已存在路径? [y/N] " ans
    case "$ans" in
        y|Y|yes|YES) ;;
        *) echo "已取消"; exit 0 ;;
    esac
fi

# 清理前可结束进程，避免占用文件
kill_app_processes || true

section "删除"
for t in "${TARGETS[@]}"; do
    if [[ -e "$t" ]]; then
        rm -rf "$t"
        info "已删除 $t"
    else
        warn "跳过（不存在）$t"
    fi
done

section "清理完成"
echo ""
echo "  下次启动将："
echo "    • 使用空任务列表"
echo "    • 重新弹出首次配置向导（无 settings.json / .setup_done）"
echo "    • 重新同步图标到数据目录"
echo ""
