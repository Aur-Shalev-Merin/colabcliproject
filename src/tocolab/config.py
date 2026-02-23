"""Configuration paths and constants."""

from pathlib import Path

APP_NAME = "tocolab"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
CONFIG_FILE = CONFIG_DIR / "config.toml"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

COLAB_BASE_URL = "https://colab.research.google.com/drive"

# Exit codes
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_AUTH_ERROR = 2
EXIT_NETWORK_ERROR = 3
