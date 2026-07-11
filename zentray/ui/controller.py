# zentray/ui/controller.py
"""
托盘协调者 —— 事件路由 + 状态协调 + 扩展管理。

将原 TrayManager 拆分为：
  - TrayController（本文件）：协调者，负责事件路由
  - TrayRenderer：封装托盘底层渲染
  - MenuBuilder：负责菜单结构生成
"""
from typing import Optional
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.services.script_service import ScriptService
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

        # 加载扩展
        self.extensions = self.extension_loader.load_all()

        # 连接番茄钟信号
        self.pomodoro_service.time_updated.connect(self._on_pomodoro_tick)
        self.pomodoro_service.pomodoro_finished.connect(self._on_pomodoro_end)

        # 连接脚本日志信号
        self.script_service.log_updated.connect(self._on_script_log)

        # 启动轮播定时器
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._update_display)
        self.poll_timer.start(POLLING_INTERVAL_MS)

        # 应用退出时关闭托盘
        self.app.aboutToQuit.connect(self.renderer.shutdown)

    # ==========================================
    # 事件路由（后续 Task 9 将替换为命令模式）
    # ==========================================

    def handle_action(self, action_id: str) -> None:
        """中央事件路由 —— 通过命令模式分发"""
        from .commands import dispatch

        if not dispatch(action_id, self):
            # 未识别的命令，静默忽略
            pass

    # ==========================================
    # 显示更新
    # ==========================================

    def _update_display(self) -> None:
        """更新状态栏显示（由定时器触发）"""
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
        """番茄钟每秒回调"""
        self._update_display()

    def _on_pomodoro_end(self) -> None:
        """番茄钟结束回调"""
        self.renderer.show_notification("专注结束", "番茄钟已完成，休息一下吧！")

    def _on_script_log(self, log: str) -> None:
        """脚本日志回调：短暂显示在状态栏"""
        self.renderer.set_text(log[:50])
