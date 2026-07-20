# tests/conftest.py
"""
pytest 配置 —— 隔离数据目录，避免污染用户真实数据。
"""
import os
import pytest
from pathlib import Path

from zentray.core.models import Task
from zentray.core.scheduler import Scheduler
from zentray.repositories.file_repository import FileTaskRepository
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository
from zentray.services.task_service import TaskService


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """将 DATA_DIR 与相关路径指到临时目录。"""
    data = tmp_path / "data"
    data.mkdir()
    archive = data / "archive"
    archive.mkdir()

    monkeypatch.setattr("zentray.config.DATA_DIR", data)
    monkeypatch.setattr("zentray.config.ACTIVE_TASKS_FILE", data / "active_tasks.json")
    monkeypatch.setattr(
        "zentray.config.PERIODIC_TEMPLATES_FILE", data / "periodic_templates.json"
    )
    monkeypatch.setattr("zentray.config.ARCHIVE_DIR", archive)
    monkeypatch.setattr(
        "zentray.services.settings_manager.SETTINGS_FILE", data / "settings.json"
    )
    monkeypatch.setattr(
        "zentray.services.settings_manager.DATA_DIR", data
    )

    # 重置 SettingsManager 单例
    from zentray.services.settings_manager import SettingsManager

    SettingsManager._instance = None
    return data


@pytest.fixture
def task_repo(tmp_data_dir):
    return FileTaskRepository(
        active_file=tmp_data_dir / "active_tasks.json",
        archive_dir=tmp_data_dir / "archive",
    )


@pytest.fixture
def template_repo(tmp_data_dir):
    return FilePeriodicTemplateRepository(
        filepath=tmp_data_dir / "periodic_templates.json"
    )


@pytest.fixture
def task_service(task_repo, template_repo):
    return TaskService(task_repo, template_repo, Scheduler())


@pytest.fixture
def sample_task() -> Task:
    return Task(
        title="测试任务",
        category="工作",
        priority="high",
        details="这是一个测试任务",
    )
