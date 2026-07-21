# zentray/ui/commands.py
"""
命令模式 —— 将托盘菜单事件路由从 if-elif 链替换为独立命令对象。

每个菜单项对应一个 ActionCommand 子类，在 TrayController 中
通过命令映射字典进行路由，支持后续动态注册扩展命令。
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TrayController


class ActionCommand(ABC):
    """命令基类"""

    @abstractmethod
    def execute(self, controller: "TrayController") -> None:
        """执行命令"""
        pass


# ==========================================
# 核心命令
# ==========================================

class NewTaskCommand(ActionCommand):
    """新建任务"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.vue_commands import try_vue_new_task

        if try_vue_new_task(controller):
            return
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog()
        if dialog.exec():
            data = dialog.get_data()
            controller.task_service.create_task(data)
            controller.update_display()


class DoneCommand(ActionCommand):
    """完成当前任务"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if task:
            controller.task_service.mark_done(task.id)
            controller.update_display()


class AbandonCommand(ActionCommand):
    """废弃当前任务"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if task:
            controller.task_service.abandon(task.id)
            controller.update_display()


class ProgressCommand(ActionCommand):
    """更新进度（当前轮播任务）"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if task:
            _run_progress_dialog(controller, task)


class TaskListCommand(ActionCommand):
    """打开任务列表面板（左列表 + 右操作）"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.vue_commands import try_vue_task_list

        if try_vue_task_list(controller):
            return
        from zentray.ui.task_list_dialog import TaskListDialog

        dialog = TaskListDialog(controller.task_service)
        if not dialog.exec():
            return
        result = dialog.get_selected_action()
        if not result:
            return
        action, task_id = result
        task = controller.task_service.find_task(task_id)
        if not task:
            controller.update_display()
            return
        _dispatch_task_action(action, task, controller)


def _run_progress_dialog(controller: "TrayController", task) -> None:
    from zentray.ui.vue_commands import try_vue_progress

    if try_vue_progress(controller, task):
        return
    from zentray.ui.dialogs import ProgressDialog

    dialog = ProgressDialog(task=task)
    if not dialog.exec():
        return
    action = getattr(dialog, "result_action", "save")
    if action == "done":
        controller.task_service.mark_done(task.id)
    elif action == "abandon":
        controller.task_service.abandon(task.id)
    else:
        percent, note = dialog.get_data()
        controller.task_service.update_progress(task.id, percent, note)
    controller.update_display()


class EditCommand(ActionCommand):
    """编辑当前任务（一次性或周期实例，均可完整编辑）"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if not task:
            return
        fresh = controller.task_service.find_task(task.id) or task
        from zentray.ui.vue_commands import try_vue_edit_task

        if try_vue_edit_task(controller, fresh):
            return
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog(task=fresh)
        if dialog.exec():
            data = dialog.get_data()
            # 保留实例类型，勿被表单误改成 one-time 丢 template_id
            if getattr(fresh, "task_type", None) == "periodic_instance":
                data["task_type"] = "periodic_instance"
                data["template_id"] = fresh.template_id
            controller.task_service.update_task(task.id, data)
            controller.update_display()


class PomodoroStartCommand(ActionCommand):
    """开始番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        if getattr(controller, "plugin_runtime", None) and controller.plugin_runtime.is_busy:
            controller.renderer.show_notification(
                "番茄钟", "脚本运行中，请稍后再开始专注。"
            )
            return
        if getattr(controller, "_ops_active", False):
            controller.renderer.show_notification(
                "番茄钟", "运维脚本占用托盘中，请稍后再开始专注。"
            )
            return
        controller.pomodoro_service.start()
        controller.update_display()


class PomodoroStopCommand(ActionCommand):
    """中止番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        controller.pomodoro_service.stop()
        controller.update_display()


class PomodoroExtendCommand(ActionCommand):
    """延长番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        controller.pomodoro_service.extend()
        controller.update_display()


class QuitCommand(ActionCommand):
    """退出程序"""

    def execute(self, controller: "TrayController") -> None:
        controller.app.quit()


class SettingsCommand(ActionCommand):
    """打开设置对话框"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.vue_commands import try_vue_settings

        if try_vue_settings(controller):
            return
        from zentray.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        if dialog.exec():
            # 设置已保存，刷新控制器以应用新设置
            controller.apply_settings()
            controller.update_display()


class HistoryCommand(ActionCommand):
    """历史记录：任务操作日志 + AI 报告"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.vue_commands import try_vue_history

        if try_vue_history(controller):
            return
        from zentray.ui.web_host import use_vue_ui

        if not use_vue_ui():
            controller.renderer.show_notification(
                "历史记录",
                "请构建 Vue 前端（web/dist）后使用历史记录功能。",
            )


class PeriodicManageCommand(ActionCommand):
    """周期任务管理"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.vue_commands import try_vue_periodic

        if try_vue_periodic(controller):
            return
        from zentray.ui.periodic_manager import PeriodicManagerDialog

        dialog = PeriodicManagerDialog(controller.task_service)
        dialog.exec()
        controller.reload_data()


class AiReviewNowCommand(ActionCommand):
    """立即执行 AI 复盘（不受「每天一次 / 周末节假日跳过」限制）。"""

    def execute(self, controller: "TrayController") -> None:
        import datetime
        import logging

        from zentray.services.settings_manager import SettingsManager
        from zentray.workers.nightly_job import execute_nightly_review

        log = logging.getLogger(__name__)
        sm = SettingsManager()
        if not sm.is_ai_configured() and not sm.is_notification_configured():
            controller.renderer.show_notification(
                "AI 复盘",
                "请先在设置中配置 AI API Key（建议同时配置 WxPusher 推送）。",
            )
            return

        controller.renderer.show_notification("AI 复盘", "正在生成复盘，请稍候…")
        today = datetime.date.today().isoformat()
        try:
            ok = execute_nightly_review(today, controller.task_service.task_repo)
            if ok:
                controller.renderer.show_notification(
                    "AI 复盘",
                    "复盘已完成。本地 reviews/ 或微信推送请查看结果。",
                )
            else:
                controller.renderer.show_notification(
                    "AI 复盘",
                    "复盘已执行，但推送可能失败；请查看本地 reviews/ 目录。",
                )
        except Exception as e:
            log.exception("立即 AI 复盘失败")
            controller.renderer.show_notification("AI 复盘失败", str(e)[:120])


# ==========================================
# 任务列表命令
# ==========================================

class TaskActionCommand(ActionCommand):
    """任务列表中的操作（弹出操作对话框）"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.find_task(self.task_id)
        if not task:
            return
        from zentray.ui.vue_commands import try_vue_task_action

        if try_vue_task_action(controller, task):
            return
        from zentray.ui.dialogs import TaskActionDialog

        dialog = TaskActionDialog(task=task)
        if dialog.exec():
            action = dialog.get_selected_action()
            if action:
                _dispatch_task_action(action, task, controller)


class SelectTaskCommand(ActionCommand):
    """切换到指定任务"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def execute(self, controller: "TrayController") -> None:
        controller.task_service.select_task(self.task_id)
        controller.update_display()


# ==========================================
# 扩展命令
# ==========================================

class ExtensionCommand(ActionCommand):
    """执行扩展按钮"""

    def __init__(self, ext_class_name: str):
        self.ext_class_name = ext_class_name

    def execute(self, controller: "TrayController") -> None:
        for ext in controller.extensions:
            if ext.__class__.__name__ == self.ext_class_name:
                ext.handle_click()
                break


# ==========================================
# 命令注册与路由
# ==========================================

# 静态命令映射
COMMAND_MAP = {
    "new": NewTaskCommand(),
    "done": DoneCommand(),
    "abandon": AbandonCommand(),
    "progress": ProgressCommand(),
    "edit": EditCommand(),
    "task_list": TaskListCommand(),
    "pomodoro": PomodoroStartCommand(),
    "stop_pomodoro": PomodoroStopCommand(),
    "extend_pomodoro": PomodoroExtendCommand(),
    "periodic_manage": PeriodicManageCommand(),
    "ai_review_now": AiReviewNowCommand(),
    "history": HistoryCommand(),
    "quit": QuitCommand(),
    "settings": SettingsCommand(),
}


def dispatch(action_id: str, controller: "TrayController") -> bool:
    """
    根据 action_id 分发命令。

    Returns:
        bool: 是否成功分发
    """
    # 1. 检查静态命令
    if action_id in COMMAND_MAP:
        COMMAND_MAP[action_id].execute(controller)
        return True

    # 2. 解析带参数的动态命令
    if action_id.startswith("task_action_"):
        task_id = action_id[len("task_action_"):]
        TaskActionCommand(task_id).execute(controller)
        return True

    if action_id.startswith("select_task_"):
        task_id = action_id[len("select_task_"):]
        SelectTaskCommand(task_id).execute(controller)
        return True

    if action_id.startswith("extension_"):
        ext_name = action_id[len("extension_"):]
        ExtensionCommand(ext_name).execute(controller)
        return True

    if action_id.startswith("ops."):
        return _dispatch_ops_action(action_id, controller)

    # 3. 未识别的命令
    return False


def _dispatch_ops_action(action_id: str, controller: "TrayController") -> bool:
    """插件菜单。"""
    from PySide6.QtWidgets import QMessageBox

    if action_id in ("ops._empty", "ops._hdr_scripts", "ops._hdr_services", "ops_menu"):
        return True

    if action_id == "ops.open_last_log":
        from pathlib import Path
        import subprocess
        import sys

        from zentray.config import DATA_DIR

        last = DATA_DIR / "ops_runs" / "last.json"
        if not last.is_file():
            controller.renderer.show_notification("插件", "尚无运行记录")
            return True
        try:
            import json

            data = json.loads(last.read_text(encoding="utf-8"))
            log_path = Path(data.get("log") or "")
            if log_path.is_file():
                if sys.platform.startswith("linux"):
                    subprocess.Popen(["xdg-open", str(log_path)])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(log_path)])
                else:
                    subprocess.Popen(["cmd", "/c", "start", "", str(log_path)])
            else:
                controller.renderer.show_notification(
                    "插件", data.get("summary") or "无日志文件"
                )
        except Exception as e:
            controller.renderer.show_notification("打开日志失败", str(e)[:100])
        return True

    runtime = getattr(controller, "plugin_runtime", None)
    loader = getattr(controller, "plugin_loader", None)
    if runtime is None or loader is None:
        return False

    if action_id.startswith("ops.script."):
        pid = action_id[len("ops.script.") :]
        plug = loader.get(pid)
        if not plug:
            controller.renderer.show_notification("插件", f"插件不存在: {pid}")
            return True
        if controller.pomodoro_service.is_active:
            controller.renderer.show_notification(
                "插件", "番茄钟进行中，请先结束专注。"
            )
            return True
        sm = controller._settings
        if sm.ops.confirm_before_run:
            ret = QMessageBox.question(
                None,
                "运行脚本",
                f"确定运行「{plug.manifest.name}」？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return True
        runtime.run_script(
            plug, pomodoro_active=controller.pomodoro_service.is_active
        )
        return True

    if action_id.startswith("ops.service."):
        rest = action_id[len("ops.service.") :]
        # id.action 或 仅 id（打开时无）
        if rest.endswith(".start"):
            pid, act = rest[: -len(".start")], "start"
        elif rest.endswith(".stop"):
            pid, act = rest[: -len(".stop")], "stop"
        elif rest.endswith(".status"):
            pid, act = rest[: -len(".status")], "status"
        else:
            return True
        plug = loader.get(pid)
        if not plug:
            controller.renderer.show_notification("插件", f"插件不存在: {pid}")
            return True
        if act in ("start", "stop") and controller.pomodoro_service.is_active:
            controller.renderer.show_notification(
                "插件", "番茄钟进行中，请先结束专注。"
            )
            return True
        ok = runtime.service_cmd(
            plug, act, pomodoro_active=controller.pomodoro_service.is_active
        )
        controller.renderer.show_notification(
            plug.manifest.name,
            f"{act} " + ("成功" if ok else "失败"),
        )
        return True

    return False


# ==========================================
# 内部辅助
# ==========================================

def _dispatch_task_action(action: str, task, controller: "TrayController") -> None:
    """任务操作对话框的结果分发"""
    if action == "done":
        controller.task_service.mark_done(task.id)
    elif action == "abandon":
        controller.task_service.abandon(task.id)
    elif action == "edit":
        from zentray.ui.vue_commands import try_vue_edit_task

        if try_vue_edit_task(controller, task):
            return
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog(task=task)
        if dialog.exec():
            data = dialog.get_data()
            if getattr(task, "task_type", None) == "periodic_instance":
                data["task_type"] = "periodic_instance"
                data["template_id"] = task.template_id
            controller.task_service.update_task(task.id, data)
    elif action == "progress":
        _run_progress_dialog(controller, task)
        return  # _run_progress_dialog 已 update_display
    elif action == "select":
        controller.task_service.select_task(task.id)

    controller.update_display()
