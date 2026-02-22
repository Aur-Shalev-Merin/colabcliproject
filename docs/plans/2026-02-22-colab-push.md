# colab-push Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that takes Python code from stdin or a file and pushes it to Google Colab as a runnable notebook via the Google Drive API, then opens it in the browser.

**Architecture:** Typer-based CLI with six modules: cli.py (entry point), auth.py (OAuth2), notebook.py (nbformat generation), drive.py (Google Drive upload), colab.py (URL + browser), config.py (paths + constants). Auth stores tokens at `~/.config/colab-push/token.json`, expects user-provided `credentials.json` in the same directory.

**Tech Stack:** Python 3.10+, uv, Typer, google-auth-oauthlib, google-api-python-client, nbformat, pytest

---

## Task 0: Project Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `src/colab_push/__init__.py`
- Create: `src/colab_push/cli.py`
- Create: `src/colab_push/auth.py`
- Create: `src/colab_push/notebook.py`
- Create: `src/colab_push/drive.py`
- Create: `src/colab_push/colab.py`
- Create: `src/colab_push/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Update pyproject.toml with dependencies and entry point**

```toml
[project]
name = "colab-push"
version = "0.1.0"
description = "Push code to Google Colab from the command line"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.9.0",
    "google-auth-oauthlib>=1.0.0",
    "google-api-python-client>=2.0.0",
    "nbformat>=5.0.0",
    "pyperclip>=1.8.0",
]

[project.scripts]
colab-push = "colab_push.cli:app_entry"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = ["pytest>=7.0.0"]
```

**Step 2: Create all module stubs**

`src/colab_push/__init__.py`:
```python
"""colab-push: Push code to Google Colab from the command line."""

__version__ = "0.1.0"
```

`src/colab_push/config.py`:
```python
"""Configuration paths and constants."""

from pathlib import Path
import sys

APP_NAME = "colab-push"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
CONFIG_FILE = CONFIG_DIR / "config.toml"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

COLAB_BASE_URL = "https://colab.research.google.com/drive"

# Exit codes
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_AUTH_ERROR = 2
EXIT_NETWORK_ERROR = 3
```

`src/colab_push/cli.py` — minimal stub:
```python
"""CLI entry point using Typer."""

import typer

app = typer.Typer(
    name="colab-push",
    help="Push code to Google Colab from the command line.",
    add_completion=False,
)


def app_entry():
    app()
```

`src/colab_push/auth.py` — stub:
```python
"""OAuth2 authentication with Google."""
```

`src/colab_push/notebook.py` — stub:
```python
"""Notebook generation from source code."""
```

`src/colab_push/drive.py` — stub:
```python
"""Google Drive API: upload notebooks."""
```

`src/colab_push/colab.py` — stub:
```python
"""Colab URL construction and browser opening."""
```

`tests/__init__.py` — empty file.

`tests/conftest.py`:
```python
"""Shared test fixtures."""
```

**Step 3: Install dependencies and verify entry point**

Run: `uv sync`
Expected: dependencies installed, lockfile created

Run: `uv run colab-push --help`
Expected: shows help text with "Push code to Google Colab from the command line."

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with module stubs and dependencies"
```

---

## Task 1: Config Module

**Files:**
- Modify: `src/colab_push/config.py` (already has constants from Task 0)
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

`tests/test_config.py`:
```python
"""Tests for config module."""

from pathlib import Path
from colab_push.config import CONFIG_DIR, CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def test_config_dir_is_under_home():
    assert str(Path.home()) in str(CONFIG_DIR)
    assert "colab-push" in str(CONFIG_DIR)


def test_credentials_file_in_config_dir():
    assert CREDENTIALS_FILE.parent == CONFIG_DIR
    assert CREDENTIALS_FILE.name == "credentials.json"


def test_token_file_in_config_dir():
    assert TOKEN_FILE.parent == CONFIG_DIR
    assert TOKEN_FILE.name == "token.json"


def test_scopes_contains_drive_file():
    assert len(SCOPES) == 1
    assert "drive.file" in SCOPES[0]
```

**Step 2: Run test to verify it passes** (config.py already has the constants)

Run: `uv run pytest tests/test_config.py -v`
Expected: all 4 tests PASS

**Step 3: Commit**

```bash
git add tests/test_config.py
git commit -m "test: add config module tests"
```

---

## Task 2: Auth Module

**Files:**
- Modify: `src/colab_push/auth.py`
- Test: `tests/test_auth.py`

**Step 1: Write the failing tests**

`tests/test_auth.py`:
```python
"""Tests for auth module."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from colab_push.auth import get_credentials, print_setup_guide
from colab_push.config import EXIT_AUTH_ERROR


def test_print_setup_guide_on_missing_credentials(capsys, tmp_path):
    """When credentials.json doesn't exist, print a setup guide and exit."""
    fake_creds = tmp_path / "credentials.json"
    with patch("colab_push.auth.CREDENTIALS_FILE", fake_creds):
        with pytest.raises(SystemExit) as exc_info:
            get_credentials()
        assert exc_info.value.code == EXIT_AUTH_ERROR
    captured = capsys.readouterr()
    assert "credentials.json" in captured.err
    assert "Google Cloud Console" in captured.err


def test_loads_existing_valid_token(tmp_path):
    """When a valid token exists, return it without re-auth."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"

    mock_creds = MagicMock()
    mock_creds.valid = True

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.Credentials.from_authorized_user_file", return_value=mock_creds) as mock_load,
    ):
        fake_token.write_text('{"token": "fake"}')
        result = get_credentials()
        mock_load.assert_called_once()
        assert result is mock_creds


def test_refreshes_expired_token(tmp_path):
    """When token exists but is expired, refresh it."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"
    fake_token.write_text('{"token": "fake"}')

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_me"

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.Credentials.from_authorized_user_file", return_value=mock_creds),
        patch("colab_push.auth.Request") as mock_request,
    ):
        result = get_credentials()
        mock_creds.refresh.assert_called_once_with(mock_request.return_value)
        assert result is mock_creds


def test_runs_oauth_flow_when_no_token(tmp_path):
    """When no token exists, run the full OAuth flow."""
    fake_creds = tmp_path / "credentials.json"
    fake_creds.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    fake_token = tmp_path / "token.json"
    # no token file exists

    mock_flow_creds = MagicMock()
    mock_flow_creds.to_json.return_value = '{"token": "new"}'
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_flow_creds

    with (
        patch("colab_push.auth.CREDENTIALS_FILE", fake_creds),
        patch("colab_push.auth.TOKEN_FILE", fake_token),
        patch("colab_push.auth.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow),
    ):
        result = get_credentials()
        mock_flow.run_local_server.assert_called_once_with(port=0)
        assert result is mock_flow_creds
        assert fake_token.read_text() == '{"token": "new"}'


def test_setup_guide_has_actionable_steps(capsys):
    """The setup guide should have numbered steps."""
    print_setup_guide()
    captured = capsys.readouterr()
    assert "1." in captured.err
    assert "2." in captured.err
    assert "Drive API" in captured.err
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_auth.py -v`
Expected: FAIL — `get_credentials` and `print_setup_guide` not defined

**Step 3: Implement auth.py**

```python
"""OAuth2 authentication with Google."""

import sys
from pathlib import Path

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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_auth.py -v`
Expected: all 5 tests PASS

**Step 5: Commit**

```bash
git add src/colab_push/auth.py tests/test_auth.py
git commit -m "feat: implement OAuth2 auth with token caching and setup guide"
```

---

## Task 3: Notebook Generation (basic single-cell)

**Files:**
- Modify: `src/colab_push/notebook.py`
- Test: `tests/test_notebook.py`

**Step 1: Write the failing tests**

`tests/test_notebook.py`:
```python
"""Tests for notebook generation."""

import json
import nbformat

from colab_push.notebook import create_notebook


def test_single_cell_from_source():
    """Plain source code becomes a single code cell."""
    source = "print('hello world')"
    nb = create_notebook(source)
    assert nb.nbformat == 4
    assert len(nb.cells) == 1
    assert nb.cells[0].cell_type == "code"
    assert nb.cells[0].source == source


def test_notebook_has_python3_kernel():
    """Notebook metadata specifies python3 kernel."""
    nb = create_notebook("x = 1")
    assert nb.metadata.kernelspec.name == "python3"
    assert nb.metadata.kernelspec.display_name == "Python 3"


def test_notebook_name_set():
    """Notebook name is set in metadata when provided."""
    nb = create_notebook("x = 1", name="My Experiment")
    assert nb.metadata.get("colab", {}).get("name") == "My Experiment"


def test_gpu_accelerator():
    """--gpu sets accelerator in colab metadata."""
    nb = create_notebook("x = 1", accelerator="GPU")
    assert nb.metadata["colab"]["accelerator"] == "GPU"


def test_tpu_accelerator():
    """--tpu sets accelerator in colab metadata."""
    nb = create_notebook("x = 1", accelerator="TPU")
    assert nb.metadata["colab"]["accelerator"] == "TPU"


def test_no_accelerator_by_default():
    """No accelerator metadata when not requested."""
    nb = create_notebook("x = 1")
    colab_meta = nb.metadata.get("colab", {})
    assert "accelerator" not in colab_meta or colab_meta.get("name")  # name is ok


def test_notebook_is_valid():
    """Generated notebook passes nbformat validation."""
    nb = create_notebook("import os\nprint(os.getcwd())")
    nbformat.validate(nb)  # raises if invalid
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_notebook.py -v`
Expected: FAIL — `create_notebook` not defined

**Step 3: Implement notebook.py (basic)**

```python
"""Notebook generation from source code."""

from typing import Optional

import nbformat
from nbformat.v4 import new_notebook, new_code_cell


def create_notebook(
    source: str,
    *,
    name: Optional[str] = None,
    accelerator: Optional[str] = None,
) -> nbformat.NotebookNode:
    """Create a Jupyter notebook from source code.

    Args:
        source: Python source code string.
        name: Optional notebook display name.
        accelerator: Optional accelerator type ("GPU" or "TPU").

    Returns:
        A valid NotebookNode.
    """
    nb = new_notebook()

    # Kernel metadata
    nb.metadata.kernelspec = {
        "name": "python3",
        "display_name": "Python 3",
    }

    # Colab metadata
    colab_meta = {}
    if name:
        colab_meta["name"] = name
    if accelerator:
        colab_meta["accelerator"] = accelerator
    if colab_meta:
        nb.metadata["colab"] = colab_meta

    # Create cells
    cells = _split_cells(source)
    for cell_source in cells:
        nb.cells.append(new_code_cell(source=cell_source))

    return nb


def _split_cells(source: str) -> list[str]:
    """Split source into cells on '# %%' or '# In[' markers.

    If no markers found, return the entire source as one cell.
    """
    import re

    marker = re.compile(r"^# %%|^# In\[", re.MULTILINE)
    splits = list(marker.finditer(source))

    if not splits:
        return [source]

    cells = []
    # Content before first marker (if any)
    if splits[0].start() > 0:
        preamble = source[: splits[0].start()].strip()
        if preamble:
            cells.append(preamble)

    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(source)
        cell_text = source[start:end].strip()
        if cell_text:
            cells.append(cell_text)

    return cells if cells else [source]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_notebook.py -v`
Expected: all 7 tests PASS

**Step 5: Commit**

```bash
git add src/colab_push/notebook.py tests/test_notebook.py
git commit -m "feat: notebook generation with cell splitting and colab metadata"
```

---

## Task 4: Cell Splitting Tests (edge cases)

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1: Add edge-case tests for cell splitting**

Append to `tests/test_notebook.py`:
```python
def test_split_cells_on_percent_marker():
    """Source with # %% markers splits into multiple cells."""
    source = "x = 1\n# %%\ny = 2\n# %%\nz = 3"
    nb = create_notebook(source)
    assert len(nb.cells) == 3


def test_split_cells_on_in_marker():
    """Source with # In[] markers splits into cells."""
    source = "# In[1]:\nx = 1\n# In[2]:\ny = 2"
    nb = create_notebook(source)
    assert len(nb.cells) == 2


def test_no_markers_single_cell():
    """Source without markers stays as one cell."""
    source = "x = 1\ny = 2\nz = 3"
    nb = create_notebook(source)
    assert len(nb.cells) == 1
    assert nb.cells[0].source == source


def test_empty_source():
    """Empty string produces one empty cell."""
    nb = create_notebook("")
    assert len(nb.cells) == 1
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_notebook.py -v`
Expected: all 11 tests PASS (if any fail, fix _split_cells logic)

**Step 3: Commit**

```bash
git add tests/test_notebook.py
git commit -m "test: add cell splitting edge case tests"
```

---

## Task 5: Auto Pip-Install Cell (dependency detection)

**Files:**
- Modify: `src/colab_push/notebook.py`
- Modify: `tests/test_notebook.py`

**Step 1: Write the failing tests**

Append to `tests/test_notebook.py`:
```python
from colab_push.notebook import detect_third_party_imports


def test_detect_third_party_imports():
    """Detects non-stdlib imports."""
    source = "import numpy\nimport os\nfrom pathlib import Path\nimport torch"
    imports = detect_third_party_imports(source)
    assert "numpy" in imports
    assert "torch" in imports
    assert "os" not in imports
    assert "pathlib" not in imports


def test_known_package_name_mapping():
    """cv2 maps to opencv-python, PIL to Pillow, etc."""
    source = "import cv2\nfrom PIL import Image\nimport sklearn"
    imports = detect_third_party_imports(source)
    assert "opencv-python" in imports
    assert "Pillow" in imports
    assert "scikit-learn" in imports


def test_pip_install_cell_prepended():
    """When third-party imports detected, a setup cell is prepended."""
    source = "import numpy\nimport torch\nprint('hello')"
    nb = create_notebook(source)
    assert len(nb.cells) == 2  # setup cell + code cell
    assert "!pip install" in nb.cells[0].source
    assert "numpy" in nb.cells[0].source
    assert "torch" in nb.cells[0].source


def test_no_pip_cell_for_stdlib_only():
    """No setup cell when all imports are stdlib."""
    source = "import os\nimport sys\nprint('hello')"
    nb = create_notebook(source)
    assert len(nb.cells) == 1  # just the code cell
    assert "pip" not in nb.cells[0].source
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_notebook.py::test_detect_third_party_imports -v`
Expected: FAIL — `detect_third_party_imports` not defined

**Step 3: Implement dependency detection**

Add to `src/colab_push/notebook.py`:

```python
import re
import sys

# Common import-name → pip-package-name mismatches
IMPORT_TO_PACKAGE = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "attr": "attrs",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "gi": "PyGObject",
    "wx": "wxPython",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "usb": "pyusb",
    "Bio": "biopython",
    "cv": "opencv-python",
    "dotenv": "python-dotenv",
    "jose": "python-jose",
    "magic": "python-magic",
    "dateutil": "python-dateutil",
    "lxml": "lxml",
    "git": "GitPython",
}


def detect_third_party_imports(source: str) -> list[str]:
    """Detect third-party imports and return pip package names.

    Scans for `import X` and `from X import ...` statements,
    filters out stdlib modules, and maps known mismatches.
    """
    import_pattern = re.compile(
        r"^(?:import|from)\s+(\w+)", re.MULTILINE
    )
    found_modules = set()
    for match in import_pattern.finditer(source):
        found_modules.add(match.group(1))

    stdlib = sys.stdlib_module_names

    third_party = []
    for mod in sorted(found_modules):
        if mod in stdlib:
            continue
        package_name = IMPORT_TO_PACKAGE.get(mod, mod)
        third_party.append(package_name)

    return third_party
```

Update `create_notebook` to prepend pip install cell — insert before existing cells:

```python
def create_notebook(source, *, name=None, accelerator=None):
    # ... existing code ...

    # Detect dependencies and prepend setup cell
    third_party = detect_third_party_imports(source)
    if third_party:
        install_lines = " ".join(third_party)
        setup_source = (
            "# Auto-detected dependencies\n"
            f"!pip install -q {install_lines}"
        )
        nb.cells.insert(0, new_code_cell(source=setup_source))

    return nb
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_notebook.py -v`
Expected: all 15 tests PASS

**Step 5: Commit**

```bash
git add src/colab_push/notebook.py tests/test_notebook.py
git commit -m "feat: auto-detect third-party imports and prepend pip install cell"
```

---

## Task 6: Colab URL + Browser Module

**Files:**
- Modify: `src/colab_push/colab.py`
- Test: `tests/test_colab.py`

**Step 1: Write the failing tests**

`tests/test_colab.py`:
```python
"""Tests for Colab URL and browser module."""

from unittest.mock import patch

from colab_push.colab import get_colab_url, open_in_browser


def test_colab_url_format():
    """URL follows Colab convention."""
    url = get_colab_url("abc123")
    assert url == "https://colab.research.google.com/drive/abc123"


def test_open_in_browser_calls_webbrowser(capsys):
    """open_in_browser opens URL with webbrowser module."""
    with patch("colab_push.colab.webbrowser.open") as mock_open:
        open_in_browser("abc123")
        mock_open.assert_called_once_with(
            "https://colab.research.google.com/drive/abc123"
        )
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_colab.py -v`
Expected: FAIL

**Step 3: Implement colab.py**

```python
"""Colab URL construction and browser opening."""

import webbrowser

from colab_push.config import COLAB_BASE_URL


def get_colab_url(file_id: str) -> str:
    """Construct Colab URL from Drive file ID."""
    return f"{COLAB_BASE_URL}/{file_id}"


def open_in_browser(file_id: str) -> None:
    """Open the notebook in Google Colab in the default browser."""
    url = get_colab_url(file_id)
    webbrowser.open(url)
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_colab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/colab_push/colab.py tests/test_colab.py
git commit -m "feat: colab URL construction and browser opening"
```

---

## Task 7: Drive Upload Module

**Files:**
- Modify: `src/colab_push/drive.py`
- Test: `tests/test_drive.py`

**Step 1: Write the failing tests**

`tests/test_drive.py`:
```python
"""Tests for Google Drive upload module."""

from unittest.mock import patch, MagicMock
import nbformat

from colab_push.drive import upload_notebook, find_or_create_folder


def _make_fake_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("print('test')"))
    return nb


def test_upload_notebook_returns_file_id():
    """Upload returns the file ID from Drive API response."""
    mock_service = MagicMock()
    mock_create = mock_service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "file123"}

    file_id = upload_notebook(mock_service, _make_fake_notebook(), "Test Notebook")
    assert file_id == "file123"


def test_upload_sets_correct_mimetype():
    """Upload uses application/vnd.google.colab mimetype."""
    mock_service = MagicMock()
    mock_create = mock_service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "file123"}

    upload_notebook(mock_service, _make_fake_notebook(), "Test")
    call_kwargs = mock_create.call_args
    body = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][0]
    assert body["mimeType"] == "application/vnd.google.colab"


def test_upload_with_folder():
    """Upload places file in specified folder."""
    mock_service = MagicMock()
    mock_create = mock_service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "file123"}

    upload_notebook(mock_service, _make_fake_notebook(), "Test", folder_id="folder456")
    call_kwargs = mock_create.call_args[1]
    assert "folder456" in call_kwargs["body"]["parents"]


def test_find_or_create_folder_finds_existing():
    """Returns existing folder ID if found."""
    mock_service = MagicMock()
    mock_list = mock_service.files.return_value.list
    mock_list.return_value.execute.return_value = {
        "files": [{"id": "existing_folder"}]
    }

    folder_id = find_or_create_folder(mock_service, "My Folder")
    assert folder_id == "existing_folder"


def test_find_or_create_folder_creates_new():
    """Creates folder if not found and returns new ID."""
    mock_service = MagicMock()
    mock_list = mock_service.files.return_value.list
    mock_list.return_value.execute.return_value = {"files": []}

    mock_create = mock_service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "new_folder"}

    folder_id = find_or_create_folder(mock_service, "My Folder")
    assert folder_id == "new_folder"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_drive.py -v`
Expected: FAIL

**Step 3: Implement drive.py**

```python
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
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_drive.py -v`
Expected: all 5 tests PASS

**Step 5: Commit**

```bash
git add src/colab_push/drive.py tests/test_drive.py
git commit -m "feat: Drive upload with folder creation support"
```

---

## Task 8: CLI – Main Command (wiring everything together)

**Files:**
- Modify: `src/colab_push/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
"""Tests for CLI entry point."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from colab_push.cli import app

runner = CliRunner()


def test_help_shows_description():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Colab" in result.output


def test_stdin_input(tmp_path):
    """Piped stdin is read and uploaded."""
    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_abc"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
        patch("colab_push.cli.sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "print('hello')"

        result = runner.invoke(app, [], input="print('hello')")
        # Should not crash — auth + upload mocked
        assert result.exit_code == 0 or "file_abc" in result.output or mock_browser.called


def test_file_input(tmp_path):
    """File path argument reads file and uploads."""
    py_file = tmp_path / "test.py"
    py_file.write_text("print('from file')")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_xyz"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file)])
        assert result.exit_code == 0 or mock_browser.called


def test_no_open_flag(tmp_path):
    """--no-open skips browser, prints URL."""
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 1")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_noop"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file), "--no-open"])
        mock_browser.assert_not_called()
        assert "colab.research.google.com" in result.output


def test_no_input_shows_error():
    """No file and no stdin shows error."""
    with patch("colab_push.cli.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        result = runner.invoke(app, [])
        assert result.exit_code != 0 or "No input" in result.output or "error" in result.output.lower()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL

**Step 3: Implement cli.py**

```python
"""CLI entry point using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer
from googleapiclient.discovery import build

from colab_push.auth import get_credentials
from colab_push.notebook import create_notebook, load_ipynb
from colab_push.drive import upload_notebook, find_or_create_folder
from colab_push.colab import get_colab_url, open_in_browser
from colab_push.config import EXIT_USER_ERROR, EXIT_NETWORK_ERROR

app = typer.Typer(
    name="colab-push",
    help="Push code to Google Colab from the command line.",
    add_completion=False,
    no_args_is_help=False,
)


@app.command()
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
        sys.stderr.write("Error: No input provided. Pipe code via stdin or pass a file path.\n")
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
```

Also add `load_ipynb` to `src/colab_push/notebook.py`:

```python
def load_ipynb(content: str, *, accelerator: Optional[str] = None) -> nbformat.NotebookNode:
    """Load an existing .ipynb file, optionally updating metadata."""
    nb = nbformat.reads(content, as_version=4)
    if accelerator:
        if "colab" not in nb.metadata:
            nb.metadata["colab"] = {}
        nb.metadata["colab"]["accelerator"] = accelerator
    return nb
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 5 tests PASS

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS

**Step 6: Commit**

```bash
git add src/colab_push/cli.py src/colab_push/notebook.py tests/test_cli.py
git commit -m "feat: wire up CLI with auth, notebook gen, upload, and browser"
```

---

## Task 9: ipynb Passthrough Tests

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1: Add ipynb passthrough tests**

Append to `tests/test_notebook.py`:
```python
from colab_push.notebook import load_ipynb


def test_load_ipynb_preserves_cells():
    """Loading an ipynb preserves existing cells."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
    nb.cells.append(nbformat.v4.new_code_cell("y = 2"))
    content = nbformat.writes(nb)

    loaded = load_ipynb(content)
    assert len(loaded.cells) == 2
    assert loaded.cells[0].source == "x = 1"


def test_load_ipynb_adds_accelerator():
    """Loading ipynb with accelerator sets colab metadata."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
    content = nbformat.writes(nb)

    loaded = load_ipynb(content, accelerator="GPU")
    assert loaded.metadata["colab"]["accelerator"] == "GPU"


def test_load_ipynb_no_accelerator_leaves_metadata():
    """Loading ipynb without accelerator doesn't add colab metadata."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
    content = nbformat.writes(nb)

    loaded = load_ipynb(content)
    assert "accelerator" not in loaded.metadata.get("colab", {})
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_notebook.py -v`
Expected: all tests PASS

**Step 3: Commit**

```bash
git add tests/test_notebook.py
git commit -m "test: add ipynb passthrough tests"
```

---

## Task 10: Error Handling and Polish

**Files:**
- Modify: `src/colab_push/cli.py`
- Modify: `src/colab_push/auth.py`
- Test: `tests/test_errors.py`

**Step 1: Write error-handling tests**

`tests/test_errors.py`:
```python
"""Tests for error handling edge cases."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from colab_push.cli import app
from colab_push.config import EXIT_USER_ERROR, EXIT_AUTH_ERROR

runner = CliRunner()


def test_nonexistent_file():
    result = runner.invoke(app, ["/tmp/does_not_exist_abc.py"])
    assert result.exit_code == EXIT_USER_ERROR
    assert "not found" in result.output.lower() or "not found" in (result.output + str(result.exception)).lower()


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.py"
    empty.write_text("")
    with (
        patch("colab_push.cli.get_credentials"),
    ):
        result = runner.invoke(app, [str(empty)])
        assert result.exit_code == EXIT_USER_ERROR or "empty" in result.output.lower()
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_errors.py -v`
Expected: PASS (cli.py already handles these cases)

**Step 3: Commit**

```bash
git add tests/test_errors.py
git commit -m "test: add error handling tests"
```

---

## Task 11: Auth Subcommand Test

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: Add auth subcommand test**

Append to `tests/test_cli.py`:
```python
def test_auth_subcommand():
    """colab-push auth triggers re-authentication."""
    with patch("colab_push.cli.get_credentials") as mock_auth:
        result = runner.invoke(app, ["auth"])
        mock_auth.assert_called_once_with(force_reauth=True)
        assert result.exit_code == 0
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_cli.py::test_auth_subcommand -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add auth subcommand test"
```

---

## Task 12: End-to-End Smoke Test

**Files:**
- Create: `tests/test_e2e.py`

**Step 1: Write integration test**

`tests/test_e2e.py`:
```python
"""End-to-end smoke test with mocked Google APIs."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from colab_push.cli import app

runner = CliRunner()


def test_full_flow_file_to_colab(tmp_path):
    """Full flow: .py file → notebook → upload → URL printed."""
    py_file = tmp_path / "experiment.py"
    py_file.write_text("import numpy\n# %%\nprint('cell 2')")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "e2e_file_id"
    }

    with (
        patch("colab_push.cli.get_credentials", return_value=mock_creds),
        patch("colab_push.cli.build", return_value=mock_service),
        patch("colab_push.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file), "--no-open"])
        assert result.exit_code == 0
        assert "colab.research.google.com/drive/e2e_file_id" in result.output

        # Verify upload was called
        mock_service.files.return_value.create.assert_called_once()
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_e2e.py -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add end-to-end smoke test"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 0 | Project scaffolding | - |
| 1 | Config module constants | 4 |
| 2 | Auth (OAuth2 flow) | 5 |
| 3 | Notebook gen (basic) | 7 |
| 4 | Cell splitting edge cases | 4 |
| 5 | Dependency detection | 4 |
| 6 | Colab URL + browser | 2 |
| 7 | Drive upload | 5 |
| 8 | CLI wiring | 5 |
| 9 | ipynb passthrough | 3 |
| 10 | Error handling | 2 |
| 11 | Auth subcommand | 1 |
| 12 | E2E smoke test | 1 |
| **Total** | | **43** |
