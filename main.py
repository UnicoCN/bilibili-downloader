import argparse
from pathlib import Path
from src.bilibili_downloader.bilibili_downloader import BilibiliDownloader

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
        required=False,
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

def init_args():
    parser = create_parser()
    return parser.parse_args()

if __name__ == "__main__":
    args = init_args()

    downloader = BilibiliDownloader(Path(__file__).parent)
    video_file = downloader.download(args.bvid, args.output, args.only_info, args.only_video, args.only_audio)
    print(f"Video downloaded to: {video_file}")
