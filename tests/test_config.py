"""Tests for config module."""

from pathlib import Path
from colab_push.config import CONFIG_DIR, CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def test_config_dir_is_under_home():
    assert str(Path.home()) in str(CONFIG_DIR)
    assert "colab-push" in str(CONFIG_DIR)


def test_credentials_file_in_config_dir():
    assert CREDENTIALS_FILE.parent == CONFIG_DIR
    assert CREDENTIALS_FILE.name == "credentials.json"


def test_token_file_in_config_dir():
    assert TOKEN_FILE.parent == CONFIG_DIR
    assert TOKEN_FILE.name == "token.json"


def test_scopes_contains_drive_file():
    assert len(SCOPES) == 1
    assert "drive.file" in SCOPES[0]
