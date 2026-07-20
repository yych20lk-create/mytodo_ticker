# tests/unit/test_injector.py
from zentray.dependencies import injector
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.repositories.file_repository import FileTaskRepository
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository
from zentray.services.task_service import TaskService


def test_task_repository_injection():
    repo = injector.get(TaskRepository)
    assert isinstance(repo, FileTaskRepository)


def test_template_repository_injection():
    repo = injector.get(PeriodicTemplateRepository)
    assert isinstance(repo, FilePeriodicTemplateRepository)


def test_singleton_same_instance():
    repo1 = injector.get(TaskRepository)
    repo2 = injector.get(TaskRepository)
    assert repo1 is repo2


def test_task_service_injection():
    svc = injector.get(TaskService)
    assert isinstance(svc, TaskService)


def test_init_tray_renderer_no_bindings_crash():
    """真实 injector 下 init_tray_renderer 不得访问私有 _bindings。"""
    from zentray.dependencies import init_tray_renderer

    # 无 QApplication 时 create_tray_backend 可能失败；至少验证绑定路径不引用 _bindings
    import inspect
    src = inspect.getsource(init_tray_renderer)
    assert "injector._bindings" not in src
