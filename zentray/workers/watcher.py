import datetime
import time
import uuid

from PySide6.QtCore import QThread, Signal

from zentray.core.models import Task
from zentray.core.periodic import (
    compute_instance_deadline,
    period_display_prefix,
    should_spawn,
    spawn_key_after_create,
)
from zentray.core.repository import PeriodicTemplateRepository, TaskRepository


class WatcherWorker(QThread):
    """
    后台守护线程：每分钟扫描逾期（惩罚或自动废弃）与周期派发。
    """
    tasks_updated = Signal()
    task_overdue = Signal(object)

    def __init__(
        self,
        task_repo: TaskRepository,
        template_repo: PeriodicTemplateRepository = None,
    ):
        super().__init__()
        self.is_running = True
        self.task_repo = task_repo
        self.template_repo = template_repo

    def run(self):
        while self.is_running:
            self._do_maintenance()
            for _ in range(60):
                if not self.is_running:
                    break
                time.sleep(1)

    def _do_maintenance(self):
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        overdue_emits = []
        abandon_ids = []

        def mutate_tasks(tasks):
            changed = False
            remaining = []
            for task in tasks:
                if not task.deadline:
                    remaining.append(task)
                    continue
                try:
                    deadline_date = datetime.datetime.strptime(
                        task.deadline, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    remaining.append(task)
                    continue

                if today <= deadline_date:
                    remaining.append(task)
                    continue

                # 已逾期
                if getattr(task, "auto_abandon_on_overdue", False):
                    abandon_ids.append(task)
                    changed = True
                    continue

                if task.overdue_penalty_date != today_str:
                    pri = task.priority
                    task.priority = "medium" if pri == "low" else "high"
                    task.deadline = (
                        deadline_date + datetime.timedelta(days=1)
                    ).strftime("%Y-%m-%d")
                    task.overdue_penalty_date = today_str
                    changed = True
                    overdue_emits.append(task)
                remaining.append(task)

            if abandon_ids:
                tasks[:] = remaining
                return True
            if changed:
                tasks[:] = remaining
            return changed

        if hasattr(self.task_repo, "mutate_all"):
            task_changed = self.task_repo.mutate_all(mutate_tasks)
        else:
            tasks = self.task_repo.find_all()
            task_changed = mutate_tasks(tasks)
            if task_changed:
                self.task_repo.save_all(tasks)

        # 归档自动废弃（在锁外写 archive，避免嵌套复杂）
        for task in abandon_ids:
            try:
                self.task_repo.archive(task, "ABANDONED_OVERDUE")
            except Exception:
                pass
            # 确保已从 active 删除（mutate 已移除；若无 mutate 路径需 delete）
            if self.task_repo.find_by_id(task.id):
                self.task_repo.delete(task.id)
            task_changed = True

        for task in overdue_emits:
            self.task_overdue.emit(task)

        # 周期任务派发
        tmpl_changed = False
        templates = self.template_repo.find_all() if self.template_repo else []
        new_instances = []

        for tmpl in templates:
            if not should_spawn(tmpl, today):
                continue
            prefix = period_display_prefix(
                tmpl.periodicity, today, getattr(tmpl, "interval", 1) or 1
            )
            deadline = compute_instance_deadline(tmpl, today)
            new_task = Task(
                id=str(uuid.uuid4()),
                title=f"【{prefix}】{tmpl.base_title}",
                category=tmpl.category,
                details=tmpl.details,
                priority=tmpl.priority,
                deadline=deadline or "",
                task_type="periodic_instance",
                template_id=tmpl.template_id,
                category_primary_id=getattr(tmpl, "category_primary_id", None),
                category_secondary_id=getattr(tmpl, "category_secondary_id", None),
                reminder=getattr(tmpl, "reminder", None),
                auto_abandon_on_overdue=bool(
                    getattr(tmpl, "auto_abandon_on_overdue", False)
                ),
            )
            new_instances.append(new_task)
            tmpl.last_generated_period = spawn_key_after_create(tmpl, today)
            tmpl_changed = True

        if new_instances:
            def append_instances(tasks):
                tasks.extend(new_instances)
                return True

            if hasattr(self.task_repo, "mutate_all"):
                self.task_repo.mutate_all(append_instances)
            else:
                tasks = self.task_repo.find_all()
                tasks.extend(new_instances)
                self.task_repo.save_all(tasks)
            task_changed = True

        if tmpl_changed and self.template_repo:
            self.template_repo.save_all(templates)

        if task_changed or tmpl_changed:
            self.tasks_updated.emit()

    def stop(self):
        self.is_running = False
        self.wait()
