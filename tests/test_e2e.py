"""End-to-end smoke test with mocked Google APIs."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from tocolab.cli import app

runner = CliRunner()


def test_full_flow_file_to_colab(tmp_path):
    """Full flow: .py file -> notebook -> upload -> URL printed."""
    py_file = tmp_path / "experiment.py"
    py_file.write_text("import numpy\n# %%\nprint('cell 2')")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "e2e_file_id"
    }

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.open_in_browser") as mock_browser,
    ):
        result = runner.invoke(app, [str(py_file), "--no-open"])
        assert result.exit_code == 0
        assert "colab.research.google.com/drive/e2e_file_id" in result.output
        mock_service.files.return_value.create.assert_called_once()


def test_full_flow_with_gpu(tmp_path):
    """Full flow with --gpu flag."""
    py_file = tmp_path / "train.py"
    py_file.write_text("import torch\nmodel = torch.nn.Linear(10, 1)")

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "gpu_file"
    }

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.open_in_browser"),
    ):
        result = runner.invoke(app, [str(py_file), "--gpu", "--no-open"])
        assert result.exit_code == 0
        assert "colab.research.google.com/drive/gpu_file" in result.output


def test_full_flow_ipynb(tmp_path):
    """Full flow with .ipynb file passthrough."""
    import nbformat

    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("print('existing notebook')"))
    ipynb_file = tmp_path / "existing.ipynb"
    ipynb_file.write_text(nbformat.writes(nb))

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "ipynb_file"
    }

    with (
        patch("tocolab.cli.get_credentials", return_value=mock_creds),
        patch("tocolab.cli.build", return_value=mock_service),
        patch("tocolab.cli.open_in_browser"),
    ):
        result = runner.invoke(app, [str(ipynb_file), "--no-open"])
        assert result.exit_code == 0
        assert "colab.research.google.com/drive/ipynb_file" in result.output
