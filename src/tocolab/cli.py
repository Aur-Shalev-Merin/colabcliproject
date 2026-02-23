"""CLI entry point using Typer."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from typer.core import TyperGroup
from googleapiclient.discovery import build

from tocolab.auth import get_credentials
from tocolab.notebook import create_notebook, load_ipynb
from tocolab.drive import upload_notebook, download_notebook, find_or_create_folder
from tocolab.colab import get_colab_url, open_in_browser, parse_file_id
from tocolab.output import render_notebook
from tocolab.config import EXIT_USER_ERROR, EXIT_NETWORK_ERROR, LAST_PUSH_FILE


class _DefaultGroup(TyperGroup):
    """Typer Group that routes unknown commands to the 'push' command."""

    def parse_args(self, ctx, args):
        # If first arg doesn't match a registered command, prepend "push"
        if args and args[0] not in self.commands:
            args = ["push"] + list(args)
        elif not args:
            args = ["push"]
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="tocolab",
    help="Push code to Google Colab from the command line.",
    add_completion=False,
    cls=_DefaultGroup,
)


def _save_last_push(file_id: str, name: str) -> None:
    """Persist the most recently pushed notebook's file ID and name."""
    LAST_PUSH_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_PUSH_FILE.write_text(
        json.dumps({"file_id": file_id, "name": name}), encoding="utf-8"
    )


def _load_last_push() -> dict:
    """Load the most recently pushed notebook info.

    Returns:
        Dict with 'file_id' and 'name' keys.

    Raises:
        SystemExit: If no previous push is recorded.
    """
    if not LAST_PUSH_FILE.exists():
        sys.stderr.write("Error: No previous push found. Push a notebook first.\n")
        raise SystemExit(EXIT_USER_ERROR)
    return json.loads(LAST_PUSH_FILE.read_text(encoding="utf-8"))


@app.command(name="push", hidden=True)
def push(
    source: Optional[Path] = typer.Argument(
        None, help="File path (.py or .ipynb), or omit to read from stdin."
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Notebook title."
    ),
    gpu: bool = typer.Option(False, "--gpu", help="Set Colab runtime to GPU."),
    tpu: bool = typer.Option(False, "--tpu", help="Set Colab runtime to TPU."),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Drive folder name to upload into."
    ),
    no_open: bool = typer.Option(
        False, "--no-open", help="Don't open browser, just print URL."
    ),
    copy: bool = typer.Option(
        False, "--copy", "-c", help="Copy URL to clipboard."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full error traces."
    ),
):
    """Push code to Google Colab as a runnable notebook."""
    try:
        _run(source, name, gpu, tpu, folder, no_open, copy, verbose)
    except SystemExit:
        raise
    except Exception as e:
        if verbose:
            raise
        sys.stderr.write(f"Error: {e}\n")
        raise SystemExit(EXIT_NETWORK_ERROR)


def _run(source, name, gpu, tpu, folder, no_open, copy, verbose):
    # Determine accelerator
    accelerator = None
    if gpu:
        accelerator = "GPU"
    elif tpu:
        accelerator = "TPU"

    # Read input
    if source is not None:
        if not source.exists():
            sys.stderr.write(f"Error: File not found: {source}\n")
            raise SystemExit(EXIT_USER_ERROR)

        content = source.read_text(encoding="utf-8")
        notebook_name = name or source.stem
        is_ipynb = source.suffix == ".ipynb"
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
        notebook_name = name or "Untitled"
        is_ipynb = False
    else:
        sys.stderr.write(
            "Error: No input provided. Pipe code via stdin or pass a file path.\n"
        )
        raise SystemExit(EXIT_USER_ERROR)

    if not content.strip():
        sys.stderr.write("Error: Input is empty.\n")
        raise SystemExit(EXIT_USER_ERROR)

    # Create notebook
    if is_ipynb:
        nb = load_ipynb(content, accelerator=accelerator)
    else:
        nb = create_notebook(content, name=notebook_name, accelerator=accelerator)

    # Authenticate and build service
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    # Resolve folder
    folder_id = None
    if folder:
        folder_id = find_or_create_folder(service, folder)

    # Upload
    file_id = upload_notebook(service, nb, notebook_name, folder_id=folder_id)
    url = get_colab_url(file_id)

    # Track last push
    _save_last_push(file_id, notebook_name)

    sys.stderr.write(f"Uploaded: {file_id}\n")
    sys.stderr.write(f"URL: {url}\n")

    if no_open:
        print(url)
    else:
        open_in_browser(file_id)

    if copy:
        import pyperclip

        pyperclip.copy(url)
        sys.stderr.write("URL copied to clipboard.\n")


@app.command()
def pull(
    source: Optional[str] = typer.Argument(
        None, help="Colab URL or Drive file ID."
    ),
    last: bool = typer.Option(
        False, "--last", help="Pull the most recently pushed notebook."
    ),
    save: Optional[Path] = typer.Option(
        None, "--save", help="Save the executed notebook to a local file."
    ),
    raw: bool = typer.Option(
        False, "--raw", help="Print raw notebook JSON instead of rendered output."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full error traces."
    ),
):
    """Download an executed notebook from Colab and display results."""
    try:
        _run_pull(source, last, save, raw)
    except SystemExit:
        raise
    except Exception as e:
        if verbose:
            raise
        sys.stderr.write(f"Error: {e}\n")
        raise SystemExit(EXIT_NETWORK_ERROR)


def _run_pull(source, last, save, raw):
    # Resolve file ID
    if last:
        info = _load_last_push()
        file_id = info["file_id"]
        sys.stderr.write(f"Pulling last pushed notebook: {info.get('name', file_id)}\n")
    elif source:
        try:
            file_id = parse_file_id(source)
        except ValueError as e:
            sys.stderr.write(f"Error: {e}\n")
            raise SystemExit(EXIT_USER_ERROR)
    else:
        sys.stderr.write(
            "Error: Provide a Colab URL / file ID, or use --last.\n"
        )
        raise SystemExit(EXIT_USER_ERROR)

    # Authenticate and download
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    import nbformat

    nb = download_notebook(service, file_id)

    # Save locally if requested
    if save:
        save.write_text(nbformat.writes(nb), encoding="utf-8")
        sys.stderr.write(f"Saved to {save}\n")

    # Output
    if raw:
        print(nbformat.writes(nb))
    else:
        render_notebook(nb)


@app.command()
def auth():
    """Re-run the Google OAuth2 authentication flow."""
    get_credentials(force_reauth=True)
    sys.stderr.write("Authentication successful!\n")


def app_entry():
    app()
