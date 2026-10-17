import re
from typing import Optional

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
# Most filesystems cap a name at 255 bytes; leave room for suffixes like "_video_only.mp4"
MAX_NAME_BYTES = 200


def sanitize_filename(name: Optional[str], fallback: str) -> str:
    """Turn untrusted text (video title, uploader name) into a single safe path component.

    Path separators and characters invalid on Windows are replaced, leading/trailing dots and
    spaces are stripped (which also neutralises "." and ".."), and the result is truncated to
    MAX_NAME_BYTES of UTF-8. Returns `fallback` if nothing usable remains.
    """
    cleaned = _INVALID_CHARS.sub("_", name or "").strip(" .")
    cleaned = cleaned.encode("utf-8")[:MAX_NAME_BYTES].decode("utf-8", errors="ignore").rstrip(" .")
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned
