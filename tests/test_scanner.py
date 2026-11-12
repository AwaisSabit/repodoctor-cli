"""Tests for the read-only scanner and the basic checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from repodoctor.checks import run_checks
from repodoctor.scanner import scan_path


def test_scanner_counts_files_and_python_files(tmp_path: Path) -> None:
    """A folder with 2 .py files, 1 .txt and a README is counted correctly."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "utils.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("hello\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.total_files == 4
    assert result.python_files == 2
    assert result.has_readme is True
    assert result.readme_path == Path("README.md")


def test_scanner_reports_missing_readme(tmp_path: Path) -> None:
    """A folder with only a .py file reports no README and a finding."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.has_readme is False
    assert result.readme_path is None
    assert [finding.code for finding in findings] == ["missing-readme"]


def test_scanner_empty_directory(tmp_path: Path) -> None:
    """An empty folder is scanned without error and flagged as empty."""
    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.total_files == 0
    assert result.python_files == 0
    codes = {finding.code for finding in findings}
    assert "empty-directory" in codes
    assert "missing-readme" in codes


def test_scanner_skips_git_and_venv_directories(tmp_path: Path) -> None:
    """Files under .git / .venv / __pycache__ are not counted."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.total_files == 1
    assert result.python_files == 1


def test_scanner_ignores_pytest_cache_and_nested_readme(tmp_path: Path) -> None:
    """``.pytest_cache`` is skipped, and a nested README does not count."""
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
    (tmp_path / ".pytest_cache" / "v").mkdir()
    (tmp_path / ".pytest_cache" / "v" / "cache").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("docs\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.total_files == 2
    assert result.has_readme is False
    assert result.readme_path is None


def test_scanner_does_not_modify_target(tmp_path: Path) -> None:
    """Scanning is read-only: file contents and mtimes are unchanged."""
    target_file = tmp_path / "app.py"
    target_file.write_text("x = 1\n", encoding="utf-8")
    before = target_file.read_bytes()
    mtime_before = target_file.stat().st_mtime

    scan_path(tmp_path)

    assert target_file.read_bytes() == before
    assert target_file.stat().st_mtime == mtime_before


def test_scanner_missing_target_raises(tmp_path: Path) -> None:
    """Scanning a non-existent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        scan_path(tmp_path / "nope")


def test_scanner_file_target_raises(tmp_path: Path) -> None:
    """Scanning a file (not a directory) raises NotADirectoryError."""
    target_file = tmp_path / "app.py"
    target_file.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        scan_path(target_file)
