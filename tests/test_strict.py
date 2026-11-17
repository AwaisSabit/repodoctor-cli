"""Tests for strict mode (``repodoctor --strict``).

In strict mode the scan still prints its full report, but the exit
code changes: 1 when the scan found anything at all, 0 when it found
nothing. Without ``--strict`` findings never change the exit code.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from repodoctor.cli import build_parser, main


def _healthy_folder(tmp_path) -> None:
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


def _folder_with_findings(tmp_path) -> None:
    """Fill ``tmp_path`` with a README and a .py file only.

    The .gitignore, dependency file and tests are all missing, so
    the scan reports those three warnings.
    """
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")


def test_strict_mode_with_findings_exits_one(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict mode exits 1 when the scan found warnings."""
    _folder_with_findings(tmp_path)
    assert main([str(tmp_path), "--strict"]) == 1
    out = capsys.readouterr().out
    # The full report is still printed — only the exit code changes.
    assert "missing-gitignore" in out
    assert "missing-dependency-file" in out
    assert "missing-tests" in out
    assert "Found 3 warnings." in out


def test_strict_mode_with_no_findings_exits_zero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict mode exits 0 when the scan found nothing."""
    _healthy_folder(tmp_path)
    assert main([str(tmp_path), "--strict"]) == 0
    out = capsys.readouterr().out
    assert "Findings:     none" in out
    assert "Found no findings." in out


def test_non_strict_mode_with_findings_still_exits_zero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --strict, findings do not change the exit code."""
    _folder_with_findings(tmp_path)
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "missing-gitignore" in out


def test_strict_mode_json_exits_one_and_prints_valid_json(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict JSON mode exits 1 and still prints a valid report."""
    _folder_with_findings(tmp_path)
    assert main([str(tmp_path), "--strict", "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert [finding["code"] for finding in payload["findings"]] == [
        "missing-gitignore",
        "missing-dependency-file",
        "missing-tests",
    ]
    assert payload["summary"] == {
        "total": 3,
        "errors": 0,
        "warnings": 3,
        "notes": 0,
    }


def test_help_accepts_strict_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` exits 0 and documents the --strict flag."""
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--strict" in out


def test_strict_mode_fails_on_a_warning_only_folder(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A folder with only a warning fails strict mode, not just errors.

    The folder has a .py file, a .gitignore, a dependency file and
    tests, so the only finding is the missing README warning.
    """
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

    assert main([str(tmp_path), "--strict"]) == 1
    out = capsys.readouterr().out
    assert "missing-readme" in out
    assert "Found 1 warning." in out
    # And without strict mode the same folder still exits 0.
    capsys.readouterr()
    assert main([str(tmp_path)]) == 0


def test_strict_mode_exit_code_as_real_process(tmp_path) -> None:
    """``python -m repodoctor --strict`` really exits 1 as a process."""
    _folder_with_findings(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "repodoctor", str(tmp_path), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "missing-gitignore" in proc.stdout
