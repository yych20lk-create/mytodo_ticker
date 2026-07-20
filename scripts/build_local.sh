#!/usr/bin/env bash
# ============================================================================
# ZenTray 本地构建脚本
#
# 用法:
#   ./scripts/build_local.sh           # 仅构建
#   ./scripts/build_local.sh --run     # 构建 + 立即运行测试
#   ./scripts/build_local.sh --clean   # 清理旧构建产物后重新构建
#   ./scripts/build_local.sh -h        # 帮助
# ============================================================================
set -euo pipefail

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---- 路径 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"
RELEASES_DIR="$DIST_DIR/releases"
SPEC_FILE="$PROJECT_DIR/zentray.spec"
INSTALLER_SPEC="$PROJECT_DIR/installer.spec"
APP_BINARY="$DIST_DIR/ZenTray"
INSTALLER_BINARY="$DIST_DIR/ZenTrayInstaller"

# ---- 选项 ----
CLEAN=false
RUN_AFTER=false
BUILD_INSTALLER=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean) CLEAN=true ;;
        --run)   RUN_AFTER=true ;;
        --installer) BUILD_INSTALLER=true ;;
        -h|--help)
            echo "用法: $0 [--clean] [--run] [--installer]"
            echo ""
            echo "  --clean      清理旧构建产物后重新构建"
            echo "  --run        构建完成后立即运行应用"
            echo "  --installer  同时构建安装器（需先构建主应用）"
            echo ""
            echo "  (默认只构建主应用，不清除缓存，不运行)"
            exit 0
            ;;
        *) echo -e "${RED}未知选项: $1${NC}"; exit 1 ;;
    esac
    shift
done

# ---- 打印带标题的分隔线 ----
section() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━ $1 ━━━${NC}"
}

# ---- 进入项目目录 ----
cd "$PROJECT_DIR"

# ---- 检查 venv ----
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo -e "${RED}✗ 未找到虚拟环境: $VENV_PYTHON${NC}"
    echo "  请先运行: python3 -m venv venv && venv/bin/pip install -e '.[dev]' pyinstaller"
    exit 1
fi

# ========================================================================
# 1. 清理（可选）
# ========================================================================
if $CLEAN; then
    section "清理旧构建产物"
    echo -e "${YELLOW}  → 删除 build/ ...${NC}"
    rm -rf "$BUILD_DIR"
    echo -e "${YELLOW}  → 删除 dist/ZenTray ...${NC}"
    rm -f "$APP_BINARY"
    echo -e "${YELLOW}  → 删除 dist/releases/ ...${NC}"
    rm -rf "$RELEASES_DIR"
    echo -e "${GREEN}  ✓ 清理完成${NC}"
fi

# ========================================================================
# 2. 读取版本号
# ========================================================================
section "读取版本信息"
VERSION=$("$VENV_PYTHON" -c "from zentray.config import VERSION; print(VERSION)" 2>/dev/null) || VERSION="unknown"
echo -e "  版本: ${GREEN}v${VERSION}${NC}"

# ========================================================================
# 3. 语法检查
# ========================================================================
section "语法检查"
ERRORS=0
for pyfile in $(find "$PROJECT_DIR/zentray" -name "*.py" -not -path "*/__pycache__/*"); do
    if ! "$VENV_PYTHON" -m py_compile "$pyfile" 2>/dev/null; then
        echo -e "  ${RED}✗ $pyfile${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
if [[ $ERRORS -eq 0 ]]; then
    echo -e "  ${GREEN}✓ 全部文件语法正确${NC}"
else
    echo -e "  ${RED}✗ $ERRORS 个文件语法错误，请修复后重试${NC}"
    exit 1
fi

# ========================================================================
# 4. 确保图标资源存在
# ========================================================================
section "检查图标资源"
ICON_DIR="$PROJECT_DIR/resources/icons"
if [[ ! -f "$ICON_DIR/app_icon.png" ]]; then
    echo -e "  ${YELLOW}→ 生成默认图标...${NC}"
    "$VENV_PYTHON" -c "
import struct, zlib, os, math
os.makedirs('$ICON_DIR', exist_ok=True)
size = 32
def make_png(path, r, g, b):
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>I', 13) + b'IHDR' + struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    ihdr += struct.pack('>I', zlib.crc32(ihdr[4:]))
    cx = cy = size // 2; radius = size // 2 - 2
    raw = b''
    for y in range(size):
        raw += b'\x00'
        for x in range(size):
            d = math.sqrt((x-cx)**2 + (y-cy)**2)
            raw += bytes([r,g,b,255]) if d <= radius else bytes([0,0,0,0])
    compressed = zlib.compress(raw)
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT'+compressed))
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND'))
    with open(path, 'wb') as f: f.write(sig + ihdr + idat + iend)
colors = {'high':(234,67,53),'medium':(251,188,4),'low':(52,168,83),'none':(154,160,166)}
for label,(r,g,b) in colors.items():
    for pct in range(0,110,10): make_png(f'$ICON_DIR/pie_{label}_{pct}.png', r, g, b)
make_png(f'$ICON_DIR/app_icon.png', 66, 133, 244)
print('  ✓ 图标已生成')
"
else
    echo -e "  ${GREEN}✓ 图标就绪 ($(ls -1 $ICON_DIR/*.png 2>/dev/null | wc -l) 个)${NC}"
fi

# ========================================================================
# 5. PyInstaller 构建
# ========================================================================
section "PyInstaller 构建"
START_TIME=$(date +%s)

if "$VENV_PYTHON" -m PyInstaller "$SPEC_FILE" 2>&1 | tail -20; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo ""
    echo -e "  ${GREEN}✓ 构建成功 (耗时 ${DURATION}s)${NC}"
else
    echo -e "  ${RED}✗ 构建失败${NC}"
    exit 1
fi

# ========================================================================
# 6. 验证产物
# ========================================================================
section "验证产物"
if [[ -f "$APP_BINARY" ]]; then
    SIZE=$(du -h "$APP_BINARY" | cut -f1)
    echo -e "  ${GREEN}✓${NC} 可执行文件: $APP_BINARY (${SIZE})"
    file "$APP_BINARY" | sed 's/^/    /'
else
    echo -e "  ${RED}✗ 产物缺失: $APP_BINARY${NC}"
    exit 1
fi

# ========================================================================
# 7. 构建安装器（可选）
# ========================================================================
if $BUILD_INSTALLER; then
    section "构建安装器"

    # 确保主应用已构建
    if [[ ! -f "$APP_BINARY" ]] && [[ ! -d "$DIST_DIR/ZenTray" ]]; then
        echo -e "  ${RED}✗ 主应用产物缺失，请先构建主应用${NC}"
        exit 1
    fi

    INSTALLER_START=$(date +%s)

    if "$VENV_PYTHON" -m PyInstaller "$INSTALLER_SPEC" 2>&1 | tail -20; then
        INSTALLER_END=$(date +%s)
        INSTALLER_DURATION=$((INSTALLER_END - INSTALLER_START))
        echo ""
        echo -e "  ${GREEN}✓ 安装器构建成功 (耗时 ${INSTALLER_DURATION}s)${NC}"
    else
        echo -e "  ${RED}✗ 安装器构建失败${NC}"
        exit 1
    fi

    # 验证安装器产物
    if [[ -f "$INSTALLER_BINARY" ]]; then
        SIZE=$(du -h "$INSTALLER_BINARY" | cut -f1)
        echo -e "  ${GREEN}✓${NC} 安装器: $INSTALLER_BINARY (${SIZE})"
    elif [[ -d "$INSTALLER_BINARY" ]]; then
        echo -e "  ${GREEN}✓${NC} 安装器: $INSTALLER_BINARY/"
    else
        echo -e "  ${RED}✗ 安装器产物缺失${NC}"
        exit 1
    fi

    # 打包安装器发布包
    mkdir -p "$RELEASES_DIR"
    INSTALLER_TARBALL="ZenTrayInstaller-${VERSION}-x86_64.tar.gz"
    cd "$DIST_DIR"
    tar czf "releases/$INSTALLER_TARBALL" ZenTrayInstaller
    INSTALLER_TAR_SIZE=$(du -h "releases/$INSTALLER_TARBALL" | cut -f1)
    echo -e "  ${GREEN}✓${NC} $RELEASES_DIR/$INSTALLER_TARBALL (${INSTALLER_TAR_SIZE})"
    cd "$PROJECT_DIR"
fi

# ========================================================================
# 8. 打包发布包（主应用）
# ========================================================================
section "打包发布包"
mkdir -p "$RELEASES_DIR"
TARBALL="ZenTray-${VERSION}-x86_64.tar.gz"
cd "$DIST_DIR"
tar czf "releases/$TARBALL" ZenTray
TAR_SIZE=$(du -h "releases/$TARBALL" | cut -f1)
echo -e "  ${GREEN}✓${NC} $RELEASES_DIR/$TARBALL (${TAR_SIZE})"

# ========================================================================
# 9. 汇总
# ========================================================================
section "构建完成"
echo ""
echo -e "  ${BOLD}产物:${NC}"
echo -e "    可执行文件:    ${GREEN}$APP_BINARY${NC}"
if $BUILD_INSTALLER; then
    echo -e "    安装器:        ${GREEN}$INSTALLER_BINARY${NC}"
    echo -e "    安装器安装包:  ${GREEN}$RELEASES_DIR/$INSTALLER_TARBALL${NC}"
fi
echo -e "    安装包:        ${GREEN}$RELEASES_DIR/$TARBALL${NC}"
echo ""
echo -e "  ${BOLD}快速测试:${NC}"
echo -e "    ${CYAN}$APP_BINARY${NC}"
if $BUILD_INSTALLER; then
    echo -e "    ${CYAN}$INSTALLER_BINARY${NC}"
fi
echo ""

# ========================================================================
# 10. 运行（可选）
# ========================================================================
if $RUN_AFTER; then
    section "启动应用"
    # 杀掉旧进程
    pkill -f ZenTray 2>/dev/null || true
    sleep 0.5
    echo -e "  ${YELLOW}→ 启动 ZenTray ...${NC}"
    "$APP_BINARY" &
    sleep 2
    if pgrep -f ZenTray > /dev/null; then
        echo -e "  ${GREEN}✓ 进程已启动 (PID: $(pgrep -f ZenTray | head -1))${NC}"
    else
        echo -e "  ${RED}✗ 进程未启动，检查日志${NC}"
        echo "  查看日志: cat $PROJECT_DIR/zentray.log"
    fi
fi
