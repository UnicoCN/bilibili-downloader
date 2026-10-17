class BilibiliDownloaderError(Exception):
    """Base class for all errors raised by the downloader"""


class BilibiliAPIError(BilibiliDownloaderError):
    """Bilibili API request failed or returned an error response"""


class DownloadError(BilibiliDownloaderError):
    """Stream download failed"""


class MergeError(BilibiliDownloaderError):
    """FFmpeg failed to produce the output file"""
