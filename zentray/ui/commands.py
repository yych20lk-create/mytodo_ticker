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
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog()
        if dialog.exec():
            data = dialog.get_data()
            controller.task_service.create_task(data)
            controller._update_display()


class DoneCommand(ActionCommand):
    """完成当前任务"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if task:
            controller.task_service.mark_done(task.id)
            controller._update_display()


class AbandonCommand(ActionCommand):
    """废弃当前任务"""

    def execute(self, controller: "TrayController") -> None:
        task = controller.task_service.get_current_task()
        if task:
            controller.task_service.abandon(task.id)
            controller._update_display()


class ProgressCommand(ActionCommand):
    """更新进度"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.dialogs import ProgressDialog

        task = controller.task_service.get_current_task()
        if task:
            dialog = ProgressDialog(task=task)
            if dialog.exec():
                percent, note = dialog.get_data()
                controller.task_service.update_progress(task.id, percent, note)
                controller._update_display()


class EditCommand(ActionCommand):
    """编辑当前任务"""

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.dialogs import TaskDialog

        task = controller.task_service.get_current_task()
        if task:
            dialog = TaskDialog(task=task)
            if dialog.exec():
                data = dialog.get_data()
                controller.task_service.update_task(task.id, data)
                controller._update_display()


class PomodoroStartCommand(ActionCommand):
    """开始番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        controller.pomodoro_service.start()
        controller._update_display()


class PomodoroStopCommand(ActionCommand):
    """中止番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        controller.pomodoro_service.stop()
        controller._update_display()


class PomodoroExtendCommand(ActionCommand):
    """延长番茄钟"""

    def execute(self, controller: "TrayController") -> None:
        controller.pomodoro_service.extend()
        controller._update_display()


class QuitCommand(ActionCommand):
    """退出程序"""

    def execute(self, controller: "TrayController") -> None:
        controller.app.quit()


# ==========================================
# 任务列表命令
# ==========================================

class TaskActionCommand(ActionCommand):
    """任务列表中的操作（弹出操作对话框）"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def execute(self, controller: "TrayController") -> None:
        from zentray.ui.dialogs import TaskActionDialog

        task = controller.task_service.task_repo.find_by_id(self.task_id)
        if task:
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
        controller._update_display()


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
    "pomodoro": PomodoroStartCommand(),
    "stop_pomodoro": PomodoroStopCommand(),
    "extend_pomodoro": PomodoroExtendCommand(),
    "quit": QuitCommand(),
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

    # 3. 未识别的命令
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
        from zentray.ui.dialogs import TaskDialog

        dialog = TaskDialog(task=task)
        if dialog.exec():
            data = dialog.get_data()
            controller.task_service.update_task(task.id, data)
    elif action == "progress":
        from zentray.ui.dialogs import ProgressDialog

        dialog = ProgressDialog(task=task)
        if dialog.exec():
            percent, note = dialog.get_data()
            controller.task_service.update_progress(task.id, percent, note)
    elif action == "select":
        controller.task_service.select_task(task.id)

    controller._update_display()
