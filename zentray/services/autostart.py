"""开机自启：跨平台读写，不依赖 installer 是否打入发行包。"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

APP_NAME = "ZenTray"
APP_DISPLAY_NAME = "ZenTray"
APP_DESCRIPTION = "跨平台个人效率工具 — 待办管理 + 番茄钟 + AI 复盘"


def resolve_launch_target() -> Tuple[str, str]:
    """
    返回 (exec_line, workdir)。
    exec_line 可直接写入 desktop Exec= 或注册表。
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return str(exe), str(exe.parent)

    for candidate in (
        Path("/usr/bin/zentray"),
        Path("/opt/zentray/ZenTray"),
        Path.home() / ".local" / "bin" / "ZenTray" / "ZenTray",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve()), str(candidate.parent)

    project_root = Path(__file__).resolve().parents[2]
    run_sh = project_root / "run.sh"
    if run_sh.is_file():
        return str(run_sh.resolve()), str(project_root)

    # 开发回退：python -m zentray.main
    py = Path(sys.executable).resolve()
    return f"{py} -m zentray.main", str(project_root)


def is_enabled(app_name: str = APP_NAME) -> bool:
    try:
        if sys.platform == "win32":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, app_name)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        if sys.platform == "darwin":
            return _macos_plist(app_name).is_file()
        return _linux_desktop(app_name).is_file()
    except Exception:
        logger.exception("检查开机自启失败")
        return False


def set_enabled(enabled: bool, app_name: str = APP_NAME) -> Tuple[bool, str]:
    """开启或关闭自启。返回 (ok, message)。"""
    if enabled:
        return _enable(app_name)
    return _disable(app_name)


def _enable(app_name: str) -> Tuple[bool, str]:
    exec_line, workdir = resolve_launch_target()
    try:
        if sys.platform == "win32":
            import winreg

            # 注册表值需要带引号的可执行路径；带参数时整串写入
            value = exec_line if " " in exec_line and not exec_line.startswith('"') else exec_line
            if Path(exec_line.split()[0]).is_file() and " " in exec_line:
                # python path with args
                parts = exec_line.split(None, 1)
                value = f'"{parts[0]}" {parts[1]}' if len(parts) > 1 else f'"{parts[0]}"'
            elif Path(exec_line).is_file():
                value = f'"{exec_line}"'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)
            return True, "已开启开机自启（Windows 注册表）"

        if sys.platform == "darwin":
            return _enable_macos(exec_line, workdir, app_name)

        return _enable_linux(exec_line, workdir, app_name)
    except Exception as e:
        logger.exception("开启开机自启失败")
        return False, f"开启失败: {e}"


def _disable(app_name: str) -> Tuple[bool, str]:
    try:
        if sys.platform == "win32":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True, "已关闭开机自启"

        if sys.platform == "darwin":
            p = _macos_plist(app_name)
            if p.is_file():
                p.unlink()
            return True, "已关闭开机自启"

        p = _linux_desktop(app_name)
        if p.is_file():
            p.unlink()
        return True, "已关闭开机自启"
    except Exception as e:
        logger.exception("关闭开机自启失败")
        return False, f"关闭失败: {e}"


def _linux_desktop(app_name: str) -> Path:
    return Path.home() / ".config" / "autostart" / f"{app_name}.desktop"


def _macos_plist(app_name: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.zentray.{app_name}.plist"


def _enable_linux(exec_line: str, workdir: str, app_name: str) -> Tuple[bool, str]:
    desktop = _linux_desktop(app_name)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Exec 字段：单路径可直接写；带空格的命令原样写（desktop 规范允许）
    first = exec_line.split()[0]
    path_line = workdir if workdir else str(Path(first).parent)
    icon = "accessories-text-editor"
    for icon_candidate in (
        Path("/usr/share/icons/hicolor/256x256/apps/zentray.png"),
        Path(workdir) / "resources" / "icons" / "app_icon.png" if workdir else None,
    ):
        if icon_candidate and icon_candidate.is_file():
            icon = str(icon_candidate)
            break
    content = f"""[Desktop Entry]
Type=Application
Name={APP_DISPLAY_NAME}
Comment={APP_DESCRIPTION}
Exec={exec_line}
Path={path_line}
Icon={icon}
Terminal=false
Categories=Utility;Office;
StartupNotify=false
X-GNOME-Autostart-enabled=true
Hidden=false
"""
    desktop.write_text(content, encoding="utf-8")
    desktop.chmod(0o755)
    return True, f"已开启开机自启（{desktop}）"


def _enable_macos(exec_line: str, workdir: str, app_name: str) -> Tuple[bool, str]:
    plist = _macos_plist(app_name)
    plist.parent.mkdir(parents=True, exist_ok=True)
    parts = exec_line.split()
    program = parts[0]
    args_xml = ""
    if len(parts) > 1:
        arg_items = "\n".join(f"        <string>{a}</string>" for a in parts[1:])
        args_xml = f"""
    <key>ProgramArguments</key>
    <array>
        <string>{program}</string>
{arg_items}
    </array>"""
        program_block = ""
    else:
        program_block = f"""
    <key>Program</key>
    <string>{program}</string>"""
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zentray.{app_name}</string>{program_block}{args_xml}
    <key>WorkingDirectory</key>
    <string>{workdir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
    plist.write_text(content, encoding="utf-8")
    plist.chmod(0o644)
    return True, f"已开启开机自启（{plist}）"


def status() -> dict:
    exec_line, workdir = resolve_launch_target()
    return {
        "enabled": is_enabled(),
        "launch_target": exec_line,
        "workdir": workdir,
        "platform": sys.platform,
    }
