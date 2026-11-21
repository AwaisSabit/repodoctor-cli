"""Tests for cross-platform paths: the same report on Windows, macOS
and Linux.

Every path RepoDoctor reports must use forward slashes, whatever
platform ran the scan, so text and JSON output are identical
everywhere. A .gitignore written on Windows may list entries with
backslash separators, and those must match the same directories as
the forward-slash form. These tests prove that without needing
Windows: ``PureWindowsPath`` stands in for Windows paths, and a
plain ``Path`` built from a backslash string stands in for a path
that arrived with the other platform's separator.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from repodoctor.checks import _is_ignored_by_gitignore, run_checks
from repodoctor.models import ScanResult
from repodoctor.reporters import format_json, format_summary
from repodoctor.scanner import (
    _gitignore_entries,
    _gitignore_missing_exclusions,
    _is_skipped,
    _path_parts,
    scan_path,
)


def test_path_parts_splits_on_either_separator() -> None:
    """A path is split on both / and backslash, whichever it uses."""
    assert _path_parts(Path("src/__pycache__")) == (
        "src",
        "__pycache__",
    )
    assert _path_parts(Path("src\\__pycache__")) == (
        "src",
        "__pycache__",
    )
    assert _path_parts(PureWindowsPath("src\\__pycache__")) == (
        "src",
        "__pycache__",
    )
    assert _path_parts(PurePosixPath("src/__pycache__")) == (
        "src",
        "__pycache__",
    )


def test_skipped_directory_recognised_with_backslashes() -> None:
    """A skipped directory is recognised even when the path uses
    backslashes, as a Windows-style relative path would."""
    assert _is_skipped(Path("src\\__pycache__")) is True
    assert _is_skipped(Path("src\\__pycache__\\helper.py")) is True
    assert _is_skipped(PureWindowsPath("src\\__pycache__")) is True
    assert _is_skipped(Path(".venv\\lib\\site-packages")) is True
    assert _is_skipped(Path("src/__pycache__")) is True
    assert _is_skipped(Path("src/app.py")) is False
    assert _is_skipped(Path("src\\app.py")) is False


def test_gitignore_entries_stored_with_forward_slashes(
    tmp_path: Path,
) -> None:
    """A Windows-written .gitignore is stored with forward slashes."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        "src\\__pycache__\\\n.venv\\\n",
        encoding="utf-8",
    )

    assert _gitignore_entries(gitignore) == {
        "src/__pycache__/",
        ".venv/",
    }


def test_gitignore_missing_exclusions_accept_backslashes(
    tmp_path: Path,
) -> None:
    """Backslash exclusions in .gitignore count as present."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".venv\\\n__pycache__\\\n", encoding="utf-8")

    assert _gitignore_missing_exclusions(gitignore) == []


def test_gitignore_entry_with_backslash_covers_generated_dir() -> None:
    """A backslash entry names the same generated directory as the
    forward-slash form, with or without a trailing slash."""
    assert (
        _is_ignored_by_gitignore(Path("src/__pycache__"), {"src\\__pycache__\\"})
        is True
    )
    assert _is_ignored_by_gitignore(Path(".venv"), {".venv\\"}) is True
    assert (
        _is_ignored_by_gitignore(
            PureWindowsPath("src\\__pycache__"),
            {"src/__pycache__/"},
        )
        is True
    )
    assert (
        _is_ignored_by_gitignore(Path("src/__pycache__"), {"src\\other__\\"}) is False
    )


def test_scan_honours_backslash_gitignore_entries(
    tmp_path: Path,
) -> None:
    """End to end: a .gitignore written with backslashes covers the
    generated directories it names, so no finding is raised."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text(
        "def test_nothing():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".gitignore").write_text(
        ".venv\\\n__pycache__\\\nsrc\\__pycache__\\\n",
        encoding="utf-8",
    )

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.gitignore_missing_exclusions == []
    assert "generated-dir-not-ignored" not in [finding.code for finding in findings]
    assert findings == []


def _windows_style_result() -> ScanResult:
    """Build a scan result whose paths are Windows-style, as they
    would be after a scan on Windows."""
    result = ScanResult(target=PureWindowsPath("C:\\project"))
    result.total_files = 3
    result.python_files = 2
    result.has_readme = True
    result.readme_path = PureWindowsPath("README.md")
    result.has_gitignore = True
    result.gitignore_path = PureWindowsPath(".gitignore")
    # Only .venv/ is covered, so the generated __pycache__ directory
    # is reported — that is what the message tests check.
    result.gitignore_entries = {".venv/"}
    result.gitignore_missing_exclusions = ["__pycache__/"]
    result.dependency_file = PureWindowsPath("pyproject.toml")
    result.test_files = 1
    result.files = [
        PureWindowsPath("README.md"),
        PureWindowsPath("src\\app.py"),
        PureWindowsPath("src\\broken.py"),
    ]
    result.large_files = [(PureWindowsPath("src\\big.bin"), 2_000_000)]
    result.generated_dirs = [PureWindowsPath("src\\__pycache__")]
    result.syntax_errors = [(PureWindowsPath("src\\broken.py"), 1, "invalid syntax")]
    result.todo_markers = [(PureWindowsPath("notes.txt"), 1)]
    return result


def test_text_report_uses_forward_slashes_for_windows_paths() -> None:
    """The text report shows forward slashes even when the scan ran
    on Windows, and never shows a backslash."""
    result = _windows_style_result()
    run_checks(result)

    report = format_summary(result)

    assert "\\" not in report
    assert "src/broken.py" in report
    assert "src/big.bin" in report
    assert "src/__pycache__" in report
    assert "notes.txt" in report
    assert "C:/project" in report


def test_json_report_uses_forward_slashes_for_windows_paths() -> None:
    """The JSON report shows forward slashes even when the scan ran
    on Windows, and never shows a backslash."""
    result = _windows_style_result()
    run_checks(result)

    raw = format_json(result)
    payload = json.loads(raw)

    # A backslash inside a JSON string value is escaped as "\\", so
    # the raw document must contain no doubled backslash. (A single
    # backslash can still appear in a \u escape for punctuation such
    # as the em dash in a message, which is not a path separator.)
    assert "\\\\" not in raw
    assert payload["target"] == "C:/project"
    assert payload["files"] == [
        "README.md",
        "src/app.py",
        "src/broken.py",
    ]
    assert payload["large_files"][0]["path"] == "src/big.bin"
    assert payload["generated_dirs"] == ["src/__pycache__"]
    assert payload["syntax_errors"][0]["path"] == "src/broken.py"
    assert payload["todo_markers"][0]["path"] == "notes.txt"
    assert all("\\" not in finding["message"] for finding in payload["findings"])


def test_check_messages_use_forward_slashes_for_windows_paths() -> None:
    """Finding messages name files with forward slashes even when
    the scan ran on Windows."""
    result = _windows_style_result()
    findings = run_checks(result)

    messages = [finding.message for finding in findings]
    assert all("\\" not in message for message in messages)
    assert any("src/broken.py" in message for message in messages)
    assert any("src/big.bin" in message for message in messages)
    assert any("src/__pycache__" in message for message in messages)
