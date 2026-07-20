# zentray/repositories/file_repository.py
import datetime
from pathlib import Path
from typing import List, Optional

from zentray.config import ACTIVE_TASKS_FILE, ARCHIVE_DIR
from zentray.core.file_io import append_text_line, load_json_list, path_lock, save_json_list
from zentray.core.models import Task
from zentray.core.repository import TaskRepository


class FileTaskRepository(TaskRepository):
    def __init__(self, active_file: Path | None = None, archive_dir: Path | None = None):
        self.active_file = Path(active_file) if active_file else ACTIVE_TASKS_FILE
        self.archive_dir = Path(archive_dir) if archive_dir else ARCHIVE_DIR

    def find_all(self) -> List[Task]:
        data = load_json_list(self.active_file)
        return [Task.from_dict(d) for d in data]

    def find_by_id(self, task_id: str) -> Optional[Task]:
        with path_lock(self.active_file):
            tasks = self.find_all()
            return next((t for t in tasks if t.id == task_id), None)

    def save(self, task: Task) -> None:
        """保存或更新单个任务（同一把锁下 read-modify-write）。"""
        with path_lock(self.active_file):
            tasks = self.find_all()
            for i, t in enumerate(tasks):
                if t.id == task.id:
                    tasks[i] = task
                    self.save_all(tasks)
                    return
            tasks.append(task)
            self.save_all(tasks)

    def save_all(self, tasks: List[Task]) -> None:
        data = [t.to_dict() for t in tasks]
        save_json_list(self.active_file, data)

    def delete(self, task_id: str) -> None:
        with path_lock(self.active_file):
            tasks = [t for t in self.find_all() if t.id != task_id]
            self.save_all(tasks)

    def find_active(self) -> List[Task]:
        # JSON 模式下 active 文件中的任务均为未归档任务
        return self.find_all()

    def mutate_all(self, mutator) -> bool:
        """
        在同一把锁内完成 read → mutate → write，避免跨线程丢失更新。

        mutator(tasks: List[Task]) -> bool  返回是否有修改。
        """
        with path_lock(self.active_file):
            tasks = self.find_all()
            changed = bool(mutator(tasks))
            if changed:
                self.save_all(tasks)
            return changed

    def archive(self, task: Task, status: str) -> None:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        archive_file = self.archive_dir / f"{date_str}.log"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = (
            f"[{timestamp}] [状态: {status}] [分类: {task.category}] "
            f"[{task.priority.upper()}] {task.title} - {task.details} "
            f"(附件数: {len(task.attachments)})\n"
        )
        append_text_line(archive_file, log_line)
