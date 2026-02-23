"""Tests for Google Drive upload module."""

from unittest.mock import MagicMock
import nbformat

from tocolab.drive import upload_notebook, find_or_create_folder


def _make_fake_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("print('test')"))
    return nb


def test_upload_notebook_returns_file_id():
    """Upload returns the file ID from Drive API response."""
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file123"
    }

    file_id = upload_notebook(mock_service, _make_fake_notebook(), "Test Notebook")
    assert file_id == "file123"


def test_upload_sets_correct_mimetype():
    """Upload uses application/vnd.google.colab mimetype."""
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file123"
    }

    upload_notebook(mock_service, _make_fake_notebook(), "Test")
    call_kwargs = mock_service.files.return_value.create.call_args[1]
    assert call_kwargs["body"]["mimeType"] == "application/vnd.google.colab"


def test_upload_with_folder():
    """Upload places file in specified folder."""
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file123"
    }

    upload_notebook(mock_service, _make_fake_notebook(), "Test", folder_id="folder456")
    call_kwargs = mock_service.files.return_value.create.call_args[1]
    assert "folder456" in call_kwargs["body"]["parents"]


def test_find_or_create_folder_finds_existing():
    """Returns existing folder ID if found."""
    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "existing_folder"}]
    }

    folder_id = find_or_create_folder(mock_service, "My Folder")
    assert folder_id == "existing_folder"


def test_find_or_create_folder_creates_new():
    """Creates folder if not found and returns new ID."""
    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = {
        "files": []
    }
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "new_folder"
    }

    folder_id = find_or_create_folder(mock_service, "My Folder")
    assert folder_id == "new_folder"
