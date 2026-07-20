# -*- mode: python ; coding: utf-8 -*-
"""
ZenTray 安装器 PyInstaller 打包配置。

构建命令:
    # 先构建主应用
    pyinstaller zentray.spec
    # 再构建安装器（将主应用打包进安装器）
    pyinstaller installer.spec

输出:
    dist/ZenTrayInstaller       (Linux)
    dist/ZenTrayInstaller.exe   (Windows)
    dist/ZenTrayInstaller.app   (macOS)
"""
import sys
import os

# ---------- 基础分析 ----------
block_cipher = None

# 根据平台确定主应用二进制文件名
if sys.platform == "win32":
    _app_binary = "dist/ZenTray.exe"
elif sys.platform == "darwin":
    _app_binary = "dist/ZenTray"  # macOS .app bundle
else:
    _app_binary = "dist/ZenTray"

# 构建 data 列表：打包主应用二进制 + 图标
_datas = []

# 主应用二进制
if os.path.isfile(_app_binary):
    _datas.append((_app_binary, "ZenTray"))
elif os.path.isdir(_app_binary):
    # macOS .app 或其他目录结构：递归打包
    for root, dirs, files in os.walk(_app_binary):
        for f in files:
            src = os.path.join(root, f)
            dst = os.path.relpath(src, "dist")
            _datas.append((src, dst))
else:
    raise FileNotFoundError(f"主应用产物不存在: {_app_binary}，请先运行 pyinstaller zentray.spec")

# 应用图标（用于创建快捷方式）
_icon_candidates = [
    "resources/icons/app_icon.png",
    "resources/icons/app_icon.ico",
]
for _ic in _icon_candidates:
    if os.path.exists(_ic):
        _datas.append((_ic, os.path.dirname(_ic)))
        break

a = Analysis(
    ['installer/install_wizard.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtNetwork',
        'installer.platform_utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

# ---------- 过滤不必要的二进制 ----------
pyz = PYZ(a.pure, a.zipped_data)

# ---------- 可执行文件 ----------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ZenTrayInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # GUI 应用，无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.ico' if sys.platform == 'win32' else 'resources/icons/app_icon.png',
)
