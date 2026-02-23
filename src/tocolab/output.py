"""Render executed notebook cell outputs for the terminal."""

import re
import sys

import nbformat

# Strip ANSI escape sequences (colors, cursor movement, etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def render_notebook(nb: nbformat.NotebookNode, file=None) -> None:
    """Print code cell inputs and outputs to the terminal.

    Markdown cells are skipped. Image data shows a placeholder.
    ANSI escape codes in output are stripped.

    Args:
        nb: A parsed Jupyter notebook.
        file: Output stream (defaults to sys.stdout).
    """
    if file is None:
        file = sys.stdout

    cell_num = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue

        cell_num += 1
        execution_count = cell.get("execution_count") or cell_num

        # Input
        print(f"--- In [{execution_count}] ---", file=file)
        print(cell.source, file=file)
        print(file=file)

        # Outputs
        outputs = cell.get("outputs", [])
        if not outputs:
            continue

        print(f"--- Out [{execution_count}] ---", file=file)
        for output in outputs:
            _render_output(output, file=file)
        print(file=file)


def _render_output(output, file) -> None:
    """Render a single cell output."""
    output_type = output.get("output_type", "")

    if output_type == "stream":
        text = output.get("text", "")
        print(_strip_ansi(text), end="", file=file)

    elif output_type in ("execute_result", "display_data"):
        data = output.get("data", {})
        if "text/plain" in data:
            print(_strip_ansi(data["text/plain"]), file=file)
        elif "image/png" in data or "image/jpeg" in data:
            print("[image output]", file=file)
        elif not data:
            pass
        else:
            # Unknown mime type — show first available
            first_key = next(iter(data))
            if first_key.startswith("image/"):
                print("[image output]", file=file)
            else:
                print(_strip_ansi(str(data[first_key])), file=file)

    elif output_type == "error":
        traceback_lines = output.get("traceback", [])
        for line in traceback_lines:
            print(_strip_ansi(line), file=file)
