# tests/unit/test_injector.py
from zentray.dependencies import injector
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.repositories.file_repository import FileTaskRepository
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository


def test_task_repository_injection():
    """验证 TaskRepository 能正确注入"""
    repo = injector.get(TaskRepository)
    assert isinstance(repo, FileTaskRepository)


def test_template_repository_injection():
    """验证 PeriodicTemplateRepository 能正确注入"""
    repo = injector.get(PeriodicTemplateRepository)
    assert isinstance(repo, FilePeriodicTemplateRepository)


def test_singleton_same_instance():
    """验证单例模式：多次获取返回同一实例"""
    repo1 = injector.get(TaskRepository)
    repo2 = injector.get(TaskRepository)
    assert repo1 is repo2
