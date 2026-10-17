"""Unit tests for Bilibili API helpers."""
from unittest.mock import Mock, patch

import pytest
import requests

from src.bilibili_downloader.exceptions import BilibiliAPIError
from src.bilibili_downloader.utils.downloader import get_video_info, get_video_stream_info


@pytest.fixture
def config():
    config = Mock()
    config.get_api_url.return_value = "https://api.example.com"
    config.get_headers_for_video.return_value = {"User-Agent": "test"}
    return config


def _json_response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class TestApi:

    def test_get_video_info_returns_data(self, config):
        with patch("requests.get", return_value=_json_response({"code": 0, "data": {"cid": 1}})):
            assert get_video_info(config, "BV1", "sess") == {"cid": 1}

    def test_get_video_info_sends_sessdata_as_named_cookie(self, config):
        with patch("requests.get", return_value=_json_response({"code": 0, "data": {}})) as get:
            get_video_info(config, "BV1", "sess")
        assert get.call_args.kwargs["cookies"] == {"SESSDATA": "sess"}
        assert "Cookie" not in get.call_args.kwargs["headers"]

    def test_get_video_info_without_sessdata_sends_no_cookie(self, config):
        with patch("requests.get", return_value=_json_response({"code": 0, "data": {}})) as get:
            get_video_info(config, "BV1")
        assert get.call_args.kwargs["cookies"] is None

    def test_api_error_code_raises_with_message(self, config):
        payload = {"code": -404, "message": "啥都木有"}
        with patch("requests.get", return_value=_json_response(payload)):
            with pytest.raises(BilibiliAPIError, match="啥都木有"):
                get_video_stream_info(config, "BV1", "1", "sess")

    def test_network_error_raises_api_error(self, config):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("down")):
            with pytest.raises(BilibiliAPIError, match="down"):
                get_video_info(config, "BV1", "sess")

    def test_invalid_json_raises_api_error(self, config):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("not json")
        with patch("requests.get", return_value=response):
            with pytest.raises(BilibiliAPIError):
                get_video_info(config, "BV1", "sess")
