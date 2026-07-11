# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件。

构建命令:
    pyinstaller zentray.spec

输出:
    dist/ZenTray  (Linux)
    dist/ZenTray.app  (macOS)
    dist/ZenTray.exe  (Windows)
"""

import sys
from pathlib import Path

# ---------- 基础分析 ----------
block_cipher = None

a = Analysis(
    ['zentray/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 样式文件
        ('zentray/ui/styles/*.qss', 'zentray/ui/styles'),
        # 图标资源
        ('resources/icons/*.png', 'resources/icons'),
    ],
    hiddenimports=[
        # 核心模块
        'zentray.core.models',
        'zentray.core.scheduler',
        'zentray.core.repository',
        'zentray.repositories.file_repository',
        'zentray.repositories.file_periodic_repository',
        'zentray.services.task_service',
        'zentray.services.pomodoro_service',
        'zentray.services.script_service',
        'zentray.services.notification',
        'zentray.services.ai_review',
        'zentray.ui.controller',
        'zentray.ui.renderer',
        'zentray.ui.menu_builder',
        'zentray.ui.commands',
        'zentray.ui.tray',
        'zentray.ui.dialogs',
        'zentray.ui.overlay',
        'zentray.ui.extensions.interface',
        'zentray.ui.extensions.loader',
        'zentray.workers.watcher',
        'zentray.workers.nightly_job',
        # DI 容器
        'zentray.di',
        'zentray.dependencies',
        # pynput 平台特定后端
        'pynput.keyboard._xorg',
        'pynput.keyboard._win32',
        'pynput.keyboard._darwin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除不需要的重量级库以减小包体积
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
    name='ZenTray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # 无控制台窗口（GUI 应用）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 图标（根据平台选择）
    icon='resources/icons/app_icon.ico' if sys.platform == 'win32' else 'resources/icons/app_icon.png',
)
