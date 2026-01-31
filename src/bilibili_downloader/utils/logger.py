import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(log_file: Path, max_size: int, backup_count: int, log_format: str,
                 enable_console: bool = True) -> logging.Logger:
    """Setup and return a configured logger instance.

    Args:
        log_file: Path to the log file
        max_size: Maximum size of each log file in bytes
        backup_count: Number of backup files to keep
        log_format: Format string for log messages
        enable_console: Whether to enable console output (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("bilibili_downloader")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(log_format)

    # Create file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Add console handler if enabled
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)

    return logger

def get_logger() -> logging.Logger:
    """Get or create logger instance"""
    return logging.getLogger("bilibili_downloader")

def log_info(msg: str) -> None:
    """Log info message"""
    get_logger().info(msg)

def log_error(msg: str) -> None:
    """Log error message"""
    get_logger().error(msg)
