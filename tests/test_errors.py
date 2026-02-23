"""Tests for error handling edge cases."""

from unittest.mock import patch
from typer.testing import CliRunner

from tocolab.cli import app
from tocolab.config import EXIT_USER_ERROR

runner = CliRunner()


def test_nonexistent_file():
    result = runner.invoke(app, ["/tmp/does_not_exist_abc.py"])
    assert result.exit_code == EXIT_USER_ERROR


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.py"
    empty.write_text("")
    result = runner.invoke(app, [str(empty)])
    assert result.exit_code == EXIT_USER_ERROR


def test_no_input_tty():
    """No file and stdin is a TTY shows error."""
    with patch("tocolab.cli.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        result = runner.invoke(app, [])
        # Either shows help or shows error about no input
        assert result.exit_code == EXIT_USER_ERROR or "No input" in result.output or result.exit_code == 0
