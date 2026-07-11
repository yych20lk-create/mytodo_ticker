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


class AppModule(Module):
    """应用依赖注入模块配置"""

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

    # ==========================================
    # 以下 provider 将在后续任务中逐步添加:
    # - provide_task_service (Task 6)
    # - provide_pomodoro_service (Task 7)
    # - provide_renderer (Task 8)
    # - provide_extension_loader (Task 8)
    # - provide_qapplication (Task 10)
    # ==========================================


# 全局 injector 实例
injector = Injector([AppModule()])
