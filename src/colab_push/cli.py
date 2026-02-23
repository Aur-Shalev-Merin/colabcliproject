"""CLI entry point using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer
from typer.core import TyperGroup
from googleapiclient.discovery import build

from colab_push.auth import get_credentials
from colab_push.notebook import create_notebook, load_ipynb
from colab_push.drive import upload_notebook, find_or_create_folder
from colab_push.colab import get_colab_url, open_in_browser
from colab_push.config import EXIT_USER_ERROR, EXIT_NETWORK_ERROR


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
    name="colab-push",
    help="Push code to Google Colab from the command line.",
    add_completion=False,
    cls=_DefaultGroup,
)


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
def auth():
    """Re-run the Google OAuth2 authentication flow."""
    get_credentials(force_reauth=True)
    sys.stderr.write("Authentication successful!\n")


def app_entry():
    app()
