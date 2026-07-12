# zentray/ui/settings_dialog.py
"""
设置对话框 —— 4 标签页配置面板。

校验规则：高优停留 ≥ 中优停留 ≥ 低优停留（强要求）。
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QSpinBox, QCheckBox,
    QMessageBox, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from zentray.services.settings_manager import SettingsManager, AppSettings


class SettingsDialog(QDialog):
    """应用设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ZenTray 设置")
        self.setMinimumSize(480, 440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._manager = SettingsManager()
        self._settings = self._manager.get_all()

        self.init_ui()
        self._load_values()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_notification_tab(), "📱 通知")
        self.tabs.addTab(self._create_ai_tab(), "🤖 AI教练")
        self.tabs.addTab(self._create_polling_tab(), "📋 任务轮播")
        self.tabs.addTab(self._create_pomodoro_tab(), "🍅 番茄钟")
        layout.addWidget(self.tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("💾 保存设置")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    # ==========================================
    # 通知标签页
    # ==========================================

    def _create_notification_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        self.notif_enabled = QCheckBox("启用移动端消息推送")
        self.notif_enabled.toggled.connect(self._toggle_notif_group)
        layout.addWidget(self.notif_enabled)

        group = QGroupBox("WxPusher 凭据")
        self.notif_group = group
        form = QFormLayout(group)
        form.setSpacing(8)

        self.wx_token = QLineEdit()
        self.wx_token.setPlaceholderText("AT_xxxxxxxxxxxxxxxxxxxx")
        form.addRow("App Token:", self.wx_token)

        self.wx_uid = QLineEdit()
        self.wx_uid.setPlaceholderText("UID_xxxxxxxxxxxxxxxxxxxx")
        form.addRow("UID:", self.wx_uid)

        layout.addWidget(group)
        layout.addStretch()

        hint = QLabel("获取方式：访问 wxpusher.zjiecode.com 注册并创建应用。")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return tab

    def _toggle_notif_group(self, checked):
        self.notif_group.setEnabled(checked)

    # ==========================================
    # AI教练标签页
    # ==========================================

    def _create_ai_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        self.ai_enabled = QCheckBox("启用 AI 每日复盘教练")
        self.ai_enabled.toggled.connect(self._toggle_ai_group)
        layout.addWidget(self.ai_enabled)

        group = QGroupBox("API 配置")
        self.ai_group = group
        form = QFormLayout(group)
        form.setSpacing(8)

        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        form.addRow("API Key:", self.ai_key)

        self.ai_base = QLineEdit()
        self.ai_base.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("Base URL:", self.ai_base)

        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("gpt-4o")
        form.addRow("模型名称:", self.ai_model)

        layout.addWidget(group)

        # 调度时间
        time_group = QGroupBox("复盘时间")
        time_layout = QHBoxLayout(time_group)
        time_layout.addWidget(QLabel("每天"))
        self.nightly_hour = QSpinBox()
        self.nightly_hour.setRange(0, 23)
        self.nightly_hour.setValue(23)
        self.nightly_hour.setSuffix(" 时")
        time_layout.addWidget(self.nightly_hour)
        self.nightly_minute = QSpinBox()
        self.nightly_minute.setRange(0, 59)
        self.nightly_minute.setValue(30)
        self.nightly_minute.setSuffix(" 分")
        self.nightly_minute.setSingleStep(5)
        time_layout.addWidget(self.nightly_minute)
        time_layout.addStretch()
        layout.addWidget(time_group)

        layout.addStretch()
        return tab

    def _toggle_ai_group(self, checked):
        self.ai_group.setEnabled(checked)

    # ==========================================
    # 任务轮播标签页
    # ==========================================

    def _create_polling_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        intro = QLabel("设置各优先级任务在托盘状态栏中的停留时间。\n高优先级停留时间不得少于低优先级。")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(intro)

        group = QGroupBox("停留时间（秒）")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.high_dwell = QSpinBox()
        self.high_dwell.setRange(1, 60)
        self.high_dwell.setSuffix(" 秒")
        self.high_dwell.setPrefix("🔴 高优  ")
        self.high_dwell.valueChanged.connect(self._validate_polling)
        form.addRow(self.high_dwell)

        self.medium_dwell = QSpinBox()
        self.medium_dwell.setRange(1, 60)
        self.medium_dwell.setSuffix(" 秒")
        self.medium_dwell.setPrefix("🟡 中优  ")
        self.medium_dwell.valueChanged.connect(self._validate_polling)
        form.addRow(self.medium_dwell)

        self.low_dwell = QSpinBox()
        self.low_dwell.setRange(1, 60)
        self.low_dwell.setSuffix(" 秒")
        self.low_dwell.setPrefix("🟢 低优  ")
        self.low_dwell.valueChanged.connect(self._validate_polling)
        form.addRow(self.low_dwell)

        layout.addWidget(group)

        self.polling_error = QLabel("")
        self.polling_error.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self.polling_error.setWordWrap(True)
        layout.addWidget(self.polling_error)

        layout.addStretch()
        return tab

    def _validate_polling(self):
        """校验：高 ≥ 中 ≥ 低"""
        h = self.high_dwell.value()
        m = self.medium_dwell.value()
        l = self.low_dwell.value()

        if h < m:
            self.polling_error.setText("⚠️ 高优停留时间（{}秒）不得少于中优（{}秒）".format(h, m))
        elif m < l:
            self.polling_error.setText("⚠️ 中优停留时间（{}秒）不得少于低优（{}秒）".format(m, l))
        else:
            self.polling_error.setText("")

    # ==========================================
    # 番茄钟标签页
    # ==========================================

    def _create_pomodoro_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        group = QGroupBox("计时设置")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.pomo_duration = QSpinBox()
        self.pomo_duration.setRange(5, 120)
        self.pomo_duration.setSuffix(" 分钟")
        self.pomo_duration.setValue(25)
        form.addRow("专注时长:", self.pomo_duration)

        self.pomo_extend = QSpinBox()
        self.pomo_extend.setRange(1, 60)
        self.pomo_extend.setSuffix(" 分钟")
        self.pomo_extend.setValue(10)
        form.addRow("每次延长:", self.pomo_extend)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    # ==========================================
    # 加载 / 保存
    # ==========================================

    def _load_values(self):
        """从 SettingsManager 加载当前值"""
        # 通知
        notif = self._settings.notification
        self.notif_enabled.setChecked(notif.enabled)
        self.wx_token.setText(notif.wxpusher_app_token)
        self.wx_uid.setText(notif.wxpusher_uid)
        self._toggle_notif_group(notif.enabled)

        # AI
        ai = self._settings.ai
        self.ai_enabled.setChecked(ai.enabled)
        self.ai_key.setText(ai.api_key)
        self.ai_base.setText(ai.base_url)
        self.ai_model.setText(ai.model)
        self._toggle_ai_group(ai.enabled)

        # 夜间复盘时间
        nightly = self._settings.nightly
        self.nightly_hour.setValue(nightly.trigger_hour)
        self.nightly_minute.setValue(nightly.trigger_minute)

        # 轮播
        polling = self._settings.polling
        self.high_dwell.setValue(polling.high_priority_seconds)
        self.medium_dwell.setValue(polling.medium_priority_seconds)
        self.low_dwell.setValue(polling.low_priority_seconds)
        self._validate_polling()

        # 番茄钟
        pomo = self._settings.pomodoro
        self.pomo_duration.setValue(pomo.duration_minutes)
        self.pomo_extend.setValue(pomo.extend_minutes)

    def _save_and_accept(self):
        """校验并保存"""
        # 轮播校验
        if self.polling_error.text():
            QMessageBox.warning(
                self, "校验失败",
                "请修正任务轮播设置：\n高优停留时间 ≥ 中优 ≥ 低优。"
            )
            self.tabs.setCurrentIndex(2)  # 切换到轮播标签页
            return

        # 写入设置对象
        self._settings.polling.high_priority_seconds = self.high_dwell.value()
        self._settings.polling.medium_priority_seconds = self.medium_dwell.value()
        self._settings.polling.low_priority_seconds = self.low_dwell.value()

        self._settings.pomodoro.duration_minutes = self.pomo_duration.value()
        self._settings.pomodoro.extend_minutes = self.pomo_extend.value()

        self._settings.nightly.trigger_hour = self.nightly_hour.value()
        self._settings.nightly.trigger_minute = self.nightly_minute.value()

        self._settings.notification.enabled = self.notif_enabled.isChecked()
        self._settings.notification.wxpusher_app_token = self.wx_token.text().strip()
        self._settings.notification.wxpusher_uid = self.wx_uid.text().strip()

        self._settings.ai.enabled = self.ai_enabled.isChecked()
        self._settings.ai.api_key = self.ai_key.text().strip()
        self._settings.ai.base_url = self.ai_base.text().strip()
        self._settings.ai.model = self.ai_model.text().strip()

        # 持久化
        self._manager.save()
        self.accept()
