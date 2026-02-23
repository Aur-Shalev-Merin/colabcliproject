"""Google Drive API: upload notebooks."""

from typing import Optional

import nbformat
from googleapiclient.http import MediaInMemoryUpload


def upload_notebook(
    service,
    notebook: nbformat.NotebookNode,
    name: str,
    *,
    folder_id: Optional[str] = None,
) -> str:
    """Upload a notebook to Google Drive.

    Args:
        service: Authenticated Google Drive API service.
        notebook: The notebook to upload.
        name: Display name for the file.
        folder_id: Optional Drive folder ID to upload into.

    Returns:
        The Google Drive file ID of the uploaded notebook.
    """
    notebook_json = nbformat.writes(notebook)

    body = {
        "name": f"{name}.ipynb",
        "mimeType": "application/vnd.google.colab",
    }
    if folder_id:
        body["parents"] = [folder_id]

    media = MediaInMemoryUpload(
        notebook_json.encode("utf-8"),
        mimetype="application/x-ipynb+json",
        resumable=False,
    )

    file = service.files().create(
        body=body,
        media_body=media,
        fields="id",
    ).execute()

    return file["id"]


def find_or_create_folder(service, folder_name: str) -> str:
    """Find a Drive folder by name, or create it if it doesn't exist.

    Args:
        service: Authenticated Google Drive API service.
        folder_name: Name of the folder to find or create.

    Returns:
        The Google Drive folder ID.
    """
    query = (
        f"name = '{folder_name}' and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        "trashed = false"
    )
    results = service.files().list(
        q=query, spaces="drive", fields="files(id)"
    ).execute()

    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # Create the folder
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(
        body=folder_metadata, fields="id"
    ).execute()

    return folder["id"]
