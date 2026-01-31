import argparse
import sys
import logging
from pathlib import Path
from src.bilibili_downloader.bilibili_downloader import BilibiliDownloader

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Download videos from Bilibili using BV ID',
        epilog='Example: python main.py -id BV1xx411c7mD -o ./my_videos',
        formatter_class=argparse.RawDescriptionHelpFormatter
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

def init_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = create_parser()
    return parser.parse_args()

def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = init_args()

    try:
        downloader = BilibiliDownloader(Path(__file__).parent)
        video_file = downloader.download(
            args.bvid, args.output, args.only_info,
            args.only_video, args.only_audio
        )

        if args.only_info:
            print("✓ Video information fetched successfully")
            print("  Check data/video_info.json and data/video_stream_info.json for details")
            return 0

        if video_file and video_file.exists():
            print(f"✓ Video downloaded successfully to: {video_file}")
            return 0
        else:
            print("✗ Download failed - check logs/bilibili_downloader.log for details")
            return 1

    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        return 1
    except RuntimeError as e:
        print(f"✗ Runtime error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n✗ Download cancelled by user")
        return 1
    except Exception as e:
        logging.exception("Unexpected error occurred")
        print(f"✗ Unexpected error: {e}")
        print("  Check logs/bilibili_downloader.log for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())
