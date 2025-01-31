import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logger(log_file: Path, max_size: int, backup_count: int, log_format: str) -> logging.Logger:
    """Setup and return a configured logger instance"""
    logger = logging.getLogger("bilibili_downloader")
    logger.setLevel(logging.INFO)

    # Create formatters
    formatter = logging.Formatter(log_format)

    # Create handlers
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    
    # Disable console logging by default
    # console_handler = logging.StreamHandler(sys.stdout)
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)
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
