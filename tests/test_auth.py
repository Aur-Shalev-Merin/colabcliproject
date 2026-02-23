"""Tests for auth module."""

from unittest.mock import patch, MagicMock

import pytest

from colab_push.auth import get_credentials, print_setup_guide
from colab_push.config import EXIT_AUTH_ERROR


def test_print_setup_guide_on_missing_credentials(capsys, tmp_path):
    """When credentials.json doesn't exist, print a setup guide and exit."""
    fake_creds = tmp_path / "credentials.json"
    with patch("colab_push.auth.CREDENTIALS_FILE", fake_creds):
        with pytest.raises(SystemExit) as exc_info:
            get_credentials()
        assert exc_info.value.code == EXIT_AUTH_ERROR
    captured = capsys.readouterr()
    assert "credentials.json" in captured.err
    assert "console.cloud.google.com" in captured.err


def test_loads_existing_valid_token(tmp_path):
    """When a valid token exists, return it without re-auth."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"

    mock_creds = MagicMock()
    mock_creds.valid = True

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.Credentials.from_authorized_user_file", return_value=mock_creds) as mock_load,
    ):
        fake_token.write_text('{"token": "fake"}')
        result = get_credentials()
        mock_load.assert_called_once()
        assert result is mock_creds


def test_refreshes_expired_token(tmp_path):
    """When token exists but is expired, refresh it."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"
    fake_token.write_text('{"token": "fake"}')

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_me"

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.CONFIG_DIR", tmp_path),
        patch("colab_push.auth.Credentials.from_authorized_user_file", return_value=mock_creds),
        patch("colab_push.auth.Request") as mock_request,
    ):
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        result = get_credentials()
        mock_creds.refresh.assert_called_once_with(mock_request.return_value)
        assert result is mock_creds


def test_runs_oauth_flow_when_no_token(tmp_path):
    """When no token exists, run the full OAuth flow."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"
    # no token file exists

    mock_flow_creds = MagicMock()
    mock_flow_creds.to_json.return_value = '{"token": "new"}'
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_flow_creds

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.CONFIG_DIR", tmp_path),
        patch("colab_push.auth.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow),
    ):
        result = get_credentials()
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is mock_flow_creds
        assert fake_token.read_text() == '{"token": "new"}'


def test_setup_guide_has_actionable_steps(capsys):
    """The setup guide should have numbered steps."""
    print_setup_guide()
    captured = capsys.readouterr()
    assert "1." in captured.err
    assert "2." in captured.err
    assert "Drive API" in captured.err
