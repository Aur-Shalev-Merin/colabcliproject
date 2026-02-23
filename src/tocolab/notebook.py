"""Notebook generation from source code."""

import re
import sys
from typing import Optional

import nbformat
from nbformat.v4 import new_notebook, new_code_cell

# Common import-name -> pip-package-name mismatches
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
    "git": "GitPython",
}


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

    # Detect dependencies and prepend setup cell
    third_party = detect_third_party_imports(source)
    if third_party:
        install_lines = " ".join(third_party)
        setup_source = (
            "# Auto-detected dependencies\n"
            f"!pip install -q {install_lines}"
        )
        nb.cells.append(new_code_cell(source=setup_source))

    # Create code cells
    cells = _split_cells(source)
    for cell_source in cells:
        nb.cells.append(new_code_cell(source=cell_source))

    return nb


def load_ipynb(
    content: str,
    *,
    accelerator: Optional[str] = None,
) -> nbformat.NotebookNode:
    """Load an existing .ipynb file, optionally updating metadata.

    Args:
        content: Raw JSON string of the .ipynb file.
        accelerator: Optional accelerator type ("GPU" or "TPU").

    Returns:
        A NotebookNode.
    """
    nb = nbformat.reads(content, as_version=4)
    if accelerator:
        if "colab" not in nb.metadata:
            nb.metadata["colab"] = {}
        nb.metadata["colab"]["accelerator"] = accelerator
    return nb


def detect_third_party_imports(source: str) -> list[str]:
    """Detect third-party imports and return pip package names.

    Scans for `import X` and `from X import ...` statements,
    filters out stdlib modules, and maps known mismatches.
    """
    import_pattern = re.compile(r"^(?:import|from)\s+(\w+)", re.MULTILINE)
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


def _split_cells(source: str) -> list[str]:
    """Split source into cells on '# %%' or '# In[' markers.

    If no markers found, return the entire source as one cell.
    """
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
