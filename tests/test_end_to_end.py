"""End-to-end tests on a fixture repository.

These run the real installed ``repodoctor`` command against the
sample project in ``tests/fixtures/sample-project/`` — a small,
healthy, realistic repository — and against a messy copy of it
built in a temporary folder. They check the exit codes and the
output in text and JSON, strict and non-strict, and that scanning
the fixture changes nothing in it.

The marker text in the messy copy is built by joining pieces so
this test file itself contains no literal marker text — the tool
would otherwise flag its own repository.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from repodoctor import __version__

#: How long any single CLI run may take before the test gives up.
TIMEOUT_SECONDS = 30

#: The project root (the folder holding ``pyproject.toml``).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The healthy sample project shipped with the tests.
FIXTURE_PROJECT = PROJECT_ROOT / "tests" / "fixtures" / "sample-project"

#: The installed console script, when it resolves in the project venv.
CONSOLE_SCRIPT = PROJECT_ROOT / ".venv" / "bin" / "repodoctor"


def _cli_command() -> list[str]:
    """Return the command that runs the real installed CLI."""
    if CONSOLE_SCRIPT.is_file():
        return [str(CONSOLE_SCRIPT)]
    return [sys.executable, "-m", "repodoctor"]


def _run_cli(target: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real CLI once against ``target``."""
    return subprocess.run(
        [*_cli_command(), str(target), *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def _messy_copy(destination: Path) -> Path:
    """Copy the fixture to ``destination`` and break it: no README,
    no ``.gitignore``, no dependency file and no tests, plus a
    Python file that does not compile and a notes file carrying one
    reminder marker."""
    shutil.copytree(FIXTURE_PROJECT, destination)
    (destination / "README.md").unlink()
    (destination / ".gitignore").unlink()
    (destination / "pyproject.toml").unlink()
    shutil.rmtree(destination / "tests")
    (destination / "broken.py").write_text("def broken(\n", encoding="utf-8")
    marker = "TO" + "DO" + ": finish the notes"
    (destination / "notes.txt").write_text(f"Some notes.\n{marker}\n", encoding="utf-8")
    return destination


def test_fixture_text_scan_is_clean() -> None:
    """A text scan of the healthy fixture exits 0 with no findings
    and reports the fixture's real shape."""
    proc = _run_cli(FIXTURE_PROJECT, "--no-color")
    assert proc.returncode == 0
    assert "Files:        5" in proc.stdout
    assert "Python files: 2" in proc.stdout
    assert "README:       yes (README.md)" in proc.stdout
    assert "Gitignore:    yes (.gitignore)" in proc.stdout
    assert "Dependency:   pyproject.toml" in proc.stdout
    assert "Test files:   1" in proc.stdout
    assert "Findings:     none" in proc.stdout
    assert "Found no findings." in proc.stdout
    assert "The repository looks healthy" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_fixture_json_scan_is_clean() -> None:
    """A JSON scan of the healthy fixture exits 0 with an empty
    report listing the fixture's files."""
    proc = _run_cli(FIXTURE_PROJECT, "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["tool"] == "repodoctor"
    assert payload["schema_version"] == 1
    assert payload["tool_version"] == __version__
    assert payload["target"] == FIXTURE_PROJECT.as_posix()
    assert payload["total_files"] == 5
    assert payload["python_files"] == 2
    assert payload["test_files"] == 1
    assert payload["files"] == [
        ".gitignore",
        "README.md",
        "app.py",
        "pyproject.toml",
        "tests/test_app.py",
    ]
    assert payload["findings"] == []
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }
    assert "Traceback" not in proc.stderr


def test_fixture_strict_scans_exit_zero() -> None:
    """Strict scans of the healthy fixture exit 0, text and JSON."""
    text = _run_cli(FIXTURE_PROJECT, "--strict", "--no-color")
    assert text.returncode == 0
    assert "Found no findings." in text.stdout
    assert "Traceback" not in text.stderr
    as_json = _run_cli(FIXTURE_PROJECT, "--strict", "--format", "json")
    assert as_json.returncode == 0
    assert json.loads(as_json.stdout)["summary"]["total"] == 0
    assert "Traceback" not in as_json.stderr


def test_messy_copy_text_scan_reports_everything(
    tmp_path: Path,
) -> None:
    """A text scan of the messy copy groups one error, four
    warnings and one note, and still exits 0 without strict."""
    messy = _messy_copy(tmp_path / "messy-project")
    proc = _run_cli(messy, "--no-color")
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
    assert "Fix the errors first, then look at the rest." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_messy_copy_strict_scans_exit_one(tmp_path: Path) -> None:
    """Strict scans of the messy copy exit 1, text and JSON, with
    the same counts in both formats."""
    messy = _messy_copy(tmp_path / "messy-project")
    text = _run_cli(messy, "--strict", "--no-color")
    assert text.returncode == 1
    assert "Found 1 error, 4 warnings and 1 note." in text.stdout
    assert "Traceback" not in text.stderr
    as_json = _run_cli(messy, "--strict", "--format", "json")
    assert as_json.returncode == 1
    payload = json.loads(as_json.stdout)
    assert payload["summary"] == {
        "total": 6,
        "errors": 1,
        "warnings": 4,
        "notes": 1,
    }
    assert "Traceback" not in as_json.stderr


def test_version_command_prints_the_package_version() -> None:
    """``--version`` prints the version the package reports."""
    proc = subprocess.run(
        [*_cli_command(), "--version"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == f"repodoctor {__version__}"
    assert "Traceback" not in proc.stderr


def test_released_version_is_1_0_0() -> None:
    """The released version is 1.0.0, in the package and on the
    command line: this test locks the release number so a later
    change cannot slip it back by accident."""
    assert __version__ == "1.0.0"
    proc = subprocess.run(
        [*_cli_command(), "--version"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "repodoctor 1.0.0"


def test_scanning_the_fixture_changes_nothing(
    tmp_path: Path,
) -> None:
    """Scanning a copy of the fixture leaves it byte-identical:
    names, contents and modification times, with no new files."""
    messy = _messy_copy(tmp_path / "messy-project")
    before = {
        path.relative_to(messy).as_posix(): (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(messy.rglob("*"))
        if path.is_file()
    }
    proc = _run_cli(messy, "--format", "json")
    assert proc.returncode == 0
    after = {
        path.relative_to(messy).as_posix(): (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(messy.rglob("*"))
        if path.is_file()
    }
    assert after == before
