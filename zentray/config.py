import os
import sys
from pathlib import Path
from platformdirs import user_data_dir

# 自动从项目根目录加载 .env 环境变量
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

APP_NAME = "ZenTray"
APP_AUTHOR = "Zen-Geek"

# 跨平台标准数据目录
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
ACTIVE_TASKS_FILE = DATA_DIR / "active_tasks.json"
PERIODIC_TEMPLATES_FILE = DATA_DIR / "periodic_templates.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# WxPusher 默认配置
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN")
WXPUSHER_UID = os.getenv("WXPUSHER_UID")

# LLM AI 配置 (用于 Nightly Job)
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o")

# 存储后端配置 (file | mysql)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "file")

# UI 与调度设置
POLLING_INTERVAL_MS = 30000  # 托盘轮播间隔 (30秒)
POMODORO_MINUTES = 25        # 番茄钟专注时长
HOTKEY_QUICK_ADD = "<cmd>+<alt>+t" if sys.platform == 'darwin' else "<ctrl>+<alt>+t"

# 确保核心目录存在
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def validate_config():
    required_vars = {
        "WXPUSHER_APP_TOKEN": WXPUSHER_APP_TOKEN,
        "WXPUSHER_UID": WXPUSHER_UID,
        "AI_API_KEY": AI_API_KEY
    }
    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        error_msg = f"Configuration error: Missing required environment variables: {', '.join(missing)}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)
