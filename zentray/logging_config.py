import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: Path | str | None = None):
    """配置 zentray 根 logger：控制台 + 用户数据目录下滚动日志。"""
    logger = logging.getLogger("zentray")
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler（热重载 / 重复调用）
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console_handler)

    if log_file is None:
        try:
            from zentray.config import LOG_FILE

            log_file = LOG_FILE
        except Exception:
            log_file = Path("zentray.log")

    log_path = Path(log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger


def get_logger():
    """Get the configured logger"""
    return logging.getLogger("zentray")
