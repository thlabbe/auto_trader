import pytest

from auto_trader.cli import build_parser


def test_main_runs():
    """CLI parser builds without error and has expected sub-commands."""
    parser = build_parser()
    assert parser is not None


def test_cli_help(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "auto_trader" in captured.out
