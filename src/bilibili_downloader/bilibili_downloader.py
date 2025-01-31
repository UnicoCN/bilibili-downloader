import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional

from . import __version__
from .config import config
from .utils.logger import log_info, log_error
from .utils.downloader import (
    get_video_info,
    get_video_stream_info,
    get_accepted_video_quality,
    parallel_download
)

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
        '-o', '--output',
        type=Path,
        default=config.downloads_dir,  # Fixed reference
        help='Output directory for downloaded files (default: downloads/)'
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

def process_video(bv_id: str, output_dir: Path, video_info: dict,
                 only_video: bool = False, only_audio: bool = False) -> Optional[Path]:
    """Process video download and merging"""
    try:
        # Get stream info
        cid = video_info.get('cid')
        dir_name = video_info.get('owner', {}).get('name')
        file_name = video_info.get('title')
        
        video_stream_info = get_video_stream_info(bv_id, cid, config.sessdata)
        
        # Save stream info
        with open(output_dir / 'video_stream_info.json', 'w', encoding='utf-8') as file:
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
        
        # Create directory if it doesn't exist
        dir_name = output_dir / dir_name
        dir_name.mkdir(parents=True, exist_ok=True)
        
        log_info("Starting parallel download of video and audio...")
        try:
            video_input_file, audio_input_file = parallel_download(
                video_url, audio_url, config.temp_dir, only_video, only_audio
            )
            if not video_input_file and not only_audio:
                raise FileNotFoundError("Video file not downloaded")
            if not audio_input_file and not only_video:
                raise FileNotFoundError("Audio file not downloaded")
        except Exception as e:
            log_error(f"Error during parallel download: {str(e)}")
            return

        if only_video:
            output_file = dir_name / f'{file_name}_video_only{config.get_file_extension("output")}'
        elif only_audio:
            output_file = dir_name / f'{file_name}_audio_only{config.get_file_extension("output")}'
        else:
            output_file = dir_name / f'{file_name}{config.get_file_extension("output")}'

        log_info("Merging video and audio...")
        try:
            log_info(f"Merging files into: {output_file}")
            
            # Check if input files exist
            if not video_input_file.exists() or (not only_video and not audio_input_file.exists()):
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
            try:
                if video_input_file and video_input_file.exists():
                    video_input_file.unlink()
                    log_info(f"Cleaned up temporary video file: {video_input_file}")
                    
                if audio_input_file and audio_input_file.exists():
                    audio_input_file.unlink()
                    log_info(f"Cleaned up temporary audio file: {audio_input_file}")
                    
            except Exception as e:
                log_error(f"Warning: Failed to clean up temporary files: {e}")
            
            log_info(f"Download completed! File saved as: {output_file}")
        
        except subprocess.CalledProcessError as e:
            log_error(f"Error: Failed to merge video and audio files: {e}")
        except Exception as e:
            log_error(f"Error during cleanup: {str(e)}")
        
        return output_file
        
    except Exception as e:
        log_error(f"Error processing video: {str(e)}")
        return None

def download_video():
    try:
        parser = create_parser()
        args = parser.parse_args()
        
        log_info(f"Bilibili Downloader v{__version__}")
        
        bv_id = args.bvid
        output_dir = args.output
        
        only_info = args.only_info
        
        only_video = args.only_video
        only_audio = args.only_audio

        if not config.sessdata:
            log_error("Error: SESSDATA not configured in config/user.yaml")
            return
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get video info
        video_info = get_video_info(bv_id, config.sessdata)
        if "error" in video_info:
            log_error(f"Error: {video_info['error']}")
            return
        
        # Save video info
        with open(output_dir / 'video_info.json', 'w', encoding='utf-8') as file:
            json.dump(video_info, file, ensure_ascii=False, indent=2)
        
        # Print video information
        log_info("Video Information:")
        log_info(f"Title: {video_info.get('title')}")
        log_info(f"Description: {video_info.get('desc')}")
        log_info(f"Uploader: {video_info.get('owner', {}).get('name')}")
        log_info(f"Duration: {video_info.get('duration')} seconds")
        
        if only_info:
            log_info("Video information and stream URLs saved to files.")
            log_info("Only info flag is set. Skipping download.")
            return
        
        process_video(bv_id, output_dir, video_info, only_video, only_audio)
    except Exception as e:
        log_error(f"Unhandled error: {e}")
        raise
