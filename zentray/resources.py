# zentray/resources.py
"""
资源文件管理 —— 兼容开发模式和 PyInstaller 打包模式。

PyInstaller 打包后资源会解压到临时目录 sys._MEIPASS，
开发模式下资源位于项目根目录。此模块提供统一访问路径。
"""
import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件绝对路径，兼容开发 / PyInstaller 两种模式。

    开发模式：相对于项目根目录
    PyInstaller 打包：相对于 _MEIPASS 临时目录

    Args:
        relative_path: 资源文件相对路径，如 "resources/icons/app_icon.png"

    Returns:
        Path: 资源文件绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行
        base_path = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        # 开发模式：zentray 包的父目录即项目根目录
        base_path = Path(__file__).parent.parent

    return base_path / relative_path


def get_user_data_dir() -> Path:
    """
    获取用户数据目录（配置、任务数据等持久化文件）。

    遵循各平台标准惯例：
    - Linux: $XDG_DATA_HOME/zentray 或 ~/.local/share/zentray
    - macOS: ~/Library/Application Support/ZenTray
    - Windows: %APPDATA%/ZenTray

    Returns:
        Path: 用户数据目录路径
    """
    if sys.platform == "linux":
        xdg = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        return Path(xdg) / "zentray"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ZenTray"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "ZenTray"
    return Path.home() / ".zentray"


def ensure_data_dirs() -> None:
    """确保所有用户数据目录存在"""
    data_dir = get_user_data_dir()
    (data_dir / "archive").mkdir(parents=True, exist_ok=True)
    (data_dir / "icons").mkdir(parents=True, exist_ok=True)
