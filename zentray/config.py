import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# 跨平台用户数据目录（避免依赖 platformdirs）
def _user_data_dir(app_name: str) -> Path:
    """获取应用用户数据目录"""
    if sys.platform == "linux":
        xdg = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        return Path(xdg) / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        return Path(appdata) / app_name
    return Path.home() / f".{app_name.lower()}"


# 自动从项目根目录加载 .env 环境变量
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# ==========================================
# 基础配置
# ==========================================

APP_NAME = "ZenTray"
APP_AUTHOR = "Zen-Geek"
VERSION = "3.7.0"

# 跨平台标准数据目录
DATA_DIR = _user_data_dir(APP_NAME)
ACTIVE_TASKS_FILE = DATA_DIR / "active_tasks.json"
PERIODIC_TEMPLATES_FILE = DATA_DIR / "periodic_templates.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# ==========================================
# 第三方服务配置（可选）
# ==========================================

# WxPusher 通知配置
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN")
WXPUSHER_UID = os.getenv("WXPUSHER_UID")

# LLM AI 配置 (用于 Nightly Job)
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o")

# 存储后端配置 (file | mysql)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "file")

# ==========================================
# UI 与调度设置
# ==========================================

POLLING_INTERVAL_MS = 30000   # 托盘轮播间隔 (30秒)
POMODORO_MINUTES = 25         # 番茄钟专注时长
HOTKEY_QUICK_ADD = "<cmd>+<alt>+t" if sys.platform == 'darwin' else "<ctrl>+<alt>+t"

# 确保核心目录存在
os.makedirs(ARCHIVE_DIR, exist_ok=True)


# ==========================================
# 功能可用性检查
# ==========================================

def is_notification_enabled() -> bool:
    """检查通知服务是否可用"""
    return bool(WXPUSHER_APP_TOKEN and WXPUSHER_UID)


def is_ai_coach_enabled() -> bool:
    """检查 AI 教练功能是否可用"""
    return bool(AI_API_KEY)


def get_enabled_features() -> dict:
    """返回所有功能的可用性状态"""
    return {
        "core": True,                              # 核心功能始终可用
        "notification": is_notification_enabled(),
        "ai_coach": is_ai_coach_enabled(),
        "mysql": STORAGE_BACKEND == "mysql",
    }


def validate_config() -> list[str]:
    """
    验证配置并返回警告列表。

    与旧版不同，此函数不会因配置缺失而退出应用。
    核心功能（任务管理、番茄钟、托盘）始终可用，
    仅在缺少第三方服务凭据时给出警告。

    Returns:
        list[str]: 警告信息列表（空列表 = 一切正常）
    """
    warnings = []

    if not is_notification_enabled():
        warnings.append(
            "通知服务未配置：创建 .env 文件并设置 WXPUSHER_APP_TOKEN 和 WXPUSHER_UID "
            "即可启用移动端消息推送。"
        )

    if not is_ai_coach_enabled():
        warnings.append(
            "AI 教练未配置：设置 AI_API_KEY 即可启用每日夜间复盘与毒舌锐评功能。"
        )

    return warnings
