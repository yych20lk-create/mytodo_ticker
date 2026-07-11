# tests/unit/test_file_periodic_repository.py
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository
from zentray.core.models import PeriodicTemplate
import os


def test_template_save_and_load():
    """验证周期模板的保存与加载功能"""
    repo = FilePeriodicTemplateRepository()
    template = PeriodicTemplate(
        base_title="每日站会",
        category="工作",
        periodicity="daily"
    )
    repo.save_all([template])
    loaded = repo.find_all()
    assert len(loaded) == 1
    assert loaded[0].base_title == "每日站会"
    assert loaded[0].periodicity == "daily"

    # 清理测试文件
    if repo.filepath.exists():
        os.remove(repo.filepath)


def test_load_empty_when_file_missing():
    """验证文件不存在时返回空列表"""
    repo = FilePeriodicTemplateRepository()
    # 确保文件不存在
    if repo.filepath.exists():
        os.remove(repo.filepath)
    result = repo.find_all()
    assert result == []
