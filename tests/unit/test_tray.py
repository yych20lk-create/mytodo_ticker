import unittest
from PySide6.QtWidgets import QApplication
import sys

from zentray.ui.tray import WindowsTaskbarTray, create_tray_backend

# 单例 QApplication
app = QApplication.instance() or QApplication([])


class TestWindowsTaskbarTray(unittest.TestCase):
    def test_windows_taskbar_tray_creation(self):
        tray = WindowsTaskbarTray(app)
        self.assertIsNotNone(tray.taskbar_window)
        self.assertEqual(tray._full_text, "ZenTray")

    def test_set_label_and_marquee(self):
        tray = WindowsTaskbarTray(app)
        short_title = "短标题"
        tray.set_label(short_title)
        self.assertEqual(tray._full_text, short_title)
        self.assertFalse(tray._marquee_timer.isActive())
        self.assertEqual(tray.taskbar_window.windowTitle(), short_title)

        long_title = "这是一个非常长非常长的 ZenTray 任务标题用来测试跑马灯"
        tray.set_label(long_title)
        self.assertEqual(tray._full_text, long_title)
        self.assertTrue(tray._marquee_timer.isActive())

        # 模拟 1 次 tick 滚动
        tray._on_marquee_tick()
        self.assertNotEqual(tray.taskbar_window.windowTitle(), "")

        tray.shutdown()


if __name__ == "__main__":
    unittest.main()
