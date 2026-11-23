"""Self-scan tests: the installed command on its own repository.

These run the real installed ``repodoctor`` command against the
project root in every output mode — text and JSON, strict and
non-strict — and check the exit codes, the output, and that the
report leaks nothing: every path in the JSON report is relative to
the scanned folder, and the absolute path of the repository appears
exactly once, as the ``target`` the user asked to scan.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from repodoctor import __version__

#: How long any single CLI run may take before the test gives up.
TIMEOUT_SECONDS = 30

#: The project root (the folder holding ``pyproject.toml``).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The installed console script, when it resolves in the project venv.
CONSOLE_SCRIPT = PROJECT_ROOT / ".venv" / "bin" / "repodoctor"


def _cli_command() -> list[str]:
    """Return the command that runs the real installed CLI."""
    if CONSOLE_SCRIPT.is_file():
        return [str(CONSOLE_SCRIPT)]
    return [sys.executable, "-m", "repodoctor"]


def _run_cli(
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run the real CLI once against the project root."""
    return subprocess.run(
        [*_cli_command(), *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def test_self_scan_text_non_strict_exits_zero() -> None:
    """Text scan of the own repository exits 0 with no findings."""
    proc = _run_cli(".", "--no-color")
    assert proc.returncode == 0
    assert "Found no findings." in proc.stdout
    assert "The repository looks healthy" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_self_scan_text_strict_exits_zero() -> None:
    """Strict text scan of the own repository exits 0: it is clean."""
    proc = _run_cli(".", "--strict", "--no-color")
    assert proc.returncode == 0
    assert "Found no findings." in proc.stdout
    assert "Traceback" not in proc.stderr


def test_self_scan_json_non_strict_is_clean() -> None:
    """JSON scan of the own repository exits 0 with an empty report."""
    proc = _run_cli(".", "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["tool"] == "repodoctor"
    assert payload["schema_version"] == 1
    assert payload["tool_version"] == __version__
    assert payload["findings"] == []
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }
    assert "Traceback" not in proc.stderr


def test_self_scan_json_strict_exits_zero() -> None:
    """Strict JSON scan of the own repository exits 0 with valid JSON."""
    proc = _run_cli(".", "--strict", "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["findings"] == []
    assert payload["summary"]["total"] == 0
    assert "Traceback" not in proc.stderr


def test_self_scan_json_paths_are_all_relative() -> None:
    """Every path in the JSON report is relative to the target.

    Only ``target`` itself is absolute — it is the folder the user
    asked to scan. File lists, README, gitignore, dependency file
    and every finding path must be relative, so a report can be
    shared without leaking where the repository lives.
    """
    proc = _run_cli(".", "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert Path(payload["target"]).is_absolute()
    for path in payload["files"]:
        assert not path.startswith("/"), f"absolute path leaked: {path}"
    for key in ("readme_path", "gitignore_path", "dependency_file"):
        value = payload[key]
        if value is not None:
            assert not value.startswith("/"), f"absolute path leaked: {value}"
    for entry in payload["large_files"]:
        assert not entry["path"].startswith("/")
    for path in payload["generated_dirs"]:
        assert not path.startswith("/")


def test_self_scan_json_names_the_target_exactly_once() -> None:
    """The absolute repository path appears once in the JSON output,
    as ``target`` — nowhere else, so no other field leaks it."""
    proc = _run_cli(".", "--format", "json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    serialized = json.dumps(payload)
    assert serialized.count(str(PROJECT_ROOT)) == 1
    assert payload["target"] == PROJECT_ROOT.as_posix()
