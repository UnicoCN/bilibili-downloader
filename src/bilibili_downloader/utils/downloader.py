from pathlib import Path
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm

from ..config import Config
from .logger import log_info, log_error

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

def download_file(config: Config, url: str, output_path: Path, desc: Optional[str] = None) -> None:
    """Download file with progress bar"""
    response = requests.get(
        url, 
        headers=config.get_headers_for_video(),
        stream=True
    )
    response.raise_for_status()
    
    file_size = int(response.headers.get('content-length', 0))
    
    # Use desc if provided, otherwise use filename
    progress_desc = desc if desc else output_path.name
    
    # Silently log the download start
    log_info(f"Starting download of {output_path}, size: {file_size} bytes")
    
    with tqdm(total=file_size, unit='iB', unit_scale=True, desc=progress_desc, colour='green') as pbar:
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                pbar.update(size)

def parallel_download(config: Config, video_url: str, audio_url: str, output_dir: Path, 
                     only_video: bool = False, only_audio: bool = False) -> Tuple[Optional[Path], Optional[Path]]:
    """Download video and audio files in parallel"""
    video_path = None
    audio_path = None
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        
        if not only_audio:
            video_path = output_dir / f'video{config.get_file_extension("video")}'
            futures.append(
                executor.submit(download_file, config, video_url, video_path, "Downloading video")
            )
        
        if not only_video:
            audio_path = output_dir / f'audio{config.get_file_extension("audio")}'
            futures.append(
                executor.submit(download_file, config, audio_url, audio_path, "Downloading audio")
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
