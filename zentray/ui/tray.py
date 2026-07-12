# zentray/ui/tray.py
"""
跨平台系统托盘底层实现。

提供统一的托盘接口抽象，Linux 下使用原生 GTK AppIndicator 桥接，
Windows / macOS 下回退到 Qt 标准系统托盘。
"""
import os
import sys
import json
import subprocess
import threading

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, Signal, QObject

from zentray.config import DATA_DIR


# ==========================================
# 1. 底层跨平台托盘接口抽象
# ==========================================

class TrayImplementation(QObject):
    """跨平台状态栏底层接口定义"""

    action_received = Signal(str)

    def set_label(self, text: str):
        pass

    def set_icon(self, name: str):
        pass

    def update_menu(self, items: list):
        pass

    def show_notification(self, title: str, msg: str):
        pass

    def shutdown(self):
        pass


# ==========================================
# 2. Linux 原生 GNOME 桥接实现
# ==========================================

class LinuxBridgeTray(TrayImplementation):
    """通过系统 Python 和 AyatanaAppIndicator 实现的 Linux 顶栏文本滚动模块"""

    def __init__(self):
        super().__init__()
        self.bridge_process = None
        self._start_bridge()

    def _start_bridge(self):
        bridge_script = os.path.join(os.path.dirname(__file__), "linux_tray_bridge.py")
        icon_dir = os.path.join(DATA_DIR, "icons")
        self.bridge_process = subprocess.Popen(
            ["/usr/bin/python3", bridge_script, icon_dir],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
        )

        def read_bridge():
            for line in self.bridge_process.stdout:
                try:
                    data = json.loads(line)
                    if "action" in data:
                        self.action_received.emit(data["action"])
                except Exception:
                    pass

        threading.Thread(target=read_bridge, daemon=True).start()

    def _send(self, data):
        if self.bridge_process and self.bridge_process.poll() is None:
            try:
                self.bridge_process.stdin.write(json.dumps(data) + "\n")
                self.bridge_process.stdin.flush()
            except Exception:
                pass

    def set_icon(self, name: str):
        self._send({"type": "icon", "icon": name})

    def set_label(self, text: str):
        self._send({"type": "label", "text": text})

    def update_menu(self, items: list):
        self._send({"type": "menu", "items": items})

    def show_notification(self, title: str, msg: str):
        tray = QSystemTrayIcon(QIcon.fromTheme("emblem-default"))
        tray.show()
        tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)
        QTimer.singleShot(6000, tray.hide)

    def shutdown(self):
        self._send({"type": "quit"})


# ==========================================
# 3. Windows/macOS 标准 Qt 实现
# ==========================================

class QtStandardTray(TrayImplementation):
    """标准的跨平台托盘，适用于 Windows / macOS 或不支持 AppIndicator 的桌面"""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tray = QSystemTrayIcon()

        fallback_icon = QIcon.fromTheme("emblem-default")
        self.tray.setIcon(fallback_icon)
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        self.actions = []

    def set_label(self, text: str):
        self.tray.setToolTip(text)

    def set_icon(self, name: str):
        icon_path = os.path.join(DATA_DIR, "icons", f"{name}.png")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))

    def update_menu(self, items: list):
        self.menu.clear()
        self.actions.clear()
        self._build_qt_menu(self.menu, items)

    def _build_qt_menu(self, qt_menu, items):
        for item in items:
            if item == "separator":
                qt_menu.addSeparator()
            elif "submenu" in item:
                submenu = QMenu(item["label"], qt_menu)
                if "icon" in item:
                    icon_path = os.path.join(DATA_DIR, "icons", f"{item['icon']}.png")
                    if os.path.exists(icon_path):
                        submenu.setIcon(QIcon(icon_path))
                self._build_qt_menu(submenu, item["submenu"])
                qt_menu.addMenu(submenu)
            else:
                action = QAction(item["label"], qt_menu)
                action.setEnabled(item.get("enabled", True))
                if "icon" in item:
                    icon_path = os.path.join(DATA_DIR, "icons", f"{item['icon']}.png")
                    if os.path.exists(icon_path):
                        action.setIcon(QIcon(icon_path))
                action.triggered.connect(
                    lambda checked=False, aid=item["id"]: self.action_received.emit(aid)
                )
                qt_menu.addAction(action)
                self.actions.append(action)

    def show_notification(self, title: str, msg: str):
        self.tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)

    def shutdown(self):
        self.tray.hide()


# ==========================================
# 4. 托盘后端工厂方法
# ==========================================

def create_tray_backend(app) -> TrayImplementation:
    """根据平台创建合适的托盘实现"""
    if sys.platform.startswith("linux"):
        try:
            res = subprocess.run(
                ["/usr/bin/python3", "-c", "import gi; gi.require_version('AppIndicator3', '0.1')"],
                capture_output=True, timeout=1,
            )
            if res.returncode == 0:
                return LinuxBridgeTray()
        except Exception:
            pass
    # 其他情况回退到 Qt 标准实现
    return QtStandardTray(app)
