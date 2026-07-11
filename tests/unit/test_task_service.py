# tests/unit/test_task_service.py
"""
TaskService 单元测试
"""
import pytest
from zentray.dependencies import injector
from zentray.services.task_service import TaskService
from zentray.core.models import Task


@pytest.fixture
def task_service():
    """获取注入的 TaskService 实例"""
    return injector.get(TaskService)


class TestTaskService:
    """TaskService 核心功能测试"""

    def test_create_task(self, task_service):
        """验证创建任务"""
        task = task_service.create_task({
            "title": "测试任务",
            "category": "工作",
            "priority": "high",
        })
        assert task.id is not None
        assert task.title == "测试任务"

    def test_get_all_tasks_returns_list(self, task_service):
        """验证获取任务列表"""
        tasks = task_service.get_all_tasks()
        assert isinstance(tasks, list)

    def test_mark_done_removes_task(self, task_service):
        """验证完成任务后从活跃列表移除"""
        task = task_service.create_task({
            "title": "待完成的任务",
            "category": "学习",
            "priority": "medium",
        })
        task_id = task.id
        task_service.mark_done(task_id)
        remaining = task_service.get_all_tasks()
        assert not any(t.id == task_id for t in remaining)

    def test_update_progress(self, task_service):
        """验证更新进度"""
        task = task_service.create_task({
            "title": "进度测试",
            "category": "生活",
            "priority": "low",
        })
        updated = task_service.update_progress(task.id, 50, "完成一半")
        assert updated is not None
        assert updated.progress == 50
        assert len(updated.progress_logs) == 1
        assert updated.progress_logs[0]["percent"] == 50

    def test_abandon_removes_task(self, task_service):
        """验证废弃任务后从活跃列表移除"""
        task = task_service.create_task({
            "title": "要废弃的任务",
            "category": "工作",
            "priority": "low",
        })
        task_id = task.id
        task_service.abandon(task_id)
        remaining = task_service.get_all_tasks()
        assert not any(t.id == task_id for t in remaining)
