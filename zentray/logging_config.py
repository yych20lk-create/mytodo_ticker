import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logging():
    logger = logging.getLogger('zentray')
    logger.setLevel(logging.INFO)

    # Console handler for real-time output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    # File handler with rotation (10MB per file, 5 backups)
    file_handler = RotatingFileHandler(
        'zentray.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    return logger


def get_logger():
    """Get the configured logger"""
    return logging.getLogger('zentray')
