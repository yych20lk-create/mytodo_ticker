# zentray/core/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from zentray.core.models import Task, PeriodicTemplate

class TaskRepository(ABC):
    @abstractmethod
    def find_all(self) -> List[Task]:
        pass

    @abstractmethod
    def find_by_id(self, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    def save(self, task: Task) -> None:
        pass

    @abstractmethod
    def save_all(self, tasks: List[Task]) -> None:
        pass

    @abstractmethod
    def delete(self, task_id: str) -> None:
        pass

    @abstractmethod
    def find_active(self) -> List[Task]:
        pass

    @abstractmethod
    def archive(self, task: Task, status: str) -> None:
        pass