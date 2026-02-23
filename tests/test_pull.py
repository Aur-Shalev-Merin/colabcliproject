"""Tests for pull functionality: parse_file_id, download, output rendering, CLI."""

import io
import json
from unittest.mock import patch, MagicMock

import nbformat
import pytest
from typer.testing import CliRunner

from tocolab.colab import parse_file_id
from tocolab.drive import download_notebook
from tocolab.output import render_notebook, _strip_ansi
from tocolab.cli import app, _save_last_push, _load_last_push

runner = CliRunner()


# --- parse_file_id tests ---


def test_parse_file_id_from_colab_url():
    """Extracts file ID from a standard Colab URL."""
    url = "https://colab.research.google.com/drive/1AbCdEfGhIjKlMnOpQrStUvWxYz"
    assert parse_file_id(url) == "1AbCdEfGhIjKlMnOpQrStUvWxYz"


def test_parse_file_id_from_short_colab_url():
    """Extracts file ID from the shorter colab.google.com URL."""
    url = "https://colab.google.com/drive/1AbCdEfGhIjKlMnOpQrStUvWxYz"
    assert parse_file_id(url) == "1AbCdEfGhIjKlMnOpQrStUvWxYz"


def test_parse_file_id_from_url_with_query():
    """Ignores query parameters in URL."""
    url = "https://colab.research.google.com/drive/1AbCdEf?usp=sharing#scrollTo=cell1"
    assert parse_file_id(url) == "1AbCdEf"


def test_parse_file_id_bare_id():
    """Accepts a bare file ID string."""
    assert parse_file_id("1AbCdEfGhIjKlMnOpQrStUvWxYz") == "1AbCdEfGhIjKlMnOpQrStUvWxYz"


def test_parse_file_id_invalid():
    """Raises ValueError for unparseable input."""
    with pytest.raises(ValueError, match="Cannot parse file ID"):
        parse_file_id("short")


def test_parse_file_id_bare_id_with_whitespace():
    """Strips whitespace from bare IDs."""
    assert parse_file_id("  1AbCdEfGhIjKlMnOpQr  ") == "1AbCdEfGhIjKlMnOpQr"


# --- download_notebook tests ---


def test_download_notebook_returns_notebook_node():
    """download_notebook returns a parsed NotebookNode."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("print('hello')"))
    nb_bytes = nbformat.writes(nb).encode("utf-8")

    mock_service = MagicMock()
    mock_request = MagicMock()
    mock_service.files.return_value.get_media.return_value = mock_request

    # Simulate MediaIoBaseDownload: write bytes to buffer and return done=True
    def fake_download(buf, request):
        class FakeDownloader:
            def __init__(self, buf, data):
                self._buf = buf
                self._data = data
                self._done = False

            def next_chunk(self):
                self._buf.write(self._data)
                self._done = True
                return None, True

        return FakeDownloader(buf, nb_bytes)

    with patch("tocolab.drive.MediaIoBaseDownload", side_effect=fake_download):
        result = download_notebook(mock_service, "file123")

    assert isinstance(result, nbformat.NotebookNode)
    assert result.cells[0].source == "print('hello')"
    mock_service.files.return_value.get_media.assert_called_once_with(fileId="file123")


# --- output rendering tests ---


def _make_executed_notebook():
    """Create a notebook with various output types for testing."""
    nb = nbformat.v4.new_notebook()

    # Cell 1: stream output
    cell1 = nbformat.v4.new_code_cell("print('hello')")
    cell1.execution_count = 1
    cell1.outputs = [
        nbformat.v4.new_output(output_type="stream", name="stdout", text="hello\n")
    ]
    nb.cells.append(cell1)

    # Cell 2: execute_result
    cell2 = nbformat.v4.new_code_cell("42")
    cell2.execution_count = 2
    cell2.outputs = [
        nbformat.v4.new_output(output_type="execute_result", data={"text/plain": "42"}, metadata={}, execution_count=2)
    ]
    nb.cells.append(cell2)

    # Cell 3: error
    cell3 = nbformat.v4.new_code_cell("1/0")
    cell3.execution_count = 3
    cell3.outputs = [
        {
            "output_type": "error",
            "ename": "ZeroDivisionError",
            "evalue": "division by zero",
            "traceback": [
                "\x1b[0;31mZeroDivisionError\x1b[0m: division by zero"
            ],
        }
    ]
    nb.cells.append(cell3)

    # A markdown cell (should be skipped)
    nb.cells.append(nbformat.v4.new_markdown_cell("# Title"))

    # Cell 4: display_data with image
    cell4 = nbformat.v4.new_code_cell("display(img)")
    cell4.execution_count = 4
    cell4.outputs = [
        {
            "output_type": "display_data",
            "data": {"image/png": "iVBOR...base64..."},
            "metadata": {},
        }
    ]
    nb.cells.append(cell4)

    return nb


def test_render_notebook_stream_output():
    """Stream output (stdout) is rendered correctly."""
    nb = _make_executed_notebook()
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "--- In [1] ---" in output
    assert "print('hello')" in output
    assert "--- Out [1] ---" in output
    assert "hello" in output


def test_render_notebook_execute_result():
    """execute_result shows text/plain data."""
    nb = _make_executed_notebook()
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "--- In [2] ---" in output
    assert "--- Out [2] ---" in output
    assert "42" in output


def test_render_notebook_error_strips_ansi():
    """Error tracebacks have ANSI codes stripped."""
    nb = _make_executed_notebook()
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "ZeroDivisionError" in output
    assert "\x1b[" not in output


def test_render_notebook_skips_markdown():
    """Markdown cells are not rendered."""
    nb = _make_executed_notebook()
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "# Title" not in output


def test_render_notebook_image_placeholder():
    """Image outputs show [image output] placeholder."""
    nb = _make_executed_notebook()
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "[image output]" in output


def test_render_notebook_no_outputs():
    """Cells with no outputs only show input."""
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("x = 1")
    cell.outputs = []
    nb.cells.append(cell)
    buf = io.StringIO()
    render_notebook(nb, file=buf)
    output = buf.getvalue()
    assert "--- In [1] ---" in output
    assert "x = 1" in output
    assert "--- Out" not in output


def test_strip_ansi():
    """_strip_ansi removes ANSI escape codes."""
    assert _strip_ansi("\x1b[0;31mred\x1b[0m") == "red"
    assert _strip_ansi("plain text") == "plain text"


# --- last push helpers ---


def test_save_and_load_last_push(tmp_path):
    """_save_last_push persists data that _load_last_push can read."""
    last_push_file = tmp_path / "last_push.json"
    with patch("tocolab.cli.LAST_PUSH_FILE", last_push_file):
        _save_last_push("abc123", "my_notebook")
        info = _load_last_push()
    assert info["file_id"] == "abc123"
    assert info["name"] == "my_notebook"


def test_load_last_push_missing(tmp_path):
    """_load_last_push exits with error when no file exists."""
    last_push_file = tmp_path / "nonexistent" / "last_push.json"
    with patch("tocolab.cli.LAST_PUSH_FILE", last_push_file):
        with pytest.raises(SystemExit):
            _load_last_push()


# --- CLI pull command tests ---


def test_pull_no_source_no_last():
    """pull with no arguments shows error."""
    result = runner.invoke(app, ["pull"])
    assert result.exit_code != 0


def test_pull_with_file_id(tmp_path):
    """pull downloads and renders a notebook."""
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("print('hi')")
    cell.execution_count = 1
    cell.outputs = [
        nbformat.v4.new_output(output_type="stream", name="stdout", text="hi\n")
    ]
    nb.cells.append(cell)

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.download_notebook", return_value=nb),
    ):
        result = runner.invoke(app, ["pull", "1AbCdEfGhIjKlMnOp"])
        assert result.exit_code == 0
        assert "--- In [1] ---" in result.output
        assert "hi" in result.output


def test_pull_save_writes_file(tmp_path):
    """pull --save writes the notebook to a local file."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))

    mock_creds = MagicMock()
    mock_service = MagicMock()
    out_file = tmp_path / "output.ipynb"

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.download_notebook", return_value=nb),
    ):
        result = runner.invoke(app, ["pull", "1AbCdEfGhIjKl", "--save", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        saved = nbformat.read(str(out_file), as_version=4)
        assert saved.cells[0].source == "x = 1"


def test_pull_raw_outputs_json():
    """pull --raw prints raw notebook JSON."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.download_notebook", return_value=nb),
    ):
        result = runner.invoke(app, ["pull", "1AbCdEfGhIjKl", "--raw"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        # nbformat may serialize source as string or list of lines
        source = parsed["cells"][0]["source"]
        if isinstance(source, list):
            source = "".join(source)
        assert source == "x = 1"
