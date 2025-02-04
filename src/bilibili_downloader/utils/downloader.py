import time
import random
from functools import wraps
from pathlib import Path
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm
from requests.exceptions import RequestException, ConnectionError

from ..config import Config
from .logger import log_info, log_error

def retry_with_backoff(retries=5, backoff_in_seconds=1, desc='Unknown'):
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

def get_video_info(config: Config, bv_id: str, cookies: str) -> Dict:
    """Fetch video information from Bilibili"""
    try:
        response = requests.get(
            config.get_api_url("video_info"),
            params={"bvid": bv_id},
            headers={**config.get_headers_for_video(), "Cookie": cookies}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {})
        else:
            return {"error": data.get("message", "Unknown error")}
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching video information: {e}")
        return {"error": str(e)}

def get_video_stream_info(config: Config, bv_id, cid, my_cookie):
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
    
    try:
        response = requests.get(
            config.get_api_url("video_stream"),
            params=params,
            headers=config.get_headers_for_video(bv_id),
            cookies=cookies
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {})
        else:
            return {"error": data.get("message", "Unknown error")}
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching video stream information: {e}")
        return {"error": str(e)}

def download_file(config: Config, bv_id: str, url: str, output_path: Path, desc: Optional[str] = None) -> None:
    """Download file with progress bar and resume capability"""
    
    @retry_with_backoff(retries=5, backoff_in_seconds=1, desc="Getting file size")
    def get_file_size():
        # If only request header, it may return 404 Not Found
        response = requests.get(url, headers=config.get_headers_for_video(bv_id), stream=True)
        response.raise_for_status()
        return int(response.headers.get('content-length', 0))

    file_size = get_file_size()
    initial_pos = 0
    
    # Check if partial download exists
    if output_path.exists():
        initial_pos = output_path.stat().st_size
        if initial_pos >= file_size:
            log_info(f"File {output_path} already completely downloaded")
            return
        else:
            log_info(f"Resuming download from byte {initial_pos}")

    progress_desc = desc if desc else output_path.name
    
    @retry_with_backoff(retries=5, backoff_in_seconds=1, desc="Downloading file chunks")
    def download_chunk(pos):
        # Update headers with current position for each chunk request
        headers = config.get_headers_for_video()
        if pos > 0:
            headers['Range'] = f'bytes={pos}-'
        response = requests.get(url, headers=headers, stream=True)
        
        # If resuming, server should return 206 Partial Content
        if pos > 0 and response.status_code != 206:
            raise RequestException("Server doesn't support resume")
            
        response.raise_for_status()
        return response
    
    with tqdm(total=file_size, initial=initial_pos, unit='B', 
              unit_scale=True, desc=progress_desc, colour='green') as pbar:
        
        current_pos = initial_pos
        while current_pos < file_size:
            try:
                response = download_chunk(current_pos)
                # Open in append mode if resuming, write mode if starting fresh
                mode = 'ab' if current_pos > 0 else 'wb'
                with open(output_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=4*1024*1024):
                        if chunk:
                            size = f.write(chunk)
                            pbar.update(size)
                            current_pos += size
            except Exception as e:
                log_error(f"Error during download: {str(e)}")
                if current_pos < file_size:
                    log_info(f"Will retry download from position {current_pos}")
                    time.sleep(1)
    
    # Verify file size after download
    if output_path.stat().st_size != file_size:
        raise Exception(f"Downloaded file size mismatch for {output_path}")
    log_info(f"Downloaded file: {output_path} completed with size: {file_size}")

def parallel_download(config: Config, bv_id: str, video_url: str, audio_url: str, output_dir: Path, 
                     only_video: bool = False, only_audio: bool = False) -> Tuple[Optional[Path], Optional[Path]]:
    """Download video and audio files in parallel"""
    video_path = None
    audio_path = None
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        
        if not only_audio:
            video_path = output_dir / f'video{config.get_file_extension("video")}'
            futures.append(
                executor.submit(download_file, config, bv_id, video_url, video_path, "Downloading video")
            )
        
        if not only_video:
            audio_path = output_dir / f'audio{config.get_file_extension("audio")}'
            futures.append(
                executor.submit(download_file, config, bv_id, audio_url, audio_path, "Downloading audio")
            )
        
        # Wait for all downloads to complete
        for future in futures:
            future.result()
            
    return video_path, audio_path

def get_accepted_video_quality(video_stream_info):
    """Get the accepted quality of the video stream.
    
    Args:
        video_stream_info (dict): Video stream information from Bilibili
    """
    quality = video_stream_info.get('accept_quality', [])
    desc = video_stream_info.get('accept_description', [])
    
    dict_quality = dict(zip(quality, desc))
    return dict_quality
