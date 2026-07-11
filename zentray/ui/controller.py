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
        """中央事件路由"""
        # 当前版本保留简单的 if-elif 路由
        # Task 9 将替换为命令模式
        if action_id == "new":
            self._open_new_task_dialog()
        elif action_id == "done":
            self._mark_done()
        elif action_id == "abandon":
            self._abandon()
        elif action_id == "progress":
            self._update_progress_dialog()
        elif action_id == "edit":
            self._edit_current_task()
        elif action_id == "pomodoro":
            self.pomodoro_service.start()
        elif action_id == "stop_pomodoro":
            self.pomodoro_service.stop()
        elif action_id == "extend_pomodoro":
            self.pomodoro_service.extend()
        elif action_id == "quit":
            self.app.quit()
        elif action_id.startswith("task_action_"):
            pass  # 将在命令模式中处理
        elif action_id.startswith("extension_"):
            self._execute_extension(action_id)

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
        # 截断过长的日志，只显示前 50 个字符
        self.renderer.set_text(log[:50])

    # ==========================================
    # 内部操作方法（桩实现，Task 9 完善）
    # ==========================================

    def _open_new_task_dialog(self) -> None:
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog()
        if dialog.exec():
            data = dialog.get_data()
            self.task_service.create_task(data)
            self._update_display()

    def _mark_done(self) -> None:
        task = self.task_service.get_current_task()
        if task:
            self.task_service.mark_done(task.id)
            self._update_display()

    def _abandon(self) -> None:
        task = self.task_service.get_current_task()
        if task:
            self.task_service.abandon(task.id)
            self._update_display()

    def _update_progress_dialog(self) -> None:
        from zentray.ui.dialogs import ProgressDialog

        task = self.task_service.get_current_task()
        if task:
            dialog = ProgressDialog(task=task)
            if dialog.exec():
                percent, note = dialog.get_data()
                self.task_service.update_progress(task.id, percent, note)
                self._update_display()

    def _edit_current_task(self) -> None:
        from zentray.ui.dialogs import TaskDialog

        task = self.task_service.get_current_task()
        if task:
            dialog = TaskDialog(task=task)
            if dialog.exec():
                data = dialog.get_data()
                self.task_service.update_task(task.id, data)
                self._update_display()

    def _execute_extension(self, action_id: str) -> None:
        """执行扩展按钮"""
        ext_name = action_id[len("extension_"):]
        for ext in self.extensions:
            if ext.__class__.__name__ == ext_name:
                ext.handle_click()
                break
