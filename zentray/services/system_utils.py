# zentray/services/system_utils.py
"""
系统级工具：单例锁、空闲检测、全局快捷键监听。
"""
import sys
import logging

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)


SERVER_NAME = "ZenTray_SingleInstance"


class SingleInstanceGuard(QObject):
    """单例模式锁：基于 Qt 本地套接字实现跨平台防多开 + IPC 通信"""

    quit_requested = Signal()
    activate_requested = Signal()  # 二次点击桌面图标时唤醒已有实例

    def __init__(self, server_name: str = SERVER_NAME):
        super().__init__()
        self.server_name = server_name

        # 尝试连接已有实例 —— 若成功则通知其「激活」后安静退出
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            try:
                socket.write(b"activate")
                socket.waitForBytesWritten(500)
            except Exception:
                pass
            socket.close()
            logger.info("ZenTray 已在运行，已通知前台实例激活。")
            # 正常退出码 0，避免桌面显示「启动失败」
            sys.exit(0)

        # 创建本地服务端，占住单例锁 + 接收外部指令
        self._server = QLocalServer()
        # 清理残留 socket 文件（异常退出后）
        QLocalServer.removeServer(self.server_name)
        if not self._server.listen(self.server_name):
            # 再试一次
            QLocalServer.removeServer(self.server_name)
            if not self._server.listen(self.server_name):
                logger.error("SingleInstanceGuard 服务启动失败: %s", self._server.errorString())
                print("SingleInstanceGuard 服务启动失败，程序退出。", file=sys.stderr)
                sys.exit(1)

        self._server.newConnection.connect(self._on_new_connection)

    # ==========================================
    # 内部：处理外部连接（activate / quit）
    # ==========================================

    def _on_new_connection(self) -> None:
        client = self._server.nextPendingConnection()
        if client is None:
            return
        if client.waitForReadyRead(800):
            data = client.readAll().data().decode("utf-8", errors="replace").strip()
            if data == "quit":
                logger.info("收到退出指令，正在关闭...")
                self.quit_requested.emit()
            elif data == "activate" or data == "":
                # 空数据：兼容旧二次启动只 connect 不写内容
                logger.info("收到激活指令（二次点击图标）")
                self.activate_requested.emit()
        else:
            # 连接后无数据也视为激活（旧客户端）
            self.activate_requested.emit()
        client.close()

    # ==========================================
    # 静态工具：供安装器检测 & 通信
    # ==========================================

    @staticmethod
    def is_running(server_name: str = SERVER_NAME) -> bool:
        """检测是否已有 ZenTray 实例在运行（安装器使用）"""
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(500):
            socket.close()
            return True
        return False

    @staticmethod
    def send_quit(server_name: str = SERVER_NAME) -> bool:
        """向运行中的 ZenTray 发送退出指令，返回是否发送成功"""
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if not socket.waitForConnected(1000):
            return False
        socket.write(b"quit")
        if not socket.waitForBytesWritten(1000):
            socket.close()
            return False
        socket.close()
        return True

    @staticmethod
    def send_activate(server_name: str = SERVER_NAME) -> bool:
        """通知已运行实例弹出提示"""
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if not socket.waitForConnected(1000):
            return False
        socket.write(b"activate")
        ok = socket.waitForBytesWritten(1000)
        socket.close()
        return ok


# ==========================================
# 桌面快捷方式 & 开机自启 工具函数
# ==========================================

import os as _os

APP_NAME = "ZenTray"


def _get_desktop_dir() -> str:
    """获取用户桌面目录路径"""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf)
            return buf.value
        except Exception:
            return _os.path.join(_os.environ["USERPROFILE"], "Desktop")
    else:
        desktop = _os.path.join(_os.path.expanduser("~"), "Desktop")
        try:
            user_dirs = _os.path.join(_os.path.expanduser("~"), ".config", "user-dirs.dirs")
            if _os.path.exists(user_dirs):
                with open(user_dirs, "r") as f:
                    for line in f:
                        if line.startswith("XDG_DESKTOP_DIR="):
                            val = line.strip().split("=", 1)[1].strip('"').replace("$HOME", _os.path.expanduser("~"))
                            if _os.path.isdir(val):
                                return val
        except Exception:
            pass
        return desktop


def is_shortcut_created(app_name: str = APP_NAME) -> bool:
    """检查桌面快捷方式是否存在"""
    desktop = _get_desktop_dir()
    if sys.platform == "win32":
        return _os.path.exists(_os.path.join(desktop, f"{app_name}.lnk"))
    elif sys.platform == "darwin":
        return _os.path.exists(_os.path.join(desktop, f"{app_name}.app"))
    else:
        return _os.path.exists(_os.path.join(desktop, f"{app_name}.desktop"))


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
            plist = _os.path.join(
                _os.path.expanduser("~"), "Library", "LaunchAgents",
                f"com.zentray.{app_name}.plist",
            )
            return _os.path.exists(plist)
        else:
            desktop_file = _os.path.join(
                _os.path.expanduser("~"), ".config", "autostart",
                f"{app_name}.desktop",
            )
            return _os.path.exists(desktop_file)
    except Exception:
        return False


def toggle_shortcut(enable: bool, app_name: str = APP_NAME) -> bool:
    """创建或移除桌面快捷方式"""
    try:
        exe = sys.executable
        desktop = _get_desktop_dir()

        if sys.platform == "win32":
            lnk_path = _os.path.join(desktop, f"{app_name}.lnk")
            if enable:
                ps = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{lnk_path}")
$Shortcut.TargetPath = "{exe}"
$Shortcut.WorkingDirectory = "{_os.path.dirname(exe)}"
$Shortcut.Save()
'''
                import subprocess as _sp
                result = _sp.run(["powershell", "-NoProfile", "-Command", ps],
                                 capture_output=True, text=True)
                return result.returncode == 0
            else:
                if _os.path.exists(lnk_path):
                    _os.remove(lnk_path)
                return True

        elif sys.platform == "darwin":
            link_path = _os.path.join(desktop, f"{app_name}.app")
            if enable:
                if not _os.path.exists(link_path):
                    _os.symlink(exe, link_path)
            else:
                if _os.path.exists(link_path):
                    _os.remove(link_path)
            return True

        else:  # Linux
            desktop_file = _os.path.join(desktop, f"{app_name}.desktop")
            if enable:
                content = f"""[Desktop Entry]
Type=Application
Name=ZenTray
Exec={exe}
Path={_os.path.dirname(exe)}
Icon=accessories-text-editor
Terminal=false
Categories=Utility;Office;
"""
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(content)
                _os.chmod(desktop_file, 0o755)
            else:
                if _os.path.exists(desktop_file):
                    _os.remove(desktop_file)
            return True
    except Exception:
        return False


def toggle_autostart(enable: bool, app_name: str = APP_NAME) -> bool:
    """设置或取消开机自启"""
    try:
        exe = sys.executable

        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True

        elif sys.platform == "darwin":
            launch_dir = _os.path.join(_os.path.expanduser("~"), "Library", "LaunchAgents")
            _os.makedirs(launch_dir, exist_ok=True)
            plist_path = _os.path.join(launch_dir, f"com.zentray.{app_name}.plist")
            if enable:
                plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zentray.{app_name}</string>
    <key>Program</key>
    <string>{exe}</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
                with open(plist_path, "w", encoding="utf-8") as f:
                    f.write(plist)
            else:
                if _os.path.exists(plist_path):
                    _os.remove(plist_path)
            return True

        else:  # Linux
            autostart_dir = _os.path.join(_os.path.expanduser("~"), ".config", "autostart")
            desktop_file = _os.path.join(autostart_dir, f"{app_name}.desktop")
            if enable:
                _os.makedirs(autostart_dir, exist_ok=True)
                content = f"""[Desktop Entry]
Type=Application
Name=ZenTray
Exec={exe}
Path={_os.path.dirname(exe)}
Icon=accessories-text-editor
Terminal=false
X-GNOME-Autostart-enabled=true
"""
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(content)
                _os.chmod(desktop_file, 0o755)
            else:
                if _os.path.exists(desktop_file):
                    _os.remove(desktop_file)
            return True
    except Exception:
        return False


class HotkeyListener(QObject):
    """后台全局快捷键监听器，通过 Qt Signal 唤醒主线程"""

    triggered = Signal()

    def __init__(self, hotkey_str="<ctrl>+<alt>+t"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.listener = None

    def start(self) -> bool:
        """启动全局热键。失败时返回 False，不抛出到主流程。"""
        try:
            self.listener = keyboard.GlobalHotKeys({
                self.hotkey_str: self.on_activate,
            })
            self.listener.start()
            return True
        except Exception as e:
            logger.error("全局热键启动失败 (%s): %s", self.hotkey_str, e)
            self.listener = None
            return False

    def on_activate(self):
        self.triggered.emit()

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
