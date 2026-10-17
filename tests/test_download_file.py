"""Unit tests for download_file resume and retry behaviour."""
from unittest.mock import Mock, patch

import pytest
import requests

from src.bilibili_downloader.exceptions import DownloadError
from src.bilibili_downloader.utils import downloader
from src.bilibili_downloader.utils.downloader import download_file

CONTENT = b"0123456789" * 10


class FakeResponse:
    def __init__(self, body=b"", status_code=200, content_length=None, fail_after=None):
        self.body = body
        self.status_code = status_code
        self.headers = {} if content_length == 0 else {"content-length": str(content_length or len(body))}
        self.fail_after = fail_after
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error")

    def iter_content(self, chunk_size):
        sent = 0
        for i in range(0, len(self.body), 10):
            if self.fail_after is not None and sent >= self.fail_after:
                raise requests.exceptions.ChunkedEncodingError("connection reset")
            yield self.body[i:i + 10]
            sent += 10

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _range_server(fail_first_body_after=None):
    """Serve CONTENT honouring Range headers; optionally drop the first body transfer midway."""
    state = {"body_requests": 0}

    def get(url, headers=None, stream=False, timeout=None):
        assert timeout is not None
        range_header = (headers or {}).get("Range")
        if range_header:
            start = int(range_header.split("=")[1].rstrip("-"))
            return FakeResponse(CONTENT[start:], status_code=206)
        state["body_requests"] += 1
        fail_after = fail_first_body_after if state["body_requests"] == 2 else None
        return FakeResponse(CONTENT, fail_after=fail_after)

    return get


@pytest.fixture
def config():
    config = Mock()
    config.get_headers_for_video.return_value = {"Referer": "https://www.bilibili.com/video/BV1"}
    return config


@pytest.fixture(autouse=True)
def no_sleep():
    with patch.object(downloader.time, "sleep"):
        yield


class TestDownloadFile:

    def test_downloads_complete_file(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        with patch("requests.get", side_effect=_range_server()):
            download_file(config, "BV1", "https://cdn/f", output)
        assert output.read_bytes() == CONTENT

    def test_resumes_after_connection_drop(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        with patch("requests.get", side_effect=_range_server(fail_first_body_after=30)):
            download_file(config, "BV1", "https://cdn/f", output)
        assert output.read_bytes() == CONTENT

    def test_resumes_existing_partial_file(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        output.write_bytes(CONTENT[:40])
        server = Mock(side_effect=_range_server())
        with patch("requests.get", server):
            download_file(config, "BV1", "https://cdn/f", output)
        assert output.read_bytes() == CONTENT
        assert server.call_args.kwargs["headers"]["Range"] == "bytes=40-"

    def test_restarts_when_server_ignores_range(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        output.write_bytes(CONTENT[:40])
        with patch("requests.get", side_effect=lambda *a, **k: FakeResponse(CONTENT)):
            download_file(config, "BV1", "https://cdn/f", output)
        assert output.read_bytes() == CONTENT

    def test_restarts_when_existing_file_is_larger(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        output.write_bytes(CONTENT + b"stale")
        with patch("requests.get", side_effect=_range_server()):
            download_file(config, "BV1", "https://cdn/f", output)
        assert output.read_bytes() == CONTENT

    def test_gives_up_when_no_progress(self, config, tmp_path):
        output = tmp_path / "f.m4s"
        stalled = [FakeResponse(b"", status_code=206, content_length=len(CONTENT)) for _ in range(3)]
        responses = [FakeResponse(CONTENT), FakeResponse(CONTENT, fail_after=20), *stalled]
        server = Mock(side_effect=responses)
        with patch("requests.get", server):
            with pytest.raises(DownloadError, match="stalled at byte 20/100"):
                download_file(config, "BV1", "https://cdn/f", output, max_attempts=3)
        assert server.call_count == len(responses)

    def test_missing_content_length_raises(self, config, tmp_path):
        with patch("requests.get", return_value=FakeResponse(b"", content_length=0)):
            with pytest.raises(DownloadError, match="did not report a size"):
                download_file(config, "BV1", "https://cdn/f", tmp_path / "f.m4s")
