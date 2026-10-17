import argparse
import sys
from pathlib import Path
from src.bilibili_downloader.bilibili_downloader import BilibiliDownloader
from src.bilibili_downloader.exceptions import BilibiliDownloaderError
from src.bilibili_downloader.utils.logger import get_logger

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
            print("  Check data/video_info.json for details")
            return 0

        if video_file and video_file.exists():
            print(f"✓ Video downloaded successfully to: {video_file}")
            return 0
        print("✗ Download failed - output file was not created")
        return 1

    except KeyboardInterrupt:
        print("\n✗ Download cancelled by user")
        return 1
    except (BilibiliDownloaderError, FileNotFoundError, RuntimeError) as e:
        get_logger().error(f"✗ {type(e).__name__}: {e}")
        return 1
    except Exception as e:
        get_logger().exception(f"✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
