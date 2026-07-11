# tests/unit/test_repository.py
import pytest
from zentray.core.repository import TaskRepository

def test_repository_interface():
    with pytest.raises(TypeError):
        TaskRepository()  # Abstract class can't be instantiated