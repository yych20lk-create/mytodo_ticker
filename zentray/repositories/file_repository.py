# zentray/repositories/file_repository.py
import json
import shutil
import datetime
from pathlib import Path
from typing import List, Optional
from zentray.core.repository import TaskRepository
from zentray.core.models import Task
from zentray.config import ACTIVE_TASKS_FILE, ARCHIVE_DIR

class FileTaskRepository(TaskRepository):
    def __init__(self):
        self.active_file = ACTIVE_TASKS_FILE
        self.archive_dir = ARCHIVE_DIR

    def _load_json(self, filepath: Path) -> List[dict]:
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Backup damaged file
            backup = filepath.with_suffix('.json.bak')
            shutil.copy(filepath, backup)
            return []

    def _save_json(self, filepath: Path, data: List[dict]) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def find_all(self) -> List[Task]:
        data = self._load_json(self.active_file)
        return [Task.from_dict(d) for d in data]

    def find_by_id(self, task_id: str) -> Optional[Task]:
        tasks = self.find_all()
        return next((t for t in tasks if t.id == task_id), None)

    def save_all(self, tasks: List[Task]) -> None:
        data = [t.to_dict() for t in tasks]
        self._save_json(self.active_file, data)

    def delete(self, task_id: str) -> None:
        tasks = self.find_all()
        tasks = [t for t in tasks if t.id != task_id]
        self.save_all(tasks)

    def find_active(self) -> List[Task]:
        return self.find_all()

    def archive(self, task: Task, status: str) -> None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        archive_file = self.archive_dir / f"{date_str}.log"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [状态: {status}] [分类: {task.category}] [{task.priority.upper()}] {task.title} - {task.details} (附件数: {len(task.attachments)})\n"
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
