# zentray/services/pomodoro_service.py
"""
番茄钟专注服务 —— 独立的番茄钟计时与状态管理。

将原 TrayManager 中的番茄钟逻辑抽取为独立服务，
通过 Qt Signal 与 UI 层解耦。
"""
from PySide6.QtCore import QTimer, Signal, QObject
from zentray.config import POMODORO_MINUTES


class PomodoroService(QObject):
    """番茄钟专注服务"""

    time_updated = Signal(int)       # 剩余秒数更新
    pomodoro_finished = Signal()     # 专注结束

    def __init__(self, duration_minutes: int = POMODORO_MINUTES):
        super().__init__()
        self.duration = duration_minutes * 60  # 转换为秒
        self.remaining_seconds = 0
        self.is_active = False

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    # ==========================================
    # 公共方法
    # ==========================================

    def start(self) -> None:
        """开始专注计时"""
        self.remaining_seconds = self.duration
        self.is_active = True
        self.timer.start(1000)  # 每秒触发一次

    def stop(self) -> None:
        """中止专注计时"""
        self.is_active = False
        self.timer.stop()
        self.remaining_seconds = 0

    def extend(self, additional_minutes: int = None) -> None:
        """延长专注时间（默认使用设置中的延长步长）"""
        if additional_minutes is None:
            from zentray.services.settings_manager import SettingsManager
            additional_minutes = SettingsManager().pomodoro.extend_minutes
        if self.is_active:
            self.remaining_seconds += additional_minutes * 60

    def get_remaining(self) -> int:
        """获取剩余秒数"""
        return self.remaining_seconds

    def get_status(self) -> dict:
        """获取当前状态摘要"""
        return {
            "is_active": self.is_active,
            "remaining_seconds": self.remaining_seconds,
            "remaining_minutes": self.remaining_seconds // 60,
        }

    # ==========================================
    # 内部方法
    # ==========================================

    def _tick(self) -> None:
        """每秒回调"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.time_updated.emit(self.remaining_seconds)
        else:
            self.is_active = False
            self.timer.stop()
            self.pomodoro_finished.emit()
