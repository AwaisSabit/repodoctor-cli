"""End-to-end tests for RepoDoctor.

These tests run the real installed ``repodoctor`` command as a
subprocess against temporary directories (and, in one case, against
the tool's own repository), instead of calling the CLI functions
in-process. That proves the installed command, its exit codes and
its output are correct the way a user actually runs them.

The tests are hermetic: every scanned folder is built in ``tmp_path``
(or read from the project root, which is never written to), there is
no network access, and each subprocess run has a timeout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from repodoctor import __version__

#: How long any single CLI run may take before the test gives up.
TIMEOUT_SECONDS = 30

#: The project root (the folder holding ``pyproject.toml``).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The installed console script, when it resolves in the project venv.
CONSOLE_SCRIPT = PROJECT_ROOT / ".venv" / "bin" / "repodoctor"


def _cli_command() -> list[str]:
    """Return the command that runs the real installed CLI.

    Prefer the ``repodoctor`` console script from the project venv;
    fall back to ``python -m repodoctor`` when it is not there, so
    the tests still run on a plain editable install.
    """
    if CONSOLE_SCRIPT.is_file():
        return [str(CONSOLE_SCRIPT)]
    return [sys.executable, "-m", "repodoctor"]


def _run_cli(*args: str, cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the real CLI once and return the finished process."""
    return subprocess.run(
        [*_cli_command(), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def _healthy_folder(tmp_path: Path) -> None:
    """Fill ``tmp_path`` with a folder that has no findings at all."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(
        ".venv/\n__pycache__/\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n', encoding="utf-8"
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        "def test_nothing():\n    assert True\n", encoding="utf-8"
    )


def _messy_folder(tmp_path: Path) -> None:
    """Fill ``tmp_path`` with a folder that has one of each severity.

    No README, no ``.gitignore``, no dependency file and no tests
    (four warnings), a Python file that does not compile (one
    error), and a notes file carrying one reminder marker (one
    informational note). The marker word is built by joining pieces
    so this test file itself contains no literal marker text — the
    tool would otherwise flag its own repository.
    """
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")
    marker = "TO" + "DO" + ": finish the notes"
    (tmp_path / "notes.txt").write_text(
        f"Some notes.\n{marker}\n", encoding="utf-8"
    )


def _codes(payload: dict) -> list[str]:
    """Return the finding codes of a parsed JSON report, in order."""
    return [finding["code"] for finding in payload["findings"]]


def test_help_exits_zero_and_names_the_flags(tmp_path: Path) -> None:
    """``--help`` exits 0 and documents every flag."""
    proc = _run_cli("--help")
    assert proc.returncode == 0
    assert "--format" in proc.stdout
    assert "--strict" in proc.stdout
    assert "--no-color" in proc.stdout
    assert "--version" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_version_exits_zero_and_prints_the_version(tmp_path: Path) -> None:
    """``--version`` exits 0 and prints the package version."""
    proc = _run_cli("--version")
    assert proc.returncode == 0
    assert f"repodoctor {__version__}" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_text_scan_of_healthy_folder_exits_zero(tmp_path: Path) -> None:
    """A text scan of a healthy folder exits 0 with no findings."""
    _healthy_folder(tmp_path)
    proc = _run_cli(str(tmp_path))
    assert proc.returncode == 0
    assert "Findings:     none" in proc.stdout
    assert "Found no findings." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_text_scan_of_messy_folder_reports_all_groups(tmp_path: Path) -> None:
    """A text scan of a messy folder groups findings and counts them.

    Without ``--strict`` the scan still exits 0, even though it
    found one error, four warnings and one note.
    """
    _messy_folder(tmp_path)
    proc = _run_cli(str(tmp_path))
    assert proc.returncode == 0
    assert "Errors (1)" in proc.stdout
    assert "Warnings (4)" in proc.stdout
    assert "Notes (1)" in proc.stdout
    assert "syntax-error" in proc.stdout
    assert "missing-readme" in proc.stdout
    assert "missing-gitignore" in proc.stdout
    assert "missing-dependency-file" in proc.stdout
    assert "missing-tests" in proc.stdout
    assert "todo-markers" in proc.stdout
    assert "Found 1 error, 4 warnings and 1 note." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_strict_scan_of_messy_folder_exits_one(tmp_path: Path) -> None:
    """``--strict`` on a messy folder exits 1 and still prints the report."""
    _messy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--strict")
    assert proc.returncode == 1
    assert "Errors (1)" in proc.stdout
    assert "Found 1 error, 4 warnings and 1 note." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_json_scan_of_messy_folder_matches_text_counts(tmp_path: Path) -> None:
    """JSON output for a messy folder is valid and agrees with text."""
    _messy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["tool"] == "repodoctor"
    assert payload["schema_version"] == 1
    assert payload["tool_version"] == __version__
    # JSON findings keep check order (presence checks first, then the
    # syntax and marker checks); the text report groups the same
    # findings by severity instead.
    assert _codes(payload) == [
        "missing-readme",
        "missing-gitignore",
        "missing-dependency-file",
        "missing-tests",
        "syntax-error",
        "todo-markers",
    ]
    assert payload["summary"] == {
        "total": 6,
        "errors": 1,
        "warnings": 4,
        "notes": 1,
    }
    assert "Traceback" not in proc.stderr


def test_strict_json_scan_of_messy_folder_exits_one(tmp_path: Path) -> None:
    """``--strict --format json`` exits 1 with a valid JSON report."""
    _messy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--strict", "--format", "json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == 1
    assert payload["summary"] == {
        "total": 6,
        "errors": 1,
        "warnings": 4,
        "notes": 1,
    }
    assert "Traceback" not in proc.stderr


def test_json_scan_of_healthy_folder_is_empty(tmp_path: Path) -> None:
    """JSON output for a healthy folder has no findings and zero counts."""
    _healthy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == 1
    assert payload["findings"] == []
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }
    assert "Traceback" not in proc.stderr


def test_missing_folder_exits_two_with_clear_error(tmp_path: Path) -> None:
    """Scanning a folder that does not exist exits 2, no traceback."""
    missing = tmp_path / "does-not-exist"
    proc = _run_cli(str(missing))
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert "Traceback" not in proc.stdout
    assert "does-not-exist" in proc.stderr
    assert "error" in proc.stderr.lower()


def test_unknown_flag_exits_two_with_no_traceback(tmp_path: Path) -> None:
    """An unknown flag exits 2 with a usage message, no traceback."""
    _healthy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--not-a-real-flag")
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert "Traceback" not in proc.stdout
    assert "usage" in proc.stderr.lower()


def test_no_color_flag_produces_no_ansi_codes(tmp_path: Path) -> None:
    """``--no-color`` output has no ANSI escape codes, piped or not."""
    _messy_folder(tmp_path)
    proc = _run_cli(str(tmp_path), "--no-color")
    assert proc.returncode == 0
    assert "\x1b[" not in proc.stdout
    # Piped output is never coloured either, since stdout is not a
    # terminal when captured by subprocess.
    plain = _run_cli(str(tmp_path))
    assert plain.returncode == 0
    assert "\x1b[" not in plain.stdout


def test_scan_is_read_only(tmp_path: Path) -> None:
    """Scanning a folder changes nothing in it — no writes, no new files."""
    _messy_folder(tmp_path)
    before_files = sorted(p for p in tmp_path.rglob("*") if p.is_file())
    before_state = {
        path: (path.read_bytes(), os.stat(path).st_mtime_ns)
        for path in before_files
    }
    proc = _run_cli(str(tmp_path))
    assert proc.returncode == 0
    after_files = sorted(p for p in tmp_path.rglob("*") if p.is_file())
    assert after_files == before_files
    for path in after_files:
        content, mtime_ns = before_state[path]
        assert path.read_bytes() == content
        assert os.stat(path).st_mtime_ns == mtime_ns


def test_scan_of_own_repo_exits_zero_with_no_findings() -> None:
    """The tool is clean on itself: scanning the project root finds nothing.

    This runs the real command from the repository directory, with
    ``.`` as the target, exactly as a user would.
    """
    proc = _run_cli(".", cwd=PROJECT_ROOT)
    assert proc.returncode == 0
    assert "Found no findings." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_scan_from_inside_folder_with_default_target(tmp_path: Path) -> None:
    """Running with no target scans the current directory."""
    _healthy_folder(tmp_path)
    proc = _run_cli(cwd=tmp_path)
    assert proc.returncode == 0
    assert "Found no findings." in proc.stdout
    assert "Traceback" not in proc.stderr
