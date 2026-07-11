import sys
import os

# 将项目根目录（zentray 的上一级目录）加入系统路径，解决绝对导包的问题
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 修复 Linux 下无法唤出 Fcitx5 输入法的底层 BUG
if sys.platform.startswith('linux'):
    os.environ["QT_IM_MODULE"] = "ibus"
    os.environ.setdefault("XMODIFIERS", "@im=fcitx")

from PySide6.QtWidgets import QApplication
from zentray.dependencies import injector, init_tray_controller
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.services.system_utils import SingleInstanceGuard, HotkeyListener
from zentray.ui.overlay import QuickAddOverlay
from zentray.workers.watcher import WatcherWorker
from zentray.workers.nightly_job import NightlyJobWorker
from zentray.config import config
import logging_config


def main():
    # 1. 配置验证
    config.validate()
    logging_config.setup_logging()

    # 2. 防多开锁
    SingleInstanceGuard()

    # 3. 初始化 QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 4. 通过 DI 容器初始化托盘控制器
    controller = init_tray_controller(app)

    # 5. 初始化闪电添加浮层与全局快捷键
    overlay = QuickAddOverlay()
    overlay.task_added.connect(controller.reload_data)

    hotkey = HotkeyListener(config.hotkey_quick_add)
    hotkey.triggered.connect(overlay.show_center)
    hotkey.start()

    # 6. 启动后台巡检 worker（注入 Repository）
    task_repo = injector.get(TaskRepository)
    template_repo = injector.get(PeriodicTemplateRepository)
    watcher = WatcherWorker(task_repo, template_repo)
    watcher.tasks_updated.connect(controller.reload_data)
    watcher.start()

    # 7. 启动夜间复盘 worker
    nightly = NightlyJobWorker(task_repo)
    nightly.job_completed.connect(controller.renderer.show_notification)
    nightly.start()

    # 8. 进入事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
