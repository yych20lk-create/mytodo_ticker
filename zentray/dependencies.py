# zentray/dependencies.py
"""
依赖注入模块配置。

优先级：标准 injector 库 > 自定义 di.py 回退。
"""
try:
    from injector import Module, provider, singleton, Injector
except ImportError:
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
        # 初始时长来自 settings，而非写死 config 常量
        try:
            from zentray.services.settings_manager import SettingsManager

            mins = SettingsManager().pomodoro.duration_minutes
            return PomodoroService(mins)
        except Exception:
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


def init_tray_renderer(app) -> TrayRenderer:
    """在 QApplication 创建后初始化托盘渲染器。"""
    from zentray.ui.tray import create_tray_backend

    backend = create_tray_backend(app)
    renderer = TrayRenderer(backend)

    # 若使用真实 injector，尝试注册实例（失败不影响启动）
    try:
        from injector import InstanceProvider, singleton as singleton_scope

        injector.binder.bind(
            TrayRenderer, to=InstanceProvider(renderer), scope=singleton_scope
        )
    except Exception:
        pass

    return renderer


def init_tray_controller(app) -> "TrayController":
    """在 QApplication 和 TrayRenderer 创建后初始化 TrayController。"""
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
