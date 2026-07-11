# tests/conftest.py
"""
pytest 配置文件 —— 提供测试夹具 (fixtures)。

为单元测试提供 DI 容器、Repository、Service 等共享实例。
"""
import pytest
from zentray.dependencies import injector
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.core.models import Task


@pytest.fixture
def task_repo() -> TaskRepository:
    """获取注入的 TaskRepository"""
    return injector.get(TaskRepository)


@pytest.fixture
def template_repo() -> PeriodicTemplateRepository:
    """获取注入的 PeriodicTemplateRepository"""
    return injector.get(PeriodicTemplateRepository)


@pytest.fixture
def task_service() -> TaskService:
    """获取注入的 TaskService"""
    return injector.get(TaskService)


@pytest.fixture
def pomodoro_service() -> PomodoroService:
    """获取注入的 PomodoroService"""
    return injector.get(PomodoroService)


@pytest.fixture
def sample_task() -> Task:
    """创建一个示例任务对象"""
    return Task(
        title="测试任务",
        category="工作",
        priority="high",
        details="这是一个测试任务",
    )
