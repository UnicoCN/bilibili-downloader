"""Unit tests for the BilibiliDownloader orchestration."""
import subprocess
from unittest.mock import Mock, patch

import pytest

from src.bilibili_downloader import bilibili_downloader as module
from src.bilibili_downloader.bilibili_downloader import BilibiliDownloader
from src.bilibili_downloader.exceptions import BilibiliAPIError, MergeError

VIDEO_INFO = {"cid": 123, "title": "Title", "owner": {"name": "Uploader"}, "duration": 10}
STREAM_INFO = {
    "accept_quality": [80, 64],
    "accept_description": ["1080P", "720P"],
    "dash": {
        "video": [
            {"id": 64, "bandwidth": 100, "baseUrl": "https://cdn/v64"},
            {"id": 80, "bandwidth": 200, "baseUrl": "https://cdn/v80"},
        ],
        "audio": [{"id": 30280, "bandwidth": 50, "baseUrl": "https://cdn/a"}],
    },
}


@pytest.fixture
def downloader(tmp_path):
    config = Mock()
    config.sessdata = "sess"
    config.data_dir = tmp_path / "data"
    config.data_dir.mkdir()
    config.downloads_dir = tmp_path / "downloads"
    config.logs_dir = tmp_path / "logs"
    config.logs_dir.mkdir()
    config.log_config = {"filename": "test.log", "max_size": 1024, "backup_count": 1, "format": "%(message)s"}
    config.get_file_extension.side_effect = lambda name: {"video": ".m4s", "audio": ".m4s", "output": ".mp4"}[name]

    instance = BilibiliDownloader.__new__(BilibiliDownloader)
    instance.config = config
    return instance


def _fake_parallel_download(config, bv_id, video_url, audio_url, output_dir, only_video, only_audio):
    video_path = audio_path = None
    if not only_audio:
        video_path = output_dir / "video.m4s"
        video_path.write_bytes(b"v")
    if not only_video:
        audio_path = output_dir / "audio.m4s"
        audio_path.write_bytes(b"a")
    return video_path, audio_path


class TestBilibiliDownloader:

    def test_successful_download_merges_and_cleans_up(self, downloader):
        with patch.object(module, "get_video_info", return_value=dict(VIDEO_INFO)), \
             patch.object(module, "get_video_stream_info", return_value=STREAM_INFO), \
             patch.object(module, "parallel_download", side_effect=_fake_parallel_download) as pd, \
             patch.object(module.subprocess, "run") as run:
            output = downloader.download("BV1")

        assert output == downloader.config.downloads_dir / "Uploader" / "Title.mp4"
        assert pd.call_args.args[2] == "https://cdn/v80"
        cmd = run.call_args.args[0]
        assert cmd[0] == "ffmpeg" and "-y" in cmd and cmd[-1] == str(output)
        assert not list(downloader.config.data_dir.glob("*.m4s"))

    def test_missing_sessdata_raises(self, downloader):
        downloader.config.sessdata = ""
        with pytest.raises(RuntimeError, match="SESSDATA"):
            downloader.download("BV1")

    def test_api_error_propagates(self, downloader):
        with patch.object(module, "get_video_info", side_effect=BilibiliAPIError("boom")):
            with pytest.raises(BilibiliAPIError, match="boom"):
                downloader.download("BV1")

    def test_missing_audio_stream_raises(self, downloader):
        stream_info = {"dash": {"video": STREAM_INFO["dash"]["video"], "audio": None}}
        with patch.object(module, "get_video_info", return_value=dict(VIDEO_INFO)), \
             patch.object(module, "get_video_stream_info", return_value=stream_info):
            with pytest.raises(BilibiliAPIError, match="audio"):
                downloader.download("BV1")

    def test_only_video_does_not_require_audio_stream(self, downloader):
        stream_info = {"dash": {"video": STREAM_INFO["dash"]["video"], "audio": None}}
        with patch.object(module, "get_video_info", return_value=dict(VIDEO_INFO)), \
             patch.object(module, "get_video_stream_info", return_value=stream_info), \
             patch.object(module, "parallel_download", side_effect=_fake_parallel_download), \
             patch.object(module.subprocess, "run"):
            output = downloader.download("BV1", only_video=True)
        assert output.name == "Title_video_only.mp4"

    def test_ffmpeg_failure_raises_merge_error_and_cleans_up(self, downloader):
        error = subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"Invalid data")
        with patch.object(module, "get_video_info", return_value=dict(VIDEO_INFO)), \
             patch.object(module, "get_video_stream_info", return_value=STREAM_INFO), \
             patch.object(module, "parallel_download", side_effect=_fake_parallel_download), \
             patch.object(module.subprocess, "run", side_effect=error):
            with pytest.raises(MergeError, match="Invalid data"):
                downloader.download("BV1")
        assert not list(downloader.config.data_dir.glob("*.m4s"))
