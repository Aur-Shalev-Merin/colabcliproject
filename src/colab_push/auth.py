"""OAuth2 authentication with Google."""

import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from colab_push.config import (
    CONFIG_DIR,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    SCOPES,
    EXIT_AUTH_ERROR,
)


def print_setup_guide() -> None:
    """Print instructions for setting up Google Cloud credentials."""
    sys.stderr.write(
        "\n"
        "=== colab-push: Setup Required ===\n"
        "\n"
        "No credentials.json found. Follow these steps:\n"
        "\n"
        "1. Go to https://console.cloud.google.com/\n"
        "2. Create a new project (or select an existing one)\n"
        "3. Enable the Google Drive API:\n"
        "   - Go to APIs & Services > Library\n"
        "   - Search for 'Google Drive API' and enable it\n"
        "4. Create OAuth credentials:\n"
        "   - Go to APIs & Services > Credentials\n"
        "   - Click 'Create Credentials' > 'OAuth client ID'\n"
        "   - Choose 'Desktop app' as the application type\n"
        "   - Download the JSON file\n"
        f"5. Save it as: {CREDENTIALS_FILE}\n"
        "6. Run: colab-push auth\n"
        "\n"
    )


def get_credentials(force_reauth: bool = False) -> Credentials:
    """Get valid Google OAuth2 credentials.

    Loads from token file if available, refreshes if expired,
    or runs full OAuth flow if needed.

    Args:
        force_reauth: If True, ignore existing token and re-run OAuth flow.

    Returns:
        Valid Credentials object.

    Raises:
        SystemExit: If credentials.json is missing (exit code 2).
    """
    if not CREDENTIALS_FILE.exists():
        print_setup_guide()
        raise SystemExit(EXIT_AUTH_ERROR)

    creds = None

    if not force_reauth and TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if creds.valid:
            return creds

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
            return creds

    # Run full OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), SCOPES
    )
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def _save_token(creds: Credentials) -> None:
    """Save credentials to token file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
