"""Bilibili video downloader package."""

__version__ = "1.0.0"

from .config import config
from .utils.logger import setup_logger

# Initialize logger when package is imported
logger = setup_logger(
    config.logs_dir / config.log_config['filename'],
    config.log_config['max_size'],
    config.log_config['backup_count'],
    config.log_config['format']
)
