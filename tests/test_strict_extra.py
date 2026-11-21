"""Extra tests for strict mode (``repodoctor --strict``).

The basic strict-mode behaviour — exit 1 with findings, exit 0
without, in text and JSON — is covered in ``test_strict.py``. These
tests cover the combinations that file does not: strict mode with
only note-level findings, strict mode with only an error, strict
mode in JSON on a clean repo, and the usage-error exit code 2 in
both output modes.
"""

from __future__ import annotations

import json

import pytest

from repodoctor.cli import main


def _healthy_folder(tmp_path) -> None:
    """Fill ``tmp_path`` with a folder that has no findings at all."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n', encoding="utf-8"
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        "def test_nothing():\n    assert True\n", encoding="utf-8"
    )


def _marker_text() -> str:
    """Return one line carrying a reminder marker.

    The marker word is built from pieces so this test file itself
    contains no literal marker text and the tool's own scan stays
    clean.
    """
    return ("TO" + "DO") + ": remember this\n"


def test_strict_json_on_a_clean_repo_exits_zero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict JSON mode exits 0 with a valid report on a clean repo."""
    _healthy_folder(tmp_path)
    assert main([str(tmp_path), "--strict", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }


def test_strict_mode_fails_on_notes_only(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict mode fails even when the only finding is an
    informational note — any finding counts, not just errors and
    warnings."""
    _healthy_folder(tmp_path)
    (tmp_path / "notes.txt").write_text(_marker_text(), encoding="utf-8")
    assert main([str(tmp_path), "--strict"]) == 1
    out = capsys.readouterr().out
    assert "todo-markers" in out
    assert "Found 1 note." in out


def test_strict_json_fails_on_notes_only(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict JSON mode exits 1 on a notes-only folder and still
    prints a valid report with the note counted."""
    _healthy_folder(tmp_path)
    (tmp_path / "notes.txt").write_text(_marker_text(), encoding="utf-8")
    assert main([str(tmp_path), "--strict", "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert [finding["code"] for finding in payload["findings"]] == ["todo-markers"]
    assert payload["summary"] == {
        "total": 1,
        "errors": 0,
        "warnings": 0,
        "notes": 1,
    }


def test_strict_mode_fails_on_an_error_only_folder(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Strict mode fails on a folder whose only finding is a syntax
    error, with everything else healthy."""
    _healthy_folder(tmp_path)
    (tmp_path / "app.py").write_text("def broken(:\n", encoding="utf-8")
    assert main([str(tmp_path), "--strict"]) == 1
    out = capsys.readouterr().out
    assert "syntax-error" in out
    assert "Found 1 error." in out


def test_bad_flag_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unknown flag is a usage error: exit 2 with a usage
    message and no traceback."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--bogus"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments: --bogus" in err
    assert "Traceback" not in err


def test_bad_flag_exits_two_in_json_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The exit code 2 for a bad flag does not depend on the output
    format."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--format", "json", "--bogus"])
    assert excinfo.value.code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_missing_folder_exits_two(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    """Scanning a folder that does not exist is a usage error:
    exit 2, naming the folder, with no traceback and no report."""
    missing = tmp_path / "no-such-folder"
    assert main([str(missing)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no-such-folder" in captured.err
    assert "Traceback" not in captured.err


def test_missing_folder_exits_two_in_json_mode(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The exit code 2 for a missing folder also holds in JSON
    mode, and no half-written JSON is printed."""
    missing = tmp_path / "no-such-folder"
    assert main([str(missing), "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no-such-folder" in captured.err


def test_missing_folder_exits_two_even_in_strict_mode(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A usage error beats strict mode: a missing folder exits 2,
    not 1, even with --strict."""
    missing = tmp_path / "no-such-folder"
    assert main([str(missing), "--strict"]) == 2
    assert "no-such-folder" in capsys.readouterr().err
