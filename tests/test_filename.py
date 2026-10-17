"""Unit tests for filename sanitisation."""
import pytest

from src.bilibili_downloader.utils.filename import MAX_NAME_BYTES, sanitize_filename


class TestSanitizeFilename:

    @pytest.mark.parametrize("name, expected", [
        ("普通标题", "普通标题"),
        ("a/b\\c", "a_b_c"),
        ('【4K】标题: "测试"?*<>|', '【4K】标题_ _测试______'),
        ("line\nbreak\ttab", "line_break_tab"),
        ("  .hidden title.  ", "hidden title"),
        ("../../etc/passwd", "_.._etc_passwd"),
        ("CON", "_CON"),
        ("nul.txt", "_nul.txt"),
    ])
    def test_sanitizes(self, name, expected):
        assert sanitize_filename(name, fallback="fb") == expected

    @pytest.mark.parametrize("name", ["", None, "..", " . ", "..."])
    def test_falls_back_when_nothing_usable(self, name):
        assert sanitize_filename(name, fallback="BV1xx411c7mD") == "BV1xx411c7mD"

    def test_truncates_on_utf8_boundary(self):
        result = sanitize_filename("中" * 200, fallback="fb")
        encoded = result.encode("utf-8")
        assert len(encoded) <= MAX_NAME_BYTES
        assert result == "中" * (MAX_NAME_BYTES // 3)
