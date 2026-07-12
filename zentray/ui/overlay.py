# zentray/ui/overlay.py
"""
闪电添加无边框界面。

使用半透明背景模拟毛玻璃特效，极简居中，失去焦点后自动隐藏。
通过 DI 容器获取 TaskRepository，与存储层解耦。
"""
import uuid
import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from PySide6.QtCore import Qt, Signal
from zentray.core.models import Task
from zentray.dependencies import injector
from zentray.core.repository import TaskRepository


class QuickAddOverlay(QWidget):
    """闪电添加无边框界面"""

    task_added = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 80)
        self.init_ui()

        # 通过 DI 获取存储
        self.task_repo = injector.get(TaskRepository)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.entry = QLineEdit(self)
        self.entry.setPlaceholderText("⚡ 闪电录入待办，按回车立即入库 (按 ESC 取消)...")
        self.entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 12px;
                padding: 15px 20px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: rgba(40, 40, 40, 230);
            }
        """)
        self.entry.returnPressed.connect(self.save_and_close)
        layout.addWidget(self.entry)

    def show_center(self):
        """让输入框在屏幕水平居中，垂直稍偏上"""
        screen_geo = self.screen().geometry()
        x = (screen_geo.width() - self.width()) // 2
        y = (screen_geo.height() - self.height()) // 2 - 150
        self.move(x, y)

        self.entry.clear()
        self.show()
        self.activateWindow()
        self.entry.setFocus()

    def save_and_close(self):
        """保存任务到存储并通知主 UI 刷新"""
        title = self.entry.text().strip()
        if title:
            task = Task(
                id=str(uuid.uuid4()),
                title=title,
                category="工作",
                priority="medium",
                created_at=datetime.datetime.now().isoformat(),
            )
            tasks = self.task_repo.find_all()
            tasks.append(task)
            self.task_repo.save_all(tasks)
            self.task_added.emit()

        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow():
                self.hide()
        super().changeEvent(event)
