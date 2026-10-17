import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config
from .exceptions import BilibiliAPIError, DownloadError, MergeError
from .utils.filename import sanitize_filename
from .utils.logger import log_info, log_error, setup_logger
from .utils.downloader import (
    get_video_info,
    get_video_stream_info,
    get_accepted_video_quality,
    parallel_download
)

__version__ = "1.0.0"

BV_ID_PATTERN = re.compile(r"BV[0-9A-Za-z]{10}")

class BilibiliDownloader():

    def __init__(self, config_path: Path):
        self.config = Config(config_path)

    def download(self, bv_id: str, output_path: Optional[Path] = None, only_info: bool = False,
                 only_video: bool = False, only_audio: bool = False) -> Optional[Path]:
        """Download a video.

        Returns:
            Path of the output file, or None when only_info is set

        Raises:
            BilibiliDownloaderError: When fetching, downloading or merging fails
            RuntimeError: When SESSDATA is not configured
            ValueError: When bv_id is not a valid BV ID or both only_video and only_audio are set
        """
        if not BV_ID_PATTERN.fullmatch(bv_id):
            raise ValueError(f"Invalid BV ID: {bv_id!r} (expected e.g. BV1xx411c7mD)")
        if only_video and only_audio:
            raise ValueError("only_video and only_audio are mutually exclusive")
        self._set_logger()

        self.bv_id = bv_id
        self.output_dir = output_path if output_path else self.config.downloads_dir

        self.only_info = only_info

        self.only_video = only_video
        self.only_audio = only_audio

        return self._download_video()

    def get_config(self) -> Config:
        return self.config
    
    def _set_logger(self):
        self.logger = setup_logger(
            self.config.logs_dir / self.config.log_config['filename'],
            self.config.log_config['max_size'],
            self.config.log_config['backup_count'],
            self.config.log_config['format']
        )

    @staticmethod
    def _select_best_stream(streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        return max(streams, key=lambda s: (s.get('id', 0), s.get('bandwidth', 0)))

    def _download(self, video_info: dict) -> Path:
        """Process video download and merging"""
        cid = video_info.get('cid')
        if not cid:
            raise BilibiliAPIError("Video information does not contain a cid")
        dir_name = sanitize_filename(video_info.get('owner', {}).get('name'), fallback='unknown_uploader')
        file_name = sanitize_filename(video_info.get('title'), fallback=self.bv_id)

        video_stream_info = get_video_stream_info(self.config, self.bv_id, cid, self.config.sessdata)

        with open(self.config.data_dir / f'{self.bv_id}_video_stream_info.json', 'w', encoding='utf-8') as file:
            json.dump(video_stream_info, file, ensure_ascii=False, indent=2)

        accepted_quality = get_accepted_video_quality(video_stream_info)
        for quality, desc in accepted_quality.items():
            log_info(f"Accepted Quality: {quality} - {desc}")

        dash = video_stream_info.get('dash') or {}
        video_streams = dash.get('video') or []
        audio_streams = dash.get('audio') or []

        # Temp files are keyed by video, part and stream so a leftover partial file is only
        # ever resumed by a download of exactly the same stream
        temp_prefix = f"{self.bv_id}_{cid}"
        video_url = audio_url = None
        video_input_file = audio_input_file = None
        if not self.only_audio:
            if not video_streams:
                raise BilibiliAPIError("No DASH video stream available for this video")
            video_stream = self._select_best_stream(video_streams)
            video_url = video_stream.get('baseUrl') or video_stream.get('base_url')
            if not video_url:
                raise BilibiliAPIError("Selected video stream has no URL")
            video_input_file = self.config.data_dir / (
                f"{temp_prefix}_video_{video_stream.get('id', 0)}_{video_stream.get('codecid', 0)}"
                f"{self.config.get_file_extension('video')}"
            )
            video_quality = accepted_quality.get(video_stream.get('id', 0), 'Unknown')
            log_info(f"Quality of the video to be downloaded: {video_quality}")
        if not self.only_video:
            if not audio_streams:
                raise BilibiliAPIError("No DASH audio stream available for this video")
            audio_stream = self._select_best_stream(audio_streams)
            audio_url = audio_stream.get('baseUrl') or audio_stream.get('base_url')
            if not audio_url:
                raise BilibiliAPIError("Selected audio stream has no URL")
            audio_input_file = self.config.data_dir / (
                f"{temp_prefix}_audio_{audio_stream.get('id', 0)}{self.config.get_file_extension('audio')}"
            )

        output_subdir = self.output_dir / dir_name
        output_subdir.mkdir(parents=True, exist_ok=True)

        log_info("Starting parallel download of video and audio...")
        parallel_download(
            self.config, self.bv_id, video_url, video_input_file, audio_url, audio_input_file
        )
        for temp_file in (video_input_file, audio_input_file):
            if temp_file and not temp_file.exists():
                raise DownloadError(f"Stream file not downloaded: {temp_file}")

        if self.only_video:
            output_file = output_subdir / f'{file_name}_video_only{self.config.get_file_extension("output")}'
        elif self.only_audio:
            output_file = output_subdir / f'{file_name}_audio_only{self.config.get_file_extension("output")}'
        else:
            output_file = output_subdir / f'{file_name}{self.config.get_file_extension("output")}'

        log_info(f"Merging files into: {output_file}")
        try:
            self._merge(video_input_file, audio_input_file, output_file)
        finally:
            for temp_file, file_type in [(video_input_file, 'video'), (audio_input_file, 'audio')]:
                if temp_file and temp_file.exists():
                    try:
                        temp_file.unlink()
                        log_info(f"Cleaned up temporary {file_type} file: {temp_file}")
                    except OSError as e:
                        log_error(f"Warning: Failed to clean up temporary {file_type} file {temp_file}: {e}")

        log_info(f"Download completed! File saved as: {output_file}")
        return output_file

    @staticmethod
    def _merge(video_file: Optional[Path], audio_file: Optional[Path], output_file: Path) -> None:
        inputs: List[str] = []
        for input_file in (video_file, audio_file):
            if input_file:
                inputs += ['-i', str(input_file)]
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', *inputs, '-c', 'copy', '-f', 'mp4', str(output_file)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, stdin=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='replace').strip() if e.stderr else ''
            raise MergeError(f"FFmpeg failed with exit code {e.returncode}: {stderr}") from e

    def _download_video(self) -> Optional[Path]:
        log_info(f"Bilibili Downloader v{__version__}")

        if not self.only_info and not self.config.sessdata:
            log_error("Error: SESSDATA not configured")
            log_error("Please set SESSDATA via:")
            log_error("  1. Environment variable: export BILIBILI_SESSDATA='your_sessdata'")
            log_error("  2. Config file: config/user.yaml")
            raise RuntimeError("SESSDATA not configured. Cannot proceed with download.")

        video_info = get_video_info(self.config, self.bv_id, self.config.sessdata)

        with open(self.config.data_dir / f'{self.bv_id}_video_info.json', 'w', encoding='utf-8') as file:
            json.dump(video_info, file, ensure_ascii=False, indent=2)

        log_info("Video Information:")
        log_info(f"Title: {video_info.get('title')}")
        log_info(f"Description: {video_info.get('desc')}")
        log_info(f"Uploader: {video_info.get('owner', {}).get('name')}")
        log_info(f"Duration: {video_info.get('duration')} seconds")

        if self.only_info:
            log_info("Video information saved to file.")
            log_info("Only info flag is set. Skipping download.")
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self._download(video_info)
