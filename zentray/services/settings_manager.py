# zentray/services/settings_manager.py
"""
设置管理器 —— 统一管理应用配置的持久化与读取。

优先级：settings.json > .env 环境变量 > 代码默认值
"""
import json
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict
from zentray.config import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"


# ==========================================
# 配置数据结构
# ==========================================

@dataclass
class PollingSettings:
    """任务轮播设置"""
    high_priority_seconds: int = 4      # 🔴 高优任务停留秒数
    medium_priority_seconds: int = 2    # 🟡 中优任务停留秒数
    low_priority_seconds: int = 2       # 🟢 低优任务停留秒数


@dataclass
class PomodoroSettings:
    """番茄钟设置"""
    duration_minutes: int = 25
    extend_minutes: int = 10


@dataclass
class NightlySettings:
    """夜间复盘设置"""
    trigger_hour: int = 23
    trigger_minute: int = 30


@dataclass
class NotificationSettings:
    """通知服务设置"""
    enabled: bool = True
    wxpusher_app_token: str = ""
    wxpusher_uid: str = ""


@dataclass
class AISettings:
    """AI 教练设置"""
    enabled: bool = True
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"


@dataclass
class AppSettings:
    """应用完整设置"""
    polling: PollingSettings = field(default_factory=PollingSettings)
    pomodoro: PomodoroSettings = field(default_factory=PomodoroSettings)
    nightly: NightlySettings = field(default_factory=NightlySettings)
    notification: NotificationSettings = field(default_factory=NotificationSettings)
    ai: AISettings = field(default_factory=AISettings)


# ==========================================
# 设置管理器
# ==========================================

class SettingsManager:
    """应用设置管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._settings = AppSettings()
        self._load_from_env()
        self._load_from_file()
        self._loaded = True

    # ---------- 加载 ----------

    def _load_from_env(self) -> None:
        """从环境变量加载（.env 文件已在 config.py 中预加载）"""
        notif = self._settings.notification
        if os.getenv("WXPUSHER_APP_TOKEN"):
            notif.wxpusher_app_token = os.getenv("WXPUSHER_APP_TOKEN")
        if os.getenv("WXPUSHER_UID"):
            notif.wxpusher_uid = os.getenv("WXPUSHER_UID")

        ai = self._settings.ai
        if os.getenv("AI_API_KEY"):
            ai.api_key = os.getenv("AI_API_KEY")
        ai.base_url = os.getenv("AI_API_BASE_URL", ai.base_url)
        ai.model = os.getenv("AI_MODEL_NAME", ai.model)

    def _load_from_file(self) -> None:
        """从 settings.json 加载（覆盖环境变量）"""
        if not SETTINGS_FILE.exists():
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_dict(data)
        except (json.JSONDecodeError, Exception):
            pass

    def _apply_dict(self, data: dict) -> None:
        """将字典数据写入 AppSettings"""
        if "polling" in data:
            p = data["polling"]
            self._settings.polling = PollingSettings(
                high_priority_seconds=p.get("high_priority_seconds", 4),
                medium_priority_seconds=p.get("medium_priority_seconds", 2),
                low_priority_seconds=p.get("low_priority_seconds", 2),
            )
        if "pomodoro" in data:
            p = data["pomodoro"]
            self._settings.pomodoro = PomodoroSettings(
                duration_minutes=p.get("duration_minutes", 25),
                extend_minutes=p.get("extend_minutes", 10),
            )
        if "nightly" in data:
            n = data["nightly"]
            self._settings.nightly = NightlySettings(
                trigger_hour=n.get("trigger_hour", 23),
                trigger_minute=n.get("trigger_minute", 30),
            )
        if "notification" in data:
            n = data["notification"]
            self._settings.notification = NotificationSettings(
                enabled=n.get("enabled", True),
                wxpusher_app_token=n.get("wxpusher_app_token", ""),
                wxpusher_uid=n.get("wxpusher_uid", ""),
            )
        if "ai" in data:
            a = data["ai"]
            self._settings.ai = AISettings(
                enabled=a.get("enabled", True),
                api_key=a.get("api_key", ""),
                base_url=a.get("base_url", "https://api.openai.com/v1"),
                model=a.get("model", "gpt-4o"),
            )

    # ---------- 保存 ----------

    def save(self) -> None:
        """保存当前设置到 settings.json"""
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {
            "polling": asdict(self._settings.polling),
            "pomodoro": asdict(self._settings.pomodoro),
            "nightly": asdict(self._settings.nightly),
            "notification": asdict(self._settings.notification),
            "ai": asdict(self._settings.ai),
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---------- 读取 ----------

    @property
    def polling(self) -> PollingSettings:
        return self._settings.polling

    @property
    def pomodoro(self) -> PomodoroSettings:
        return self._settings.pomodoro

    @property
    def nightly(self) -> NightlySettings:
        return self._settings.nightly

    @property
    def notification(self) -> NotificationSettings:
        return self._settings.notification

    @property
    def ai(self) -> AISettings:
        return self._settings.ai

    def get_all(self) -> AppSettings:
        return self._settings

    # ---------- 便捷方法 ----------

    def get_dwell_seconds(self, priority: str) -> int:
        """根据优先级获取托盘停留秒数"""
        mapping = {
            "high": self.polling.high_priority_seconds,
            "medium": self.polling.medium_priority_seconds,
            "low": self.polling.low_priority_seconds,
        }
        return mapping.get(priority, 2)

    def is_notification_configured(self) -> bool:
        n = self.notification
        return n.enabled and bool(n.wxpusher_app_token and n.wxpusher_uid)

    def is_ai_configured(self) -> bool:
        a = self.ai
        return a.enabled and bool(a.api_key)
