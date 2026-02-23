"""Tests for CLI entry point."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from colab_push.cli import app

runner = CliRunner()


def test_help_shows_description():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Colab" in result.output


def test_file_input(tmp_path):
    """File path argument reads file and uploads."""
    py_file = tmp_path / "test.py"
    py_file.write_text("print('from file')")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_xyz"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file)])
        assert result.exit_code == 0
        mock_browser.assert_called_once_with("file_xyz")


def test_no_open_flag(tmp_path):
    """--no-open skips browser, prints URL to stdout."""
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 1")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_noop"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file), "--no-open"])
        assert result.exit_code == 0
        mock_browser.assert_not_called()
        assert "colab.research.google.com/drive/file_noop" in result.output


def test_auth_subcommand():
    """colab-push auth triggers re-authentication."""
    with patch("colab_push.cli.get_credentials") as mock_auth:
        result = runner.invoke(app, ["auth"])
        mock_auth.assert_called_once_with(force_reauth=True)
        assert result.exit_code == 0
