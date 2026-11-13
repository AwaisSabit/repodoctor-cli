"""Tests for the RepoDoctor CLI (``repodoctor`` / ``python -m repodoctor``)."""

from __future__ import annotations

import subprocess
import sys

import pytest

from repodoctor import __version__
from repodoctor.cli import build_parser, main


def test_help_lists_target_and_format(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` exits 0 and documents the target and --format options."""
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "target" in out
    assert "--format" in out


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--version`` exits 0 and prints the package version."""
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--version"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_main_scans_directory_and_exits_zero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``main()`` on a folder with a README and a .py file exits 0."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "Python files: 1" in out
    assert "README:       yes" in out
    # A README and a .py file only: gitignore, dependency file and
    # tests are all missing, so those findings are reported.
    assert "missing-gitignore" in out
    assert "missing-dependency-file" in out
    assert "missing-tests" in out
    assert "Gitignore:    no" in out
    assert "Dependency:   no" in out
    assert "Test files:   0" in out


def test_main_missing_target_exits_nonzero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing target is a scan failure: exit code 2 and an error message."""
    missing = tmp_path / "does-not-exist"
    assert main([str(missing)]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_main_json_output_is_valid_json(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--format json`` prints a JSON document with the scan facts."""
    import json

    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    assert main([str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["has_readme"] is True
    assert payload["total_files"] == 1
    # A README-only folder has no .py files, no .gitignore, no
    # dependency file and no tests, so all four findings are correct.
    assert [finding["code"] for finding in payload["findings"]] == [
        "no-python-files",
        "missing-gitignore",
        "missing-dependency-file",
        "missing-tests",
    ]
    assert payload["has_gitignore"] is False
    assert payload["dependency_file"] is None
    assert payload["test_files"] == 0


def test_module_entry_point_help() -> None:
    """``python -m repodoctor --help`` works as a real subprocess."""
    proc = subprocess.run(
        [sys.executable, "-m", "repodoctor", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "repodoctor" in proc.stdout
