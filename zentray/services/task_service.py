# zentray/services/task_service.py
"""
任务管理服务 —— 封装所有任务相关业务逻辑。

将原 TrayManager 中的任务 CRUD、进度更新、完成/废弃等操作
抽取为独立服务，通过依赖注入与 UI 层解耦。
"""
import datetime
from typing import List, Optional
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.core.models import Task, PeriodicTemplate
from zentray.core.scheduler import Scheduler


class TaskService:
    """任务管理服务"""

    def __init__(
        self,
        task_repo: TaskRepository,
        template_repo: PeriodicTemplateRepository,
        scheduler: Scheduler,
    ):
        self.task_repo = task_repo
        self.template_repo = template_repo
        self.scheduler = scheduler

    # ==========================================
    # 查询方法
    # ==========================================

    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return self.task_repo.find_all()

    def get_current_task(self) -> Optional[Task]:
        """获取当前轮播焦点任务"""
        return self.scheduler.get_current()

    def get_all_templates(self) -> List[PeriodicTemplate]:
        """获取所有周期任务模板"""
        return self.template_repo.find_all()

    # ==========================================
    # 任务 CRUD
    # ==========================================

    def create_task(self, task_data: dict) -> Task:
        """创建新任务并刷新调度器"""
        task = Task(**task_data)
        tasks = self.task_repo.find_all()
        tasks.append(task)
        self.task_repo.save_all(tasks)
        self._refresh_scheduler()
        return task

    def update_task(self, task_id: str, task_data: dict) -> Optional[Task]:
        """更新任务字段并刷新调度器"""
        tasks = self.task_repo.find_all()
        for i, t in enumerate(tasks):
            if t.id == task_id:
                updated = Task(**{**t.to_dict(), **task_data})
                tasks[i] = updated
                self.task_repo.save_all(tasks)
                self._refresh_scheduler()
                return updated
        return None

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.delete(task_id)
            self._refresh_scheduler()
            return True
        return False

    # ==========================================
    # 任务状态操作
    # ==========================================

    def select_task(self, task_id: str) -> None:
        """将指定任务设为当前轮播焦点"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.scheduler.build_queue([task])

    def mark_done(self, task_id: str) -> None:
        """完成任务：归档 + 删除"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "DONE")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()

    def abandon(self, task_id: str) -> None:
        """废弃任务：归档 + 删除"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "ABANDONED")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()

    def update_progress(self, task_id: str, percent: int, note: str = "") -> Optional[Task]:
        """更新任务进度百分比和日志"""
        tasks = self.task_repo.find_all()
        for i, t in enumerate(tasks):
            if t.id == task_id:
                t.progress = max(0, min(100, percent))
                t.progress_logs.append({
                    "time": datetime.datetime.now().isoformat(),
                    "percent": t.progress,
                    "note": note,
                })
                tasks[i] = t
                self.task_repo.save_all(tasks)
                return t
        return None

    # ==========================================
    # 模板操作
    # ==========================================

    def save_templates(self, templates: List[PeriodicTemplate]) -> None:
        """保存周期任务模板"""
        self.template_repo.save_all(templates)

    # ==========================================
    # 内部方法
    # ==========================================

    def refresh_scheduler(self) -> None:
        """刷新调度器队列（供外部调用，如 watcher 更新后）"""
        self._refresh_scheduler()

    def _refresh_scheduler(self) -> None:
        """重新从存储加载活跃任务并构建调度队列"""
        tasks = self.task_repo.find_active()
        self.scheduler.build_queue(tasks)
