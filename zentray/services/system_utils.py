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


class SingleInstanceGuard:
    """单例模式锁：基于 Qt 本地套接字实现跨平台防多开"""

    def __init__(self, server_name="ZenTray_SingleInstance"):
        self.server_name = server_name
        self.socket = QLocalSocket()
        self.socket.connectToServer(self.server_name)

        if self.socket.waitForConnected(500):
            logger.error("ZenTray 已在运行中，本次启动已阻止。")
            sys.exit(1)

        self.server = QLocalServer()
        self.server.removeServer(self.server_name)
        if not self.server.listen(self.server_name):
            print("SingleInstanceGuard 服务启动失败，程序退出。")
            sys.exit(1)


def is_screen_locked() -> bool:
    """检测屏幕是否处于锁屏状态（后续多平台差异化实现）"""
    return False


def get_idle_time_seconds() -> int:
    """获取键鼠空闲时间（后续多平台差异化实现）"""
    return 0


class HotkeyListener(QObject):
    """后台全局快捷键监听器，通过 Qt Signal 唤醒主线程"""

    triggered = Signal()

    def __init__(self, hotkey_str="<ctrl>+<alt>+t"):
        super().__init__()
        self.hotkey_str = hotkey_str
        self.listener = None

    def start(self):
        self.listener = keyboard.GlobalHotKeys({
            self.hotkey_str: self.on_activate,
        })
        self.listener.start()

    def on_activate(self):
        self.triggered.emit()

    def stop(self):
        if self.listener:
            self.listener.stop()
