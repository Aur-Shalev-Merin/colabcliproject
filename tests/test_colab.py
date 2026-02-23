"""Tests for Colab URL and browser module."""

from unittest.mock import patch

from tocolab.colab import get_colab_url, open_in_browser


def test_colab_url_format():
    """URL follows Colab convention."""
    url = get_colab_url("abc123")
    assert url == "https://colab.research.google.com/drive/abc123"


def test_open_in_browser_calls_webbrowser():
    """open_in_browser opens URL with webbrowser module."""
    with patch("tocolab.colab.webbrowser.open") as mock_open:
        open_in_browser("abc123")
        mock_open.assert_called_once_with(
            "https://colab.research.google.com/drive/abc123"
        )
