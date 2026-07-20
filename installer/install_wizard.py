# installer/install_wizard.py
"""
ZenTray 安装向导 — 独立安装器主程序。

作为独立 PySide6 应用运行，与 ZenTray 主体分离打包。
七步向导：欢迎 → 进程检测 → 安装目录 → 通知配置 → AI 配置 → 安装 → 完成。
"""
import sys
import os
import time
import shutil
import subprocess
import logging

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QWidget, QFileDialog,
    QProgressBar, QTextEdit, QCheckBox, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from installer.platform_utils import (
    get_default_install_dir, create_desktop_shortcut,
    setup_autostart, APP_NAME, APP_DISPLAY_NAME,
)

logger = logging.getLogger(__name__)

# 应用版本（构建时从 zentray.config 读取或硬编码）
# 与 zentray.config.VERSION 保持同步
try:
    from zentray.config import VERSION as APP_VERSION
except Exception:
    APP_VERSION = "0.1.0"


# ==========================================
# 后台安装线程
# ==========================================

class InstallWorker(QThread):
    """在后台线程执行文件复制 + 快捷方式 + 开机自启"""

    progress = Signal(int, int)   # (current, total)
    log_message = Signal(str)     # 日志消息
    finished = Signal(bool, str)  # (success, error_message)

    def __init__(self, src_binary: str, dst_dir: str,
                 create_shortcut: bool, enable_autostart: bool,
                 icon_path: str = None, env_lines: list = None):
        super().__init__()
        self.src_binary = src_binary   # 源二进制文件路径 (eg. _MEIPASS/ZenTray/ZenTray)
        self.dst_dir = dst_dir
        self.create_shortcut = create_shortcut
        self.enable_autostart = enable_autostart
        self.icon_path = icon_path
        self.env_lines = env_lines or []

    def run(self):
        try:
            # Step 1: 复制二进制文件
            self.log_message.emit("正在安装 ZenTray ...")
            os.makedirs(self.dst_dir, exist_ok=True)

            # 确定目标可执行文件路径
            if sys.platform == "win32":
                exe_name = "ZenTray.exe"
            else:
                exe_name = "ZenTray"
            exe_path = os.path.join(self.dst_dir, exe_name)

            shutil.copy2(self.src_binary, exe_path)
            os.chmod(exe_path, 0o755)
            self.progress.emit(1, 2)
            self.log_message.emit(f"✓ 已安装到 {exe_path}")

            # Step 2: 复制图标到安装目录
            if self.icon_path and os.path.exists(self.icon_path):
                icon_dst_dir = os.path.join(self.dst_dir, "resources", "icons")
                os.makedirs(icon_dst_dir, exist_ok=True)
                icon_name = os.path.basename(self.icon_path)
                dst_icon = os.path.join(icon_dst_dir, icon_name)
                shutil.copy2(self.icon_path, dst_icon)
                self.progress.emit(2, 2)

            # Step 3: 写入 .env 配置
            if self.env_lines:
                env_path = os.path.join(self.dst_dir, ".env")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.env_lines) + "\n")
                self.log_message.emit("✓ 配置文件已写入 .env")

            # Step 4: 桌面快捷方式
            if self.create_shortcut:
                self.log_message.emit("正在创建桌面快捷方式...")
                if create_desktop_shortcut(exe_path, APP_NAME, dst_icon if self.icon_path else None):
                    self.log_message.emit("✓ 桌面快捷方式已创建")
                else:
                    self.log_message.emit("⚠ 桌面快捷方式创建失败")

            # Step 5: 开机自启
            if self.enable_autostart:
                self.log_message.emit("正在设置开机自启...")
                if setup_autostart(exe_path, APP_NAME):
                    self.log_message.emit("✓ 开机自启已设置")
                else:
                    self.log_message.emit("⚠ 开机自启设置失败")

            self.log_message.emit("安装完成！")
            self.finished.emit(True, "")

        except Exception as e:
            self.log_message.emit(f"安装失败: {e}")
            self.finished.emit(False, str(e))


# ==========================================
# 各页面组件
# ==========================================

class WelcomePage(QWidget):
    """欢迎页 —— 产品介绍 + 版本信息"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel(f"🚀 欢迎安装 {APP_DISPLAY_NAME}")
        title.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        ver = QLabel(f"版本 v{APP_VERSION}")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(ver)

        desc = QLabel(
            "ZenTray 是一款跨平台个人效率工具，\n"
            "帮助你管理待办任务、保持专注节奏。\n\n"
            "✅ 核心功能：\n"
            "   • 任务创建、分类、优先级管理\n"
            "   • 番茄钟专注计时\n"
            "   • 系统托盘轮播看板\n"
            "   • 全局快捷键闪电添加\n\n"
            "⚡ 可选功能：\n"
            "   • 移动端消息推送（WxPusher）\n"
            "   • AI 每日毒舌复盘教练\n\n"
            "点击「下一步」开始安装。"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; line-height: 1.6;")
        layout.addWidget(desc)


class ProcessCheckPage(QWidget):
    """进程检测页 —— 检测运行中的 ZenTray 并提供关闭选项"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._resolved = False  # 是否已解决（关闭 / 用户跳过）

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("🔍 检查运行状态")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        header.setFont(f)
        layout.addWidget(header)

        self.status_label = QLabel("正在检测...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.status_label)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.detail_label)

        self.action_btn = QPushButton("关闭 ZenTray 并继续")
        self.action_btn.setVisible(False)
        self.action_btn.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #c0392b; }"
        )
        layout.addWidget(self.action_btn)

        self.skip_btn = QPushButton("跳过，保留运行中的程序")
        self.skip_btn.setVisible(False)
        self.skip_btn.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.skip_btn)

        layout.addStretch()

    def check(self) -> bool:
        """检测进程是否运行，更新 UI，返回 True 表示可以继续"""
        try:
            from zentray.services.system_utils import SingleInstanceGuard
            self._is_running = SingleInstanceGuard.is_running()
        except ImportError:
            # 安装器独立运行时无法 import zentray，回退到直接 socket 检测
            from PySide6.QtNetwork import QLocalSocket
            socket = QLocalSocket()
            socket.connectToServer("ZenTray_SingleInstance")
            self._is_running = socket.waitForConnected(500)
            socket.close()

        if self._is_running:
            self.status_label.setText("⚠ 检测到 ZenTray 正在运行")
            self.detail_label.setText(
                "为了顺利完成安装，建议先关闭当前运行的 ZenTray。\n"
                "你的数据（任务、设置）不会丢失。"
            )
            self.action_btn.setVisible(True)
            self.skip_btn.setVisible(True)
            self._resolved = False
            return False  # 需要用户决策
        else:
            self.status_label.setText("✅ 未检测到运行中的 ZenTray")
            self.detail_label.setText("可以安全继续安装。")
            self.action_btn.setVisible(False)
            self.skip_btn.setVisible(False)
            self._resolved = True
            return True  # 可直接继续

    def is_resolved(self) -> bool:
        return self._resolved

    def try_close_app(self) -> bool:
        """尝试关闭运行中的 ZenTray，返回是否成功"""
        try:
            from zentray.services.system_utils import SingleInstanceGuard
            ok = SingleInstanceGuard.send_quit()
        except ImportError:
            from PySide6.QtNetwork import QLocalSocket
            socket = QLocalSocket()
            socket.connectToServer("ZenTray_SingleInstance")
            if not socket.waitForConnected(1000):
                ok = False
            else:
                socket.write(b"quit")
                ok = socket.waitForBytesWritten(1000)
                socket.close()

        if ok:
            # 等待进程退出（最多 5 秒）
            for _ in range(25):
                time.sleep(0.2)
                try:
                    from zentray.services.system_utils import SingleInstanceGuard
                    if not SingleInstanceGuard.is_running():
                        break
                except ImportError:
                    from PySide6.QtNetwork import QLocalSocket
                    s = QLocalSocket()
                    s.connectToServer("ZenTray_SingleInstance")
                    still_running = s.waitForConnected(200)
                    s.close()
                    if not still_running:
                        break

        # 再次检测
        try:
            from zentray.services.system_utils import SingleInstanceGuard
            still_running = SingleInstanceGuard.is_running()
        except ImportError:
            from PySide6.QtNetwork import QLocalSocket
            s = QLocalSocket()
            s.connectToServer("ZenTray_SingleInstance")
            still_running = s.waitForConnected(200)
            s.close()

        return not still_running


class InstallDirPage(QWidget):
    """安装目录选择页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("📁 选择安装目录")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        header.setFont(f)
        layout.addWidget(header)

        desc = QLabel("选择 ZenTray 的安装位置。需要约 100MB 磁盘空间。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        dir_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(get_default_install_dir())
        self.path_input.setMinimumHeight(32)
        dir_layout.addWidget(self.path_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse)
        dir_layout.addWidget(browse_btn)

        layout.addLayout(dir_layout)

        hint = QLabel("")
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)
        self.hint_label = hint

        # 检查空间
        self.path_input.textChanged.connect(self._validate)
        self._validate(self.path_input.text())

        layout.addStretch()

    def _browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择安装目录", self.path_input.text(),
        )
        if directory:
            self.path_input.setText(directory)

    def _validate(self, path: str):
        if not path:
            self.hint_label.setText("请输入安装路径")
            self.hint_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            return
        parent = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(parent):
            self.hint_label.setText("父目录不存在，将自动创建")
            self.hint_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        elif os.path.exists(path):
            self.hint_label.setText("目录已存在，将覆盖安装（数据不会丢失）")
            self.hint_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        else:
            self.hint_label.setText("")
        # 空间检查跳过（跨平台实现复杂，非关键路径）

    def get_path(self) -> str:
        return self.path_input.text().strip()


class AIConfigPage(QWidget):
    """AI 教练 & 通知配置页（合并）—— 可跳过"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel("🤖 AI 教练 & 消息推送（可选）")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        header.setFont(f)
        layout.addWidget(header)

        desc = QLabel(
            "配置 AI API 后，ZenTray 将在每晚自动生成你的当日\n"
            "任务执行复盘报告，并通过 WxPusher 推送到你的手机。\n"
            "支持 OpenAI 兼容 API（包括 DeepSeek 等国产模型）。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        # AI 配置
        layout.addWidget(QLabel("API Key:"))
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        layout.addWidget(self.ai_key)

        layout.addWidget(QLabel("API Base URL (可选):"))
        self.ai_base = QLineEdit()
        self.ai_base.setPlaceholderText("https://api.openai.com/v1")
        layout.addWidget(self.ai_base)

        layout.addWidget(QLabel("模型名称 (可选):"))
        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("gpt-4o")
        layout.addWidget(self.ai_model)

        # 分隔
        sep = QLabel("")
        sep.setFixedHeight(8)
        layout.addWidget(sep)

        # 通知配置
        sub_header = QLabel("📱 消息推送")
        f2 = QFont()
        f2.setPointSize(12)
        f2.setBold(True)
        sub_header.setFont(f2)
        layout.addWidget(sub_header)

        layout.addWidget(QLabel("App Token:"))
        self.wx_token = QLineEdit()
        self.wx_token.setPlaceholderText("AT_xxxxxxxxxxxxxxxxxxxx")
        layout.addWidget(self.wx_token)

        layout.addWidget(QLabel("UID:"))
        self.wx_uid = QLineEdit()
        self.wx_uid.setPlaceholderText("UID_xxxxxxxxxxxxxxxxxxxx")
        layout.addWidget(self.wx_uid)

        skip_hint = QLabel("留空即可跳过，后续可在 .env 文件中手动配置。\n获取方式：访问 wxpusher.zjiecode.com 注册并创建应用。")
        skip_hint.setStyleSheet("color: #aaa; font-size: 11px;")
        skip_hint.setWordWrap(True)
        layout.addWidget(skip_hint)

        layout.addStretch()

    def get_env_lines(self) -> list:
        """返回 .env 内容行列表"""
        lines = []
        if self.wx_token.text().strip():
            lines.append(f"WXPUSHER_APP_TOKEN={self.wx_token.text().strip()}")
        if self.wx_uid.text().strip():
            lines.append(f"WXPUSHER_UID={self.wx_uid.text().strip()}")
        if self.ai_key.text().strip():
            lines.append(f"AI_API_KEY={self.ai_key.text().strip()}")
        if self.ai_base.text().strip():
            lines.append(f"AI_API_BASE_URL={self.ai_base.text().strip()}")
        if self.ai_model.text().strip():
            lines.append(f"AI_MODEL_NAME={self.ai_model.text().strip()}")
        return lines


class InstallProgressPage(QWidget):
    """安装进度页 —— 进度条 + 日志输出"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("⚙ 正在安装...")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        header.setFont(f)
        layout.addWidget(header)

        self.status_label = QLabel("准备中...")
        self.status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(200)
        self.log_view.setStyleSheet(
            "QTextEdit { background: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 11px; }"
        )
        layout.addWidget(self.log_view)

        layout.addStretch()

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_progress(self, current: int, total: int):
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar.setValue(pct)

    def append_log(self, text: str):
        self.log_view.append(text)
        # 自动滚动到底部
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class FinishPage(QWidget):
    """完成页 —— 快捷方式 & 开机自启勾选 + 启动按钮"""

    launch_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🎉")
        icon.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(48)
        icon.setFont(f)
        layout.addWidget(icon)

        msg = QLabel("安装完成！")
        msg.setAlignment(Qt.AlignCenter)
        f2 = QFont()
        f2.setPointSize(16)
        f2.setBold(True)
        msg.setFont(f2)
        layout.addWidget(msg)

        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.detail_label)

        layout.addSpacing(12)

        # 选项：桌面快捷方式（仅 Windows 显示）
        self.cb_shortcut = QCheckBox("创建桌面快捷方式")
        self.cb_shortcut.setChecked(True)
        self.cb_shortcut.setStyleSheet("font-size: 13px;")
        self.cb_shortcut.setVisible(sys.platform == "win32")
        layout.addWidget(self.cb_shortcut)

        self.cb_autostart = QCheckBox("开机自动启动")
        self.cb_autostart.setChecked(False)
        self.cb_autostart.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.cb_autostart)

        layout.addSpacing(16)

        self.launch_btn = QPushButton("🚀 立即启动 ZenTray")
        self.launch_btn.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 10px 24px; "
            "border-radius: 4px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background: #219a52; }"
        )
        self.launch_btn.clicked.connect(self.launch_requested.emit)
        layout.addWidget(self.launch_btn)

        layout.addStretch()

    def set_detail(self, install_dir: str):
        self.detail_label.setText(f"已安装到：\n{install_dir}")


# ==========================================
# 安装向导主窗口
# ==========================================

class InstallWizard(QDialog):
    """安装向导主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} 安装向导")
        self.setMinimumSize(560, 460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 在 sys._MEIPASS 中定位 ZenTray 二进制文件和图标
        self._src_binary = self._find_binary()
        self._src_icon = self._find_icon()

        # 安装选项（在完成页收集）
        self._create_shortcut = True
        self._enable_autostart = False

        self._install_success = False
        self._install_dir = ""

        self._init_ui()

        # 首次显示后触发进程检测
        QTimer.singleShot(300, self._on_page_changed)

    @staticmethod
    def _find_binary() -> str:
        """在打包数据中定位 ZenTray 二进制文件"""
        base = sys._MEIPASS
        # 可能的路径
        candidates = [
            os.path.join(base, "ZenTray", "ZenTray"),          # Linux PyInstaller data
            os.path.join(base, "ZenTray", "ZenTray.exe"),      # Windows
            os.path.join(base, "ZenTray"),                     # 直接打在根目录
            os.path.join(base, "dist", "ZenTray"),             # 开发模式
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        # macOS .app bundle
        app_bundle = os.path.join(base, "ZenTray", "ZenTray.app")
        if os.path.isdir(app_bundle):
            return app_bundle
        return ""

    @staticmethod
    def _find_icon() -> str:
        """在打包数据中定位应用图标"""
        base = sys._MEIPASS
        candidates = [
            os.path.join(base, "resources", "icons", "app_icon.png"),
            os.path.join(base, "resources", "icons", "app_icon.ico"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return ""

    # ==========================================
    # UI 构建
    # ==========================================

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        self.title_label = QLabel(f"{APP_DISPLAY_NAME} 安装向导")
        self.title_label.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        self.title_label.setFont(f)
        layout.addWidget(self.title_label)

        # 页面堆栈
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # 构建所有页面
        self._welcome = WelcomePage()
        self._process = ProcessCheckPage()
        self._install_dir_page = InstallDirPage()
        self._ai = AIConfigPage()
        self._progress = InstallProgressPage()
        self._finish = FinishPage()

        self.stack.addWidget(self._welcome)           # 0
        self.stack.addWidget(self._process)           # 1
        self.stack.addWidget(self._install_dir_page)  # 2
        self.stack.addWidget(self._ai)                # 3
        self.stack.addWidget(self._progress)          # 4
        self.stack.addWidget(self._finish)            # 5

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_back = QPushButton("← 上一步")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setVisible(False)
        btn_layout.addWidget(self.btn_back)

        self.btn_next = QPushButton("下一步 →")
        self.btn_next.setDefault(True)
        self.btn_next.clicked.connect(self._go_next)
        btn_layout.addWidget(self.btn_next)

        layout.addLayout(btn_layout)

        # 完成页信号
        self._finish.launch_requested.connect(self._launch_app)
        self._finish.cb_shortcut.toggled.connect(self._on_shortcut_toggled)
        self._finish.cb_autostart.toggled.connect(self._on_autostart_toggled)

        # 进程检测页按钮
        self._process.action_btn.clicked.connect(self._on_close_and_continue)
        self._process.skip_btn.clicked.connect(self._on_skip_running)

    # ==========================================
    # 导航
    # ==========================================

    def _go_next(self):
        current = self.stack.currentIndex()

        # 页面 1 (进程检测) → 需要先检查 resolved
        if current == 1 and not self._process.is_resolved():
            return

        # 页面 4 (安装进度) → 页面 5 (完成) —— 仅安装成功时
        if current == 4:
            if not self._install_success:
                return

        if current < self.stack.count() - 1:
            self.stack.setCurrentIndex(current + 1)
            self._on_page_changed()

    def _go_back(self):
        current = self.stack.currentIndex()
        if current > 0:
            # 安装进度页和完成页禁止后退
            if current in (4, 5):
                return
            self.stack.setCurrentIndex(current - 1)
            self._on_page_changed()

    def _on_page_changed(self):
        """页面切换后的钩子"""
        current = self.stack.currentIndex()
        is_first = current == 0

        self.btn_back.setVisible(not is_first)
        self.btn_back.setEnabled(current not in (4, 5))

        if current == 4:
            # 安装进度页 —— 自动开始安装
            self.btn_next.setVisible(False)
            self.btn_back.setVisible(False)
            self._start_installation()
        elif current == 5:
            # 完成页
            self.btn_next.setVisible(False)
            self.btn_back.setVisible(False)
        else:
            self.btn_next.setVisible(True)
            self.btn_next.setText("开始安装 →" if current == 3 else "下一步 →")

        if current == 1:
            self._run_process_check()

    def _update_nav_for_process(self):
        """根据进程检测结果更新按钮状态"""
        if self._process.is_resolved():
            self.btn_next.setEnabled(True)
            self.btn_next.setText("下一步 →")
        else:
            self.btn_next.setEnabled(False)

    # ==========================================
    # 进程检测逻辑
    # ==========================================

    def _run_process_check(self):
        """执行进程检测；若无运行中进程则自动跳过本页"""
        can_proceed = self._process.check()
        self._update_nav_for_process()
        if can_proceed:
            # 未检测到运行中的 ZenTray，直接跳到下一页
            self.stack.setCurrentIndex(2)
            self._on_page_changed()

    def _on_close_and_continue(self):
        """用户选择关闭运行中的 ZenTray"""
        self._process.action_btn.setEnabled(False)
        self._process.action_btn.setText("正在关闭...")
        self._process.status_label.setText("⏳ 正在关闭 ZenTray...")
        QApplication.processEvents()

        ok = self._process.try_close_app()
        if ok:
            self._process.status_label.setText("✅ ZenTray 已关闭，可以继续安装")
            self._process.detail_label.setText("")
            self._process.action_btn.setVisible(False)
            self._process.skip_btn.setVisible(False)
            self._process._resolved = True
            self._update_nav_for_process()
        else:
            self._process.status_label.setText("⚠ 无法自动关闭 ZenTray")
            self._process.detail_label.setText(
                "请手动关闭 ZenTray（右键托盘图标 → 退出），然后点击「下一步」。\n"
                "如果仍然不行，请重启计算机后重试。"
            )
            self._process.action_btn.setText("重试关闭")
            self._process.action_btn.setEnabled(True)
            self._process._resolved = False
            self._update_nav_for_process()

    def _on_skip_running(self):
        """用户选择跳过，保留运行中的程序继续安装"""
        result = QMessageBox.question(
            self, "确认跳过",
            "ZenTray 仍在运行中。如果继续安装，新文件将覆盖旧文件，\n"
            "但运行中的进程不受影响。建议安装完成后手动重启应用。\n\n"
            "确定继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            self._process.status_label.setText("⏭ 已跳过，将继续安装")
            self._process.action_btn.setVisible(False)
            self._process.skip_btn.setVisible(False)
            self._process.detail_label.setText("")
            self._process._resolved = True
            self._update_nav_for_process()

    # ==========================================
    # 安装执行
    # ==========================================

    def _start_installation(self):
        """在后台线程启动安装流程"""
        install_dir = self._install_dir_page.get_path()
        if not install_dir:
            QMessageBox.warning(self, "路径错误", "请输入有效的安装路径。")
            self.stack.setCurrentIndex(2)
            return
        self._install_dir = install_dir

        if not self._src_binary or not os.path.isfile(self._src_binary):
            self._progress.append_log(f"错误: 找不到安装源文件 {self._src_binary}")
            self._progress.set_status("安装失败 —— 安装包不完整")
            return

        # 收集 .env 配置行（AI 页面已合并通知配置）
        env_lines = self._ai.get_env_lines()

        # 启动后台安装线程
        self._worker = InstallWorker(
            src_binary=self._src_binary,
            dst_dir=install_dir,
            create_shortcut=self._create_shortcut,
            enable_autostart=self._enable_autostart,
            icon_path=self._src_icon,
            env_lines=env_lines,
        )
        self._worker.progress.connect(self._on_install_progress)
        self._worker.log_message.connect(self._on_install_log)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_progress(self, current: int, total: int):
        self._progress.set_progress(current, total)
        self._progress.set_status(f"正在复制文件... ({current}/{total})")

    def _on_install_log(self, text: str):
        self._progress.append_log(text)

    def _on_install_finished(self, success: bool, error: str):
        if success:
            self._install_success = True
            self._progress.set_status("安装完成！")
            self._progress.progress_bar.setValue(100)

            # 更新完成页
            self._finish.set_detail(self._install_dir)

            # 自动跳转到完成页
            self.stack.setCurrentIndex(5)
            self.btn_back.setVisible(False)
            self.btn_next.setVisible(False)
        else:
            self._progress.set_status(f"安装失败: {error}")
            self._progress.append_log(f"❌ {error}")
            self.btn_next.setVisible(True)
            self.btn_next.setText("重试")
            self.btn_back.setVisible(True)
            self.btn_back.setEnabled(True)

    def _write_env_file(self):
        """.env 写入已移至 InstallWorker 中处理，此方法保留兼容"""
        pass

    # ==========================================
    # 启动应用
    # ==========================================

    def _launch_app(self):
        """安装完成后启动 ZenTray 并关闭安装器"""
        if sys.platform == "win32":
            exe = os.path.join(self._install_dir, "ZenTray.exe")
        elif sys.platform == "darwin":
            exe = self._install_dir  # .app bundle
        else:
            exe = os.path.join(self._install_dir, "ZenTray")

        if not os.path.exists(exe):
            QMessageBox.warning(self, "启动失败", f"找不到可执行文件:\n{exe}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(exe)
            elif sys.platform == "darwin":
                subprocess.run(["open", exe], check=False)
            else:
                subprocess.Popen([exe], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            QMessageBox.warning(self, "启动失败", f"无法启动应用: {e}")
            return

        # 关闭安装器
        self.accept()

    # ==========================================
    # 选项回调
    # ==========================================

    def _on_shortcut_toggled(self, checked: bool):
        self._create_shortcut = checked

    def _on_autostart_toggled(self, checked: bool):
        self._enable_autostart = checked


# ==========================================
# 入口
# ==========================================

def main():
    """安装器主入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # 开发模式：模拟 PyInstaller 的 sys._MEIPASS
    if not hasattr(sys, "_MEIPASS"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        sys._MEIPASS = project_root  # 项目根目录作为"打包根"
        # 开发模式下 ZenTray 二进制在 dist/ 下
        # _find_binary 会检查 sys._MEIPASS/ZenTray/ZenTray, sys._MEIPASS/dist/ZenTray 等

    wizard = InstallWizard()

    # 验证是否找到源文件
    if not wizard._src_binary or not os.path.isfile(wizard._src_binary):
        QMessageBox.critical(
            None, "安装包不完整",
            f"未找到 ZenTray 安装源文件。\n"
            f"搜索路径: {wizard._find_binary() or '(未找到)'}\n\n"
            f"请确认已先执行 pyinstaller zentray.spec 构建主应用。"
        )
        sys.exit(1)

    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
