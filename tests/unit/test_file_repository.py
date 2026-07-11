# tests/unit/test_file_repository.py
from zentray.repositories.file_repository import FileTaskRepository
from zentray.core.models import Task
import pytest
import os
import shutil
from pathlib import Path

def test_save_and_load_task():
    repo = FileTaskRepository()
    task = Task(id="test-1", title="test task")
    repo.save_all([task])
    loaded = repo.find_all()
    assert len(loaded) == 1
    assert loaded[0].title == "test task"

    # Clean up
    os.remove(repo.active_file)
    os.remove(repo.active_file.with_suffix('.json.bak'))