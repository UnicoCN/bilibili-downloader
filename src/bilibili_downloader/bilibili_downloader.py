import json
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config
from .utils.logger import log_info, log_error, setup_logger
from .utils.downloader import (
    get_video_info,
    get_video_stream_info,
    get_accepted_video_quality,
    parallel_download
)

__version__ = "1.0.0"

class BilibiliDownloader():

    def __init__(self, config_path: Path):
        self.config = Config(config_path)
        self.args = None

    def download(self, bv_id: str, output_path: Path = None, only_info: bool = False, only_video: bool = False, only_audio: bool = False) -> Optional[Path]:
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
    
    def _download(self, video_info: dict) -> Optional[Path]:
        """Process video download and merging"""
        try:
            # Get stream info
            cid = video_info.get('cid')
            dir_name = video_info.get('owner', {}).get('name')
            file_name = video_info.get('title')
            
            video_stream_info = get_video_stream_info(self.config, self.bv_id, cid, self.config.sessdata)
            
            # Save stream info
            with open(self.config.data_dir / 'video_stream_info.json', 'w', encoding='utf-8') as file:
                json.dump(video_stream_info, file, ensure_ascii=False, indent=2)
            
            accepted_quality = get_accepted_video_quality(video_stream_info)
            for quality, desc in accepted_quality.items():
                log_info(f"Accepted Quality: {quality} - {desc}")
            
            # Get video and audio URLs
            video_urls = video_stream_info.get('dash', {}).get('video', [])
            audio_urls = video_stream_info.get('dash', {}).get('audio', [])
            
            if not video_urls or not audio_urls:
                log_error('Error: Failed to get video and audio URLs')
                return None
            
            # Sort by quality and get highest quality URLs
            video_urls.sort(key=lambda url: (url.get('id', 0), url.get('bandwidth', 0)))
            audio_urls.sort(key=lambda url: (url.get('id', 0), url.get('bandwidth', 0)))
            
            video_url = video_urls[-1].get('baseUrl', '')
            audio_url = audio_urls[-1].get('baseUrl', '')
            
            if not video_url or not audio_url:
                log_error('Error: Failed to get video and audio URLs')
                return None
            
            # Get the quality and description of the video and audio streams
            video_quality = accepted_quality.get(video_urls[-1].get('id', 0), 'Unknown')
            log_info(f"Quality of the video to be downloaded: {video_quality}")
            
            # Create directory if it doesn't exist
            dir_name = self.output_dir / dir_name
            dir_name.mkdir(parents=True, exist_ok=True)
            
            log_info("Starting parallel download of video and audio...")
            try:
                video_input_file, audio_input_file = parallel_download(
                    self.config, self.bv_id, video_url, audio_url, self.config.data_dir,
                    self.only_video, self.only_audio
                )
                if not video_input_file and not self.only_audio:
                    raise FileNotFoundError("Video file not downloaded")
                if not audio_input_file and not self.only_video:
                    raise FileNotFoundError("Audio file not downloaded")
            except Exception as e:
                log_error(f"Error during parallel download: {str(e)}")
                return None

            if self.only_video:
                output_file = dir_name / f'{file_name}_video_only{self.config.get_file_extension("output")}'
            elif self.only_audio:
                output_file = dir_name / f'{file_name}_audio_only{self.config.get_file_extension("output")}'
            else:
                output_file = dir_name / f'{file_name}{self.config.get_file_extension("output")}'

            log_info("Merging video and audio...")
            try:
                log_info(f"Merging files into: {output_file}")
                
                # Check if input files exist
                if not video_input_file.exists() or (not self.only_video and not audio_input_file.exists()):
                    raise FileNotFoundError("Input files not found")
                
                if output_file.exists():
                    output_file.unlink()
                    log_info(f"Deleted existing output file: {output_file}")
                
                if self.only_video or self.only_audio:
                    input_file = video_input_file if self.only_video else audio_input_file
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
  
    def _download_video(self) -> Optional[Path]:
        try:
            log_info(f"Bilibili Downloader v{__version__}")

            if not self.config.sessdata:
                log_error("Error: SESSDATA not configured in config/user.yaml")
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get video info
            video_info = get_video_info(self.config, self.bv_id, self.config.sessdata)
            if "error" in video_info:
                log_error(f"Error: {video_info['error']}")
                return
            
            # Save video info
            with open(self.config.data_dir / 'video_info.json', 'w', encoding='utf-8') as file:
                json.dump(video_info, file, ensure_ascii=False, indent=2)
            
            # Print video information
            log_info("Video Information:")
            log_info(f"Title: {video_info.get('title')}")
            log_info(f"Description: {video_info.get('desc')}")
            log_info(f"Uploader: {video_info.get('owner', {}).get('name')}")
            log_info(f"Duration: {video_info.get('duration')} seconds")
            
            if self.only_info:
                log_info("Video information and stream URLs saved to files.")
                log_info("Only info flag is set. Skipping download.")
                return None
            
            return self._download(video_info)
        except Exception as e:
            log_error(f"Unhandled error: {e}")
            return None
