"""Tests for notebook generation."""

import nbformat

from colab_push.notebook import create_notebook, load_ipynb, detect_third_party_imports


# --- Basic notebook creation ---

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
    assert nb.metadata["colab"]["name"] == "My Experiment"


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
    assert "accelerator" not in colab_meta


def test_notebook_is_valid():
    """Generated notebook passes nbformat validation."""
    nb = create_notebook("import os\nprint(os.getcwd())")
    nbformat.validate(nb)


# --- Cell splitting ---

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


# --- Dependency detection ---

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
    assert len(nb.cells) == 1
    assert "pip" not in nb.cells[0].source


# --- ipynb passthrough ---

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
