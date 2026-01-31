"""Unit tests for logger module."""
import logging
from pathlib import Path
import pytest

from src.bilibili_downloader.utils.logger import (
    setup_logger,
    get_logger,
    log_info,
    log_error
)


class TestLogger:
    """Test cases for logger utilities."""

    def test_setup_logger_creates_logger(self, tmp_path):
        """Test that setup_logger creates a logger instance."""
        log_file = tmp_path / "test.log"
        logger = setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(message)s',
            enable_console=False
        )

        assert logger is not None
        assert logger.name == "bilibili_downloader"
        assert logger.level == logging.INFO

    def test_logger_writes_to_file(self, tmp_path):
        """Test that logger writes messages to file."""
        log_file = tmp_path / "test.log"
        logger = setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(message)s',
            enable_console=False
        )

        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_console_handler_optional(self, tmp_path):
        """Test that console handler can be disabled."""
        log_file = tmp_path / "test.log"

        # With console disabled
        logger = setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(message)s',
            enable_console=False
        )

        # Should have only file handler
        assert len(logger.handlers) == 1

        # Clear handlers for next test
        logger.handlers.clear()

        # With console enabled
        logger = setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(message)s',
            enable_console=True
        )

        # Should have both file and console handlers
        assert len(logger.handlers) == 2

    def test_get_logger_returns_same_instance(self, tmp_path):
        """Test that get_logger returns the same logger instance."""
        log_file = tmp_path / "test.log"
        logger1 = setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(message)s',
            enable_console=False
        )

        logger2 = get_logger()

        assert logger1 is logger2

    def test_log_info_and_error(self, tmp_path):
        """Test log_info and log_error helper functions."""
        log_file = tmp_path / "test.log"
        setup_logger(
            log_file=log_file,
            max_size=1024,
            backup_count=2,
            log_format='%(levelname)s - %(message)s',
            enable_console=False
        )

        log_info("Info message")
        log_error("Error message")

        content = log_file.read_text()
        assert "INFO - Info message" in content
        assert "ERROR - Error message" in content
