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
from zentray.config import (
    HOTKEY_QUICK_ADD, validate_config, is_notification_enabled, get_enabled_features
)
import logging_config
import logging

logger = logging.getLogger(__name__)


def main():
    # 1. 配置验证（返回警告列表，不退出）
    warnings = validate_config()
    logging_config.setup_logging()

    # 2. 显示配置状态
    features = get_enabled_features()
    logger.info("ZenTray v3.7.0 启动中...")
    logger.info("核心功能: ✓ 已启用")
    logger.info("通知服务: %s", "✓ 已启用" if features["notification"] else "✗ 未配置（设置 WXPUSHER 凭据以启用）")
    logger.info("AI 教练: %s", "✓ 已启用" if features["ai_coach"] else "✗ 未配置（设置 AI_API_KEY 以启用）")

    for warning in warnings:
        logger.warning(warning)

    # 3. 防多开锁
    SingleInstanceGuard()

    # 4. 初始化 QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 5. 通过 DI 容器初始化托盘控制器
    controller = init_tray_controller(app)

    # 6. 初始化闪电添加浮层与全局快捷键
    overlay = QuickAddOverlay()
    overlay.task_added.connect(controller.reload_data)

    hotkey = HotkeyListener(HOTKEY_QUICK_ADD)
    hotkey.triggered.connect(overlay.show_center)
    hotkey.start()

    # 7. 启动后台巡检 worker（注入 Repository）
    task_repo = injector.get(TaskRepository)
    template_repo = injector.get(PeriodicTemplateRepository)
    watcher = WatcherWorker(task_repo, template_repo)
    watcher.tasks_updated.connect(controller.reload_data)
    watcher.start()

    # 8. 启动夜间复盘 worker（仅在通知可用时）
    if features["notification"]:
        nightly = NightlyJobWorker(task_repo)
        nightly.job_completed.connect(controller.renderer.show_notification)
        nightly.start()
        logger.info("夜间复盘 worker 已启动")
    else:
        logger.info("夜间复盘 worker 已跳过（通知服务未配置）")

    # 9. 托盘提示：若未配置通知，显示引导提示
    if warnings:
        controller.renderer.show_notification(
            "ZenTray",
            "部分高级功能未配置。右键托盘 → 查看 README 了解如何启用。"
        )

    # 10. 进入事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
