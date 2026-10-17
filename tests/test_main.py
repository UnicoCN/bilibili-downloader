"""Unit tests for command-line parsing."""
import pytest

from main import create_parser


class TestArgumentParser:

    @pytest.mark.parametrize("flags", [
        ["--only-video", "--only-audio"],
        ["--only-info", "--only-video"],
        ["--only-info", "--only-audio"],
    ])
    def test_mode_flags_are_mutually_exclusive(self, flags, capsys):
        with pytest.raises(SystemExit) as exc:
            create_parser().parse_args(["-id", "BV1xx411c7mD", *flags])
        assert exc.value.code == 2
        assert "not allowed with argument" in capsys.readouterr().err

    def test_single_mode_flag_is_accepted(self):
        args = create_parser().parse_args(["-id", "BV1xx411c7mD", "--only-audio"])
        assert args.only_audio and not args.only_video and not args.only_info
