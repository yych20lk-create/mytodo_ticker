# zentray/dependencies.py
"""
依赖注入模块配置。

使用自定义 DI 容器（zentray/di.py），API 与 injector 库兼容。
当 pip 环境就绪后，可将 import 切换为标准的 injector 库。
"""
from zentray.di import Module, provider, singleton, Injector
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.repositories.file_repository import FileTaskRepository
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository
from zentray.config import STORAGE_BACKEND
from zentray.core.scheduler import Scheduler
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.services.script_service import ScriptService
from zentray.ui.renderer import TrayRenderer
from zentray.ui.menu_builder import MenuBuilder
from zentray.ui.extensions.loader import ExtensionLoader


class AppModule(Module):
    """应用依赖注入模块配置"""

    @provider
    @singleton
    def provide_scheduler(self) -> Scheduler:
        return Scheduler()

    @provider
    @singleton
    def provide_task_repository(self) -> TaskRepository:
        if STORAGE_BACKEND == "mysql":
            # 后续实现：MySQLTaskRepository
            raise NotImplementedError("MySQL 存储后端尚未实现")
        return FileTaskRepository()

    @provider
    @singleton
    def provide_template_repository(self) -> PeriodicTemplateRepository:
        return FilePeriodicTemplateRepository()

    @provider
    @singleton
    def provide_task_service(
        self,
        task_repo: TaskRepository,
        template_repo: PeriodicTemplateRepository,
        scheduler: Scheduler,
    ) -> TaskService:
        return TaskService(task_repo, template_repo, scheduler)

    @provider
    @singleton
    def provide_pomodoro_service(self) -> PomodoroService:
        return PomodoroService()

    @provider
    @singleton
    def provide_script_service(self) -> ScriptService:
        return ScriptService()

    @provider
    @singleton
    def provide_menu_builder(self) -> MenuBuilder:
        return MenuBuilder()

    @provider
    @singleton
    def provide_extension_loader(self) -> ExtensionLoader:
        return ExtensionLoader()


# 全局 injector 实例
injector = Injector([AppModule()])


# ==========================================
# 延迟绑定：需要在 QApplication 创建后初始化
# ==========================================

def init_tray_renderer(app) -> TrayRenderer:
    """在 QApplication 创建后初始化托盘渲染器"""
    from zentray.ui.tray import create_tray_backend
    from zentray.di import _Binding

    backend = create_tray_backend(app)
    renderer = TrayRenderer(backend)

    # 注册到 injector
    def _get_renderer():
        return renderer
    _get_renderer._is_provider = True
    _get_renderer._return_type = TrayRenderer
    _get_renderer._is_singleton = True
    injector._bindings[TrayRenderer] = _Binding(_get_renderer, is_singleton=True)

    return renderer


def init_tray_controller(app) -> "TrayController":
    """在 QApplication 和 TrayRenderer 创建后初始化 TrayController"""
    from zentray.ui.controller import TrayController

    task_service = injector.get(TaskService)
    pomodoro_service = injector.get(PomodoroService)
    script_service = injector.get(ScriptService)
    menu_builder = injector.get(MenuBuilder)
    extension_loader = injector.get(ExtensionLoader)

    renderer = init_tray_renderer(app)

    controller = TrayController(
        app=app,
        task_service=task_service,
        pomodoro_service=pomodoro_service,
        script_service=script_service,
        renderer=renderer,
        menu_builder=menu_builder,
        extension_loader=extension_loader,
    )
    return controller
