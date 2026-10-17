import time
import random
from functools import wraps
from pathlib import Path
from typing import Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm
from requests.exceptions import RequestException, ConnectionError

from ..config import Config
from ..exceptions import BilibiliAPIError, DownloadError
from .logger import log_info, log_error

# (connect, read) timeout in seconds; read timeout applies per socket read, not to the whole download
REQUEST_TIMEOUT = (10, 30)
CHUNK_SIZE = 1024 * 1024

def retry_with_backoff(retries: int = 5, backoff_in_seconds: float = 1, desc: str = 'Unknown'):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, RequestException) as e:
                    if x == retries:
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x + 
                            random.uniform(0, 1))
                    time.sleep(sleep)
                    x += 1
                    log_info(f"{desc}: Retry #{x} after {sleep:.1f} seconds")
        return wrapper
    return decorator

def _call_api(url: str, description: str, **kwargs: Any) -> Dict[str, Any]:
    """Call a Bilibili JSON API and return its `data` field.

    Raises:
        BilibiliAPIError: On network failure, invalid JSON or a non-zero API code
    """
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        response.raise_for_status()
        data = response.json()
    except (RequestException, ValueError) as e:
        raise BilibiliAPIError(f"Failed to fetch {description}: {e}") from e

    if data.get("code") != 0:
        raise BilibiliAPIError(
            f"Failed to fetch {description}: {data.get('message', 'Unknown error')} (code {data.get('code')})"
        )
    return data.get("data") or {}

def get_video_info(config: Config, bv_id: str, sessdata: str = "") -> Dict[str, Any]:
    """Fetch video information from Bilibili; SESSDATA is optional for this endpoint"""
    return _call_api(
        config.get_api_url("video_info"),
        "video information",
        params={"bvid": bv_id},
        headers=config.get_headers_for_video(),
        cookies={"SESSDATA": sessdata} if sessdata else None,
    )

def get_video_stream_info(config: Config, bv_id: str, cid: str, my_cookie: str) -> Dict[str, Any]:
    """Fetch video stream information from Bilibili.
    
    Args:
        bv_id (str): BV ID of the video
        cid (str): CID of the video
        my_cookie (str): Cookie string for authentication
    """
    
    log_info(f"Fetching video stream information for BV ID: {bv_id}, CID: {cid}")
    
    params = {
        "bvid": bv_id,
        "cid": cid,
        "qn": "0",
        "fnval": "80",
        "fnver": "0",
        "fourk": "1"
    }
    
    cookies = {
        'SESSDATA': my_cookie
    }
    
    return _call_api(
        config.get_api_url("video_stream"),
        "video stream information",
        params=params,
        headers=config.get_headers_for_video(bv_id),
        cookies=cookies,
    )

def download_file(config: Config, bv_id: str, url: str, output_path: Path, desc: Optional[str] = None,
                  max_attempts: int = 5) -> None:
    """Download file with progress bar and resume capability.

    Args:
        max_attempts: Consecutive attempts without any progress before giving up

    Raises:
        DownloadError: When the file cannot be fully downloaded
        RequestException: When the server keeps rejecting requests
    """
    headers = config.get_headers_for_video(bv_id)

    @retry_with_backoff(retries=5, backoff_in_seconds=1, desc="Opening download stream")
    def open_stream(pos: int) -> requests.Response:
        request_headers = {**headers, 'Range': f'bytes={pos}-'} if pos > 0 else headers
        response = requests.get(url, headers=request_headers, stream=True, timeout=REQUEST_TIMEOUT)
        try:
            response.raise_for_status()
        except RequestException:
            response.close()
            raise
        return response

    # A HEAD request may return 404, so read the size from a streamed GET and close it without the body
    with open_stream(0) as response:
        file_size = int(response.headers.get('content-length', 0))
    if file_size <= 0:
        raise DownloadError(f"Server did not report a size for {output_path.name}")

    initial_pos = output_path.stat().st_size if output_path.exists() else 0
    if initial_pos == file_size:
        log_info(f"File {output_path} already completely downloaded")
        return
    if initial_pos > file_size:
        log_info(f"Existing file {output_path} is larger than expected, restarting download")
        initial_pos = 0
    elif initial_pos > 0:
        log_info(f"Resuming download from byte {initial_pos}")

    progress_desc = desc if desc else output_path.name

    with tqdm(total=file_size, initial=initial_pos, unit='B',
              unit_scale=True, desc=progress_desc, colour='green') as pbar:

        current_pos = initial_pos
        failures = 0
        while current_pos < file_size:
            written = 0
            try:
                with open_stream(current_pos) as response:
                    if current_pos > 0 and response.status_code != 206:
                        log_info("Server ignored the Range header, restarting download from the beginning")
                        current_pos = 0
                        pbar.reset(total=file_size)
                    mode = 'ab' if current_pos > 0 else 'wb'
                    with open(output_path, mode) as f:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                size = f.write(chunk)
                                pbar.update(size)
                                current_pos += size
                                written += size
            except RequestException as e:
                log_error(f"Error during download: {e}")

            if current_pos > file_size:
                raise DownloadError(f"Received more data than expected for {output_path}")
            if current_pos == file_size:
                break

            failures = 0 if written else failures + 1
            if failures >= max_attempts:
                raise DownloadError(
                    f"Download of {output_path.name} stalled at byte {current_pos}/{file_size} "
                    f"after {max_attempts} attempts"
                )
            log_info(f"Will retry download from position {current_pos}")
            time.sleep(1)

    # Verify file size after download
    if output_path.stat().st_size != file_size:
        raise DownloadError(f"Downloaded file size mismatch for {output_path}")
    log_info(f"Downloaded file: {output_path} completed with size: {file_size}")

def parallel_download(config: Config, bv_id: str,
                      video_url: Optional[str], video_path: Optional[Path],
                      audio_url: Optional[str], audio_path: Optional[Path]) -> None:
    """Download video and audio files in parallel; a stream is skipped when its URL or path is None"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []

        if video_url and video_path:
            futures.append(
                executor.submit(download_file, config, bv_id, video_url, video_path, "Downloading video")
            )

        if audio_url and audio_path:
            futures.append(
                executor.submit(download_file, config, bv_id, audio_url, audio_path, "Downloading audio")
            )

        for future in futures:
            future.result()

def get_accepted_video_quality(video_stream_info: Dict[str, Any]) -> Dict[int, str]:
    """Get the accepted quality of the video stream.
    
    Args:
        video_stream_info (dict): Video stream information from Bilibili
    """
    quality = video_stream_info.get('accept_quality', [])
    desc = video_stream_info.get('accept_description', [])
    
    dict_quality = dict(zip(quality, desc))
    return dict_quality
