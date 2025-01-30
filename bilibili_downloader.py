import os
import json
import logging
import argparse
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from logging.handlers import RotatingFileHandler

__version__ = "1.0.0"

FETCH_VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"
FETCH_VIDEO_STREAM_URL = "https://api.bilibili.com/x/player/playurl"

# Configure logging with file rotation
log_file = 'bilibili_downloader.log'
log_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=3)  # 5 MB per file, keep 3 backup files
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

def log_info(message):
    """Log information to the log file."""
    logger.info(message)
    print(message)
    
def log_error(message):
    """Log errors to the log file."""
    logger.error(message)
    print(message)

def get_video_info(bv_id, cookies):
    """Fetch video information from Bilibili using the BV ID and cookies.
    
    Args:
        bv_id (str): BV ID of the video
        cookies (str): Cookie string for authentication
    """
    
    log_info(f"Fetching video information for BV ID: {bv_id}")
    
    url = FETCH_VIDEO_INFO_URL
    params = {"bvid": bv_id}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": cookies
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {})
        else:
            return {"error": data.get("message", "Unknown error")}
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching video information: {e}")
        return {"error": str(e)}

def get_video_stream_info(bv_id, cid, my_cookie):
    """Fetch video stream information from Bilibili.
    
    Args:
        bv_id (str): BV ID of the video
        cid (str): CID of the video
        my_cookie (str): Cookie string for authentication
    """
    
    log_info(f"Fetching video stream information for BV ID: {bv_id}, CID: {cid}")
    
    url = FETCH_VIDEO_STREAM_URL
    params = {
        "bvid": bv_id,
        "cid": cid,
        "qn": "0",
        "fnval": "80",
        "fnver": "0",
        "fourk": "1"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/video/' + bv_id,
        'Origin': 'https://www.bilibili.com',
    }

    cookies = {
        'SESSDATA': my_cookie
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {})
        else:
            return {"error": data.get("message", "Unknown error")}
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching video stream information: {e}")
        return {"error": str(e)}

def download_file(url, file_path, desc=None):
    """
    Download file with progress bar.
    
    Args:
        url (str): The file URL to download
        file_path (str): Full path to save the file
        desc (str): Description for the progress bar
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Referer": "https://www.bilibili.com"
    }
    
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    file_size = int(response.headers.get('content-length', 0))
    
    # Use desc if provided, otherwise use filename
    progress_desc = desc if desc else os.path.basename(file_path)
    
    # Silently log the download start
    log_info(f"Starting download of {file_path}, size: {file_size} bytes")
    
    with tqdm(total=file_size, unit='iB', unit_scale=True, desc=progress_desc, colour='green') as pbar:
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                pbar.update(size)

def parallel_download(video_url, audio_url, dir_name, only_video, only_audio):
    """Download video and audio files in parallel using threads.
    
    Args:
        video_url (str): URL of the video stream
        audio_url (str): URL of the audio stream
        dir_name (str): Directory to save the downloaded files
        only_video (bool): Download only the video stream
        only_audio (bool): Download only the audio stream
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        
        if not only_audio:
            video_path = os.path.join(dir_name, 'video.m4s')
            future_video = executor.submit(
                download_file, 
                video_url, 
                video_path,
                "Downloading video"
            )
            futures.append(future_video)
        
        if not only_video:
            audio_path = os.path.join(dir_name, 'audio.m4s')
            future_audio = executor.submit(
                download_file, 
                audio_url, 
                audio_path,
                "Downloading audio"
            )
            futures.append(future_audio)
        
        # Wait for all downloads to complete
        for future in futures:
            try:
                future.result()
            except Exception as e:
                log_error(f"Download failed: {str(e)}")
                raise

def get_accepted_video_quality(video_stream_info):
    """Get the accepted quality of the video stream.
    
    Args:
        video_stream_info (dict): Video stream information from Bilibili
    """
    quality = video_stream_info.get('accept_quality', [])
    desc = video_stream_info.get('accept_description', [])
    
    dict_quality = dict(zip(quality, desc))
    return dict_quality

def create_parser():
    parser = argparse.ArgumentParser(
        description='Download videos with BV ID in Bilibili'
    )
    
    parser.add_argument(
        "-id", '--bvid',
        type=str, required=True,
        help='BVid of the video from bilibili (e.g., BV1xx411c7mD)'
    )

    parser.add_argument(
        '-c', '--cookie',
        type=str, required=False,
        default='cookie.txt',
        help='File that stores the cookie (default file is cookie.txt)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str, required=False,
        default='output',
        help='Output directory for downloaded files (default is "output")'
    )

    parser.add_argument(
        '--only-info',
        action='store_true',
        help='Only fetch video information and stream URLs'
    )

    parser.add_argument(
        '--only-video',
        action='store_true',
        help='Only download the video stream (without audio)'
    )

    parser.add_argument(
        '--only-audio',
        action='store_true',
        help='Only download the audio stream (without video)'
    )

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    log_info(f"Bilibili Downloader v{__version__}")
    
    bv_id = args.bvid
    cookies_file = args.cookie
    output_dir = args.output
    
    only_info = args.only_info
    
    only_video = args.only_video
    only_audio = args.only_audio

    # Read cookies
    try:
        with open(cookies_file, 'r') as file:
            cookies = file.readline().strip()
    except FileNotFoundError:
        log_error(f"Error: {cookies_file} not found")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video info
    video_info = get_video_info(bv_id, cookies)
    if "error" in video_info:
        log_error(f"Error: {video_info['error']}")
        return
    
    # Save video info
    with open(os.path.join(output_dir, 'video_info.json'), 'w', encoding='utf-8') as file:
        json.dump(video_info, file, ensure_ascii=False, indent=2)
    
    # Print video information
    log_info("Video Information:")
    log_info(f"Title: {video_info.get('title')}")
    log_info(f"Description: {video_info.get('desc')}")
    log_info(f"Uploader: {video_info.get('owner', {}).get('name')}")
    log_info(f"Duration: {video_info.get('duration')} seconds")
    
    # Get stream info
    cid = video_info.get('cid')
    dir_name = video_info.get('owner', {}).get('name')
    file_name = video_info.get('title')
    
    video_stream_info = get_video_stream_info(bv_id, cid, cookies)
    
    # Save stream info
    with open(os.path.join(output_dir, 'video_stream_info.json'), 'w', encoding='utf-8') as file:
        json.dump(video_stream_info, file, ensure_ascii=False, indent=2)
    
    accepted_quality = get_accepted_video_quality(video_stream_info)
    for quality, desc in accepted_quality.items():
        log_info(f"Accepted Quality: {quality} - {desc}")
    
    # Get video and audio URLs
    video_urls = video_stream_info.get('dash', {}).get('video', [])
    audio_urls = video_stream_info.get('dash', {}).get('audio', [])
    
    if not video_urls or not audio_urls:
        log_error('Error: Failed to get video and audio URLs')
        return
    
    # Sort by quality and get highest quality URLs
    video_urls.sort(key=lambda url: (url.get('id', 0), url.get('bandwidth', 0)))
    audio_urls.sort(key=lambda url: (url.get('id', 0), url.get('bandwidth', 0)))
    
    video_url = video_urls[-1].get('baseUrl', '')
    audio_url = audio_urls[-1].get('baseUrl', '')
    
    if not video_url or not audio_url:
        log_error('Error: Failed to get video and audio URLs')
        return
    
    # Get the quality and description of the video and audio streams
    video_quality = accepted_quality.get(video_urls[-1].get('id', 0), 'Unknown')
    log_info(f"Quality of the video to be downloaded: {video_quality}")
    
    if only_info:
        log_info("Video information and stream URLs saved to files.")
        log_info("Only info flag is set. Skipping download.")
        return
    
    # Create directory if it doesn't exist
    dir_name = os.path.join(output_dir, dir_name)
    os.makedirs(dir_name, exist_ok=True)
    
    log_info("Starting parallel download of video and audio...")
    try:
        parallel_download(video_url, audio_url, dir_name, only_video, only_audio)
    except Exception as e:
        log_error(f"Error during parallel download: {str(e)}")
        return
    
    if only_video:
        output_file = os.path.join(dir_name, f'{file_name}_video_only.mp4')
        video_input_file = os.path.join(dir_name, 'video.m4s')
    elif only_audio:
        output_file = os.path.join(dir_name, f'{file_name}_audio_only.mp4')
        audio_input_file = os.path.join(dir_name, 'audio.m4s')
    else:
        output_file = os.path.join(dir_name, f'{file_name}.mp4')
        video_input_file = os.path.join(dir_name, 'video.m4s')
        audio_input_file = os.path.join(dir_name, 'audio.m4s')
    
    
    log_info("Merging video and audio...")
    try:
        log_info(f"Merging files into: {output_file}")
        
        # Check if input files exist
        if not os.path.exists(video_input_file) or (not only_video and not os.path.exists(audio_input_file)):
            raise FileNotFoundError("Input files not found")
            
        if only_video or only_audio:
            input_file = video_input_file if only_video else audio_input_file
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c', 'copy',
                output_file
            ]
        else:
            cmd = [
                'ffmpeg',
                '-i', video_input_file,
                '-i', audio_input_file,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-f', 'mp4',
                output_file
            ]
        
        # Run FFmpeg command
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Clean up temporary files
        if not only_video:
            os.remove(os.path.join(dir_name, 'audio.m4s'))
        if not only_audio:
            os.remove(os.path.join(dir_name, 'video.m4s'))
        
        log_info(f"Download completed! File saved as: {output_file}")
    
    except subprocess.CalledProcessError as e:
        log_error(f"Error: Failed to merge video and audio files: {e}")
    except Exception as e:
        log_error(f"Error during cleanup: {str(e)}")


if __name__ == '__main__':
    main()
