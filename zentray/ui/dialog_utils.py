# zentray/ui/dialog_utils.py
"""对话框通用布局：横版优先、适配屏幕、按钮文字完整显示。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def available_screen_size() -> QSize:
    app = QApplication.instance()
    if app and app.primaryScreen():
        g = app.primaryScreen().availableGeometry()
        return QSize(g.width(), g.height())
    return QSize(1280, 720)


def center_dialog(dialog: QDialog) -> None:
    """将对话框居中到主屏幕可用区域。"""
    app = QApplication.instance()
    if not app:
        return
    screen = app.primaryScreen()
    if not screen:
        return
    cg = dialog.frameGeometry()
    cp = screen.availableGeometry().center()
    cg.moveCenter(cp)
    dialog.move(cg.topLeft())


def fit_dialog(
    dialog: QDialog,
    *,
    preferred_w: int,
    preferred_h: int,
    min_w: int = 480,
    min_h: int = 280,
    max_ratio: float = 0.92,
) -> None:
    """
    横版优先的尺寸策略：
    - 默认宽 >= 高（横版）
    - 不超过可用屏幕 max_ratio
    - 设置 minimumSize，避免内容被压扁导致按钮文字截断
    """
    scr = available_screen_size()
    max_w = max(320, int(scr.width() * max_ratio))
    max_h = max(240, int(scr.height() * max_ratio))

    # 若偏好偏高，改为更宽的横版比例
    if preferred_h > preferred_w:
        preferred_w, preferred_h = max(preferred_w, int(preferred_h * 1.15)), min(
            preferred_h, int(preferred_w * 0.85)
        )

    w = max(min_w, min(preferred_w, max_w))
    h = max(min_h, min(preferred_h, max_h))
    # 保证横版倾向
    if h > w and max_w >= min_w + 80:
        w = min(max_w, max(w, int(h * 1.2)))

    dialog.setMinimumSize(min(min_w, w), min(min_h, h))
    dialog.resize(w, h)
    dialog.setMaximumHeight(max_h)
    dialog.setMaximumWidth(max_w)


def style_action_button(btn: QPushButton, *, min_w: int = 96, min_h: int = 34) -> QPushButton:
    """保证按钮能完整显示文字。"""
    btn.setMinimumWidth(min_w)
    btn.setMinimumHeight(min_h)
    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    # 避免样式把文字裁切
    btn.setStyleSheet(
        (btn.styleSheet() or "")
        + """
        QPushButton {
            padding: 6px 14px;
            min-height: 28px;
        }
        """
    )
    return btn


def make_scroll_body(content: QWidget) -> QScrollArea:
    """可滚动内容区（内容过高时不撑破屏幕）。"""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    scroll.setWidget(content)
    return scroll


def dialog_root_with_scroll(
    dialog: QDialog,
    *,
    margins: tuple[int, int, int, int] = (16, 16, 16, 12),
    spacing: int = 10,
) -> tuple[QVBoxLayout, QWidget, QHBoxLayout]:
    """
    标准结构：
      外层 VBox
        - ScrollArea(content_widget)  ← 主体横/纵排
        - footer_layout               ← 按钮行（始终可见）
    返回 (root_layout, content_widget, footer_layout)
    """
    root = QVBoxLayout(dialog)
    root.setContentsMargins(*margins)
    root.setSpacing(spacing)

    content = QWidget()
    scroll = make_scroll_body(content)
    root.addWidget(scroll, 1)

    footer = QHBoxLayout()
    footer.setSpacing(10)
    root.addLayout(footer)
    return root, content, footer
