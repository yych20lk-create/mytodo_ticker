# zentray/repositories/file_periodic_repository.py
import json
from pathlib import Path
from typing import List
from zentray.core.repository import PeriodicTemplateRepository
from zentray.core.models import PeriodicTemplate
from zentray.config import PERIODIC_TEMPLATES_FILE


class FilePeriodicTemplateRepository(PeriodicTemplateRepository):
    """基于 JSON 文件的周期任务模板存储实现"""

    def __init__(self):
        self.filepath = PERIODIC_TEMPLATES_FILE

    def find_all(self) -> List[PeriodicTemplate]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [PeriodicTemplate.from_dict(d) for d in data]
        except json.JSONDecodeError:
            # 周期模板数据量较小，损坏概率低，直接返回空列表
            return []

    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in templates], f, indent=2, ensure_ascii=False)
