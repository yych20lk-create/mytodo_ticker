# tests/unit/test_template_repository.py
import pytest
from zentray.core.repository import PeriodicTemplateRepository


def test_template_repository_interface():
    """验证 PeriodicTemplateRepository 是抽象类，无法直接实例化"""
    with pytest.raises(TypeError):
        PeriodicTemplateRepository()
