"""Colab URL construction and browser opening."""

import re
import webbrowser

from tocolab.config import COLAB_BASE_URL

# Matches Colab URLs like:
#   https://colab.research.google.com/drive/1AbCdEfGhIjKlMnOpQrStUvWxYz
#   https://colab.google.com/drive/1AbCdEfGhIjKlMnOpQrStUvWxYz
#   with optional query params (?usp=sharing, #scrollTo=...)
_COLAB_URL_RE = re.compile(
    r"https?://colab(?:\.research)?\.google\.com/drive/([A-Za-z0-9_-]+)"
)

# Bare Drive file IDs are alphanumeric + hyphens/underscores, typically 20-60 chars
_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


def get_colab_url(file_id: str) -> str:
    """Construct Colab URL from Drive file ID."""
    return f"{COLAB_BASE_URL}/{file_id}"


def parse_file_id(source: str) -> str:
    """Extract a Google Drive file ID from a Colab URL or bare ID.

    Args:
        source: A Colab URL or a bare Drive file ID.

    Returns:
        The extracted file ID.

    Raises:
        ValueError: If the source is not a valid Colab URL or file ID.
    """
    # Try URL first
    m = _COLAB_URL_RE.search(source)
    if m:
        return m.group(1)

    # Try bare ID
    if _BARE_ID_RE.match(source.strip()):
        return source.strip()

    raise ValueError(f"Cannot parse file ID from: {source}")


def open_in_browser(file_id: str) -> None:
    """Open the notebook in Google Colab in the default browser."""
    url = get_colab_url(file_id)
    webbrowser.open(url)
