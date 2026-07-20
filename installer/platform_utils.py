# installer/platform_utils.py
"""
跨平台安装工具：默认路径、桌面快捷方式、开机自启。
"""
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "ZenTray"
APP_DISPLAY_NAME = "ZenTray"
APP_DESCRIPTION = "跨平台个人效率工具 — 待办管理 + 番茄钟 + AI 复盘"


# ==========================================
# 默认安装目录
# ==========================================

def get_default_install_dir() -> str:
    """返回各平台的默认安装路径"""
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\ZenTray
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, APP_NAME)
    elif sys.platform == "darwin":
        # macOS: /Applications/ZenTray.app
        return os.path.join("/Applications", f"{APP_NAME}.app")
    else:
        # Linux: ~/.local/bin/ZenTray
        return os.path.join(os.path.expanduser("~"), ".local", "bin", APP_NAME)


# ==========================================
# 桌面快捷方式
# ==========================================

def create_desktop_shortcut(target_exe: str, app_name: str = APP_NAME,
                            icon_path: str = None) -> bool:
    """在桌面创建应用快捷方式。Windows=lnk, Linux=desktop, macOS=alias"""
    try:
        if sys.platform == "win32":
            return _create_shortcut_windows(target_exe, app_name, icon_path)
        elif sys.platform == "darwin":
            return _create_shortcut_macos(target_exe, app_name)
        else:
            return _create_shortcut_linux(target_exe, app_name, icon_path)
    except Exception as e:
        logger.error(f"创建桌面快捷方式失败: {e}")
        return False


def _create_shortcut_windows(target_exe: str, app_name: str, icon_path: str = None) -> bool:
    """通过 PowerShell 创建 .lnk 快捷方式"""
    desktop = _get_desktop_dir()
    lnk_path = os.path.join(desktop, f"{app_name}.lnk")

    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{lnk_path}")
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"
'''
    if icon_path and os.path.exists(icon_path):
        ps_script += f'$Shortcut.IconLocation = "{icon_path}"\n'
    ps_script += f'''
$Shortcut.Description = "{APP_DESCRIPTION}"
$Shortcut.Save()
'''

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error(f"PowerShell 创建快捷方式失败: {result.stderr}")
        return False
    logger.info(f"桌面快捷方式已创建: {lnk_path}")
    return True


def _create_shortcut_linux(target_exe: str, app_name: str, icon_path: str = None) -> bool:
    """在 Linux 桌面创建 .desktop 文件"""
    desktop = _get_desktop_dir()
    desktop_file = os.path.join(desktop, f"{app_name}.desktop")

    icon_line = f"Icon={icon_path}" if icon_path and os.path.exists(icon_path) else "Icon=accessories-text-editor"

    content = f"""[Desktop Entry]
Type=Application
Name={APP_DISPLAY_NAME}
Comment={APP_DESCRIPTION}
Exec={target_exe}
Path={os.path.dirname(target_exe)}
{icon_line}
Terminal=false
Categories=Utility;Office;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(desktop_file, 0o755)
    logger.info(f"桌面快捷方式已创建: {desktop_file}")
    return True


def _create_shortcut_macos(target_exe: str, app_name: str) -> bool:
    """在 macOS 桌面创建软链接（ZenTray.app 一般直接拖到 /Applications）"""
    desktop = _get_desktop_dir()
    link_path = os.path.join(desktop, f"{app_name}.app")
    if os.path.exists(link_path):
        os.remove(link_path)
    os.symlink(target_exe, link_path)
    logger.info(f"桌面快捷方式已创建: {link_path}")
    return True


# ==========================================
# 开机自启
# ==========================================

def setup_autostart(target_exe: str, app_name: str = APP_NAME) -> bool:
    """配置应用开机自动启动"""
    try:
        if sys.platform == "win32":
            return _setup_autostart_windows(target_exe, app_name)
        elif sys.platform == "darwin":
            return _setup_autostart_macos(target_exe, app_name)
        else:
            return _setup_autostart_linux(target_exe, app_name)
    except Exception as e:
        logger.error(f"配置开机自启失败: {e}")
        return False


def _setup_autostart_windows(target_exe: str, app_name: str) -> bool:
    """通过注册表 Run 键设置开机自启"""
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, target_exe)
        winreg.CloseKey(key)
        logger.info(f"开机自启已设置 (注册表): {app_name}")
        return True
    except Exception as e:
        logger.error(f"注册表开机自启失败: {e}")
        return False


def _setup_autostart_linux(target_exe: str, app_name: str) -> bool:
    """在 ~/.config/autostart/ 下创建 .desktop 文件"""
    autostart_dir = os.path.join(os.path.expanduser("~"), ".config", "autostart")
    os.makedirs(autostart_dir, exist_ok=True)

    desktop_file = os.path.join(autostart_dir, f"{app_name}.desktop")
    content = f"""[Desktop Entry]
Type=Application
Name={APP_DISPLAY_NAME}
Comment={APP_DESCRIPTION}
Exec={target_exe}
Path={os.path.dirname(target_exe)}
Icon=accessories-text-editor
Terminal=false
Categories=Utility;Office;
StartupNotify=false
X-GNOME-Autostart-enabled=true
Hidden=false
"""
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(desktop_file, 0o755)
    logger.info(f"开机自启已设置 (autostart): {desktop_file}")
    return True


def _setup_autostart_macos(target_exe: str, app_name: str) -> bool:
    """通过 LaunchAgent plist 设置开机自启"""
    launch_dir = os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")
    os.makedirs(launch_dir, exist_ok=True)

    plist_path = os.path.join(launch_dir, f"com.zentray.{app_name}.plist")
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zentray.{app_name}</string>
    <key>Program</key>
    <string>{target_exe}</string>
    <key>WorkingDirectory</key>
    <string>{os.path.dirname(target_exe)}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)
    os.chmod(plist_path, 0o644)
    logger.info(f"开机自启已设置 (LaunchAgent): {plist_path}")
    return True


def remove_autostart(app_name: str = APP_NAME) -> bool:
    """移除开机自启配置（卸载时使用）"""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        elif sys.platform == "darwin":
            plist = os.path.join(
                os.path.expanduser("~"), "Library", "LaunchAgents",
                f"com.zentray.{app_name}.plist",
            )
            if os.path.exists(plist):
                os.remove(plist)
        else:
            desktop_file = os.path.join(
                os.path.expanduser("~"), ".config", "autostart",
                f"{app_name}.desktop",
            )
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
        return True
    except Exception as e:
        logger.error(f"移除开机自启失败: {e}")
        return False


def is_autostart_enabled(app_name: str = APP_NAME) -> bool:
    """检查开机自启是否已设置"""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, app_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        elif sys.platform == "darwin":
            plist = os.path.join(
                os.path.expanduser("~"), "Library", "LaunchAgents",
                f"com.zentray.{app_name}.plist",
            )
            return os.path.exists(plist)
        else:
            desktop_file = os.path.join(
                os.path.expanduser("~"), ".config", "autostart",
                f"{app_name}.desktop",
            )
            return os.path.exists(desktop_file)
    except Exception:
        return False


def is_desktop_shortcut_created(app_name: str = APP_NAME) -> bool:
    """检查桌面快捷方式是否存在"""
    desktop = _get_desktop_dir()
    if sys.platform == "win32":
        return os.path.exists(os.path.join(desktop, f"{app_name}.lnk"))
    elif sys.platform == "darwin":
        return os.path.exists(os.path.join(desktop, f"{app_name}.app"))
    else:
        return os.path.exists(os.path.join(desktop, f"{app_name}.desktop"))


def remove_desktop_shortcut(app_name: str = APP_NAME) -> bool:
    """移除桌面快捷方式"""
    try:
        desktop = _get_desktop_dir()
        if sys.platform == "win32":
            path = os.path.join(desktop, f"{app_name}.lnk")
        elif sys.platform == "darwin":
            path = os.path.join(desktop, f"{app_name}.app")
        else:
            path = os.path.join(desktop, f"{app_name}.desktop")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    except Exception as e:
        logger.error(f"移除桌面快捷方式失败: {e}")
        return False


# ==========================================
# 工具函数
# ==========================================

def _get_desktop_dir() -> str:
    """获取用户桌面目录路径（跨平台）"""
    if sys.platform == "win32":
        # Windows: 优先用系统 API 读取，回退到拼接
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf)
            return buf.value
        except Exception:
            return os.path.join(os.environ["USERPROFILE"], "Desktop")
    else:
        # Linux / macOS: XDG_DESKTOP_DIR 或 ~/Desktop
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        # 尝试读取 XDG 用户目录配置（支持中文桌面等）
        try:
            user_dirs = os.path.join(os.path.expanduser("~"), ".config", "user-dirs.dirs")
            if os.path.exists(user_dirs):
                with open(user_dirs, "r") as f:
                    for line in f:
                        if line.startswith("XDG_DESKTOP_DIR="):
                            # 格式: XDG_DESKTOP_DIR="$HOME/Desktop"
                            val = line.strip().split("=", 1)[1].strip('"').replace("$HOME", os.path.expanduser("~"))
                            if os.path.isdir(val):
                                return val
        except Exception:
            pass
        return desktop


def copy_with_progress(src_dir: str, dst_dir: str, progress_callback=None) -> bool:
    """递归复制目录，支持进度回调。progress_callback(current, total)"""
    import os
    all_files = []
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            all_files.append(os.path.relpath(os.path.join(root, f), src_dir))
    total = len(all_files)
    if total == 0:
        return True

    os.makedirs(dst_dir, exist_ok=True)
    for idx, rel_path in enumerate(all_files):
        src = os.path.join(src_dir, rel_path)
        dst = os.path.join(dst_dir, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if progress_callback:
            progress_callback(idx + 1, total)
    return True
