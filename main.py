from pathlib import Path
from src.bilibili_downloader.bilibili_downloader import BilibiliDownloader

if __name__ == "__main__":
    downloader = BilibiliDownloader(Path(__file__).parent)
    video_file = downloader.download()
    print(f"Video downloaded to: {video_file}")
