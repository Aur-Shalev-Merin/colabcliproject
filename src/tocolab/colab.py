"""Colab URL construction and browser opening."""

import webbrowser

from tocolab.config import COLAB_BASE_URL


def get_colab_url(file_id: str) -> str:
    """Construct Colab URL from Drive file ID."""
    return f"{COLAB_BASE_URL}/{file_id}"


def open_in_browser(file_id: str) -> None:
    """Open the notebook in Google Colab in the default browser."""
    url = get_colab_url(file_id)
    webbrowser.open(url)
