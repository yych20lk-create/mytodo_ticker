# zentray/ui/controller.py
"""
托盘协调者 —— 事件路由 + 状态协调 + 扩展管理。

将原 TrayManager 拆分为：
  - TrayController（本文件）：协调者，负责事件路由
  - TrayRenderer：封装托盘底层渲染
  - MenuBuilder：负责菜单结构生成
"""
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.services.script_service import ScriptService
from zentray.services.settings_manager import SettingsManager
from zentray.ui.renderer import TrayRenderer
from zentray.ui.menu_builder import MenuBuilder
from zentray.ui.extensions.loader import ExtensionLoader
from zentray.config import POLLING_INTERVAL_MS


class TrayController(QObject):
    """托盘协调者"""

    def __init__(
        self,
        app: QApplication,
        task_service: TaskService,
        pomodoro_service: PomodoroService,
        script_service: ScriptService,
        renderer: TrayRenderer,
        menu_builder: MenuBuilder,
        extension_loader: ExtensionLoader,
    ):
        super().__init__()
        self.app = app
        self.task_service = task_service
        self.pomodoro_service = pomodoro_service
        self.script_service = script_service
        self.renderer = renderer
        self.menu_builder = menu_builder
        self.extension_loader = extension_loader

        # 设置管理器
        self._settings = SettingsManager()

        # 加载扩展
        self.extensions = self.extension_loader.load_all()

        # 连接番茄钟信号
        self.pomodoro_service.time_updated.connect(self._on_pomodoro_tick)
        self.pomodoro_service.pomodoro_finished.connect(self._on_pomodoro_end)

        # 连接脚本日志信号
        self.script_service.log_updated.connect(self._on_script_log)

        # 动态轮播定时器（根据当前任务优先级调整间隔）
        self.poll_timer = QTimer()
        self.poll_timer.setSingleShot(True)  # 单次触发，每次手动重新启动
        self.poll_timer.timeout.connect(self._on_poll_tick)

        # 启动首次轮播
        self._schedule_next_poll(delay_ms=500)

        # 应用退出时关闭托盘
        self.app.aboutToQuit.connect(self.renderer.shutdown)

    # ==========================================
    # 事件路由
    # ==========================================

    def handle_action(self, action_id: str) -> None:
        """中央事件路由 —— 通过命令模式分发"""
        from .commands import dispatch

        if not dispatch(action_id, self):
            pass  # 未识别的命令

    # ==========================================
    # 动态轮播
    # ==========================================

    def _on_poll_tick(self) -> None:
        """定时器触发：更新显示后，根据当前任务优先级调度下一次"""
        self._update_display()

        # 根据当前任务优先级决定下次间隔
        task = self.task_service.get_current_task()
        if task:
            dwell_seconds = self._settings.get_dwell_seconds(task.priority)
        else:
            dwell_seconds = 3  # 无任务时默认 3 秒

        self._schedule_next_poll(dwell_seconds * 1000)

    def _schedule_next_poll(self, delay_ms: int) -> None:
        """安排下一次轮播刷新"""
        self.poll_timer.start(delay_ms)

    # ==========================================
    # 设置应用
    # ==========================================

    def apply_settings(self) -> None:
        """重新加载设置并应用到各服务（设置对话框保存后调用）"""
        # 重建 SettingsManager 单例以刷新缓存
        SettingsManager._instance = None
        self._settings = SettingsManager()

        # 更新番茄钟服务时长
        self.pomodoro_service.duration = self._settings.pomodoro.duration_minutes * 60

        # 立即触发一次显示更新
        self._update_display()

    # ==========================================
    # 显示更新
    # ==========================================

    def _update_display(self) -> None:
        """更新状态栏显示"""
        if self.pomodoro_service.is_active:
            mins = self.pomodoro_service.get_remaining() // 60
            self.renderer.set_text(f"🍅 专注中 {mins}分钟")
        else:
            task = self.task_service.get_current_task()
            if task:
                self.renderer.set_text(task.title)
                progress = getattr(task, "progress", 0)
                self.renderer.set_icon(
                    f"pie_{task.priority}_{(progress // 10) * 10}"
                )
            else:
                self.renderer.set_text("🎉 暂无待办")

        # 刷新菜单
        task = self.task_service.get_current_task()
        tasks = self.task_service.get_all_tasks()
        items = self.menu_builder.build_main_menu(
            task_exists=task is not None,
            is_pomodoro=self.pomodoro_service.is_active,
            tasks=tasks,
            current_task=task,
            extensions=self.extensions,
        )
        if self.menu_builder.should_update(items):
            self.renderer.update_menu(items)

    def reload_data(self) -> None:
        """重新加载数据并刷新显示（供外部调用）"""
        self.task_service.refresh_scheduler()
        self._update_display()

    # ==========================================
    # 信号回调
    # ==========================================

    def _on_pomodoro_tick(self, seconds: int) -> None:
        self._update_display()

    def _on_pomodoro_end(self) -> None:
        self.renderer.show_notification("专注结束", "番茄钟已完成，休息一下吧！")

    def _on_script_log(self, log: str) -> None:
        """脚本日志回调：短暂显示在状态栏"""
        self.renderer.set_text(log[:50])
