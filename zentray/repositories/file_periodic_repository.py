# zentray/repositories/file_periodic_repository.py
from pathlib import Path
from typing import List

from zentray.config import PERIODIC_TEMPLATES_FILE
from zentray.core.file_io import load_json_list, save_json_list
from zentray.core.models import PeriodicTemplate
from zentray.core.repository import PeriodicTemplateRepository


class FilePeriodicTemplateRepository(PeriodicTemplateRepository):
    """基于 JSON 文件的周期任务模板存储实现"""

    def __init__(self, filepath: Path | None = None):
        self.filepath = Path(filepath) if filepath else PERIODIC_TEMPLATES_FILE

    def find_all(self) -> List[PeriodicTemplate]:
        data = load_json_list(self.filepath)
        return [PeriodicTemplate.from_dict(d) for d in data]

    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        save_json_list(self.filepath, [t.to_dict() for t in templates])
