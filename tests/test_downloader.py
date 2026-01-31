"""Unit tests for downloader module."""
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.bilibili_downloader.utils.downloader import (
    get_accepted_video_quality,
    retry_with_backoff
)


class TestDownloader:
    """Test cases for downloader utilities."""

    def test_get_accepted_video_quality(self):
        """Test parsing of video quality information."""
        video_stream_info = {
            'accept_quality': [80, 64, 32],
            'accept_description': ['1080P', '720P', '480P']
        }

        result = get_accepted_video_quality(video_stream_info)

        assert result == {80: '1080P', 64: '720P', 32: '480P'}

    def test_get_accepted_video_quality_empty(self):
        """Test handling of empty quality information."""
        video_stream_info = {
            'accept_quality': [],
            'accept_description': []
        }

        result = get_accepted_video_quality(video_stream_info)

        assert result == {}

    def test_retry_with_backoff_success_first_try(self):
        """Test that retry decorator succeeds on first try."""
        mock_func = Mock(return_value="success")
        decorated_func = retry_with_backoff(retries=3)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_with_backoff_succeeds_after_retry(self):
        """Test that retry decorator retries on failure then succeeds."""
        mock_func = Mock(
            side_effect=[
                requests.exceptions.ConnectionError("Connection failed"),
                "success"
            ]
        )
        decorated_func = retry_with_backoff(retries=3, backoff_in_seconds=0.01)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_with_backoff_exhausts_retries(self):
        """Test that retry decorator raises error after exhausting retries."""
        mock_func = Mock(
            side_effect=requests.exceptions.ConnectionError("Connection failed")
        )
        decorated_func = retry_with_backoff(retries=2, backoff_in_seconds=0.01)(mock_func)

        with pytest.raises(requests.exceptions.ConnectionError):
            decorated_func()

        # Should try initial + 2 retries = 3 times
        assert mock_func.call_count == 3
