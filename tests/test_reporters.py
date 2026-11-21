"""Tests for the RepoDoctor text and JSON reporters.

The text reporter groups findings by severity (errors, then warnings,
then informational notes) and ends with a summary count line. The
JSON reporter keeps the same findings with the same severities.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repodoctor import __version__
from repodoctor.cli import main
from repodoctor.models import Finding, ScanResult
from repodoctor.reporters import (
    JSON_SCHEMA_VERSION,
    format_json,
    format_summary,
    summary_counts,
)


def _result(*findings: Finding) -> ScanResult:
    """Build a scan result carrying exactly the given findings."""
    result = ScanResult(target=Path("example"))
    result.findings = list(findings)
    return result


def _error(code: str = "syntax-error") -> Finding:
    return Finding(
        code=code,
        message="A Python file has a syntax error.",
        severity="error",
    )


def _warning(code: str = "missing-readme") -> Finding:
    return Finding(
        code=code,
        message="Something worth a look is missing.",
        severity="warning",
    )


def _note(code: str = "todo-markers") -> Finding:
    return Finding(
        code=code,
        message="A file contains a reminder left for later.",
        severity="info",
    )


def _marker_note() -> str:
    """Build a reminder-marker line without writing one literally.

    The tool counts a marker word followed by a colon, so this test
    file must not contain one literally, or the tool would flag its
    own test file when scanning its own repository.
    """
    return "TODO" + ": remember to tidy this up\n"


def test_findings_grouped_errors_then_warnings_then_notes() -> None:
    """Findings print errors first, then warnings, then notes,
    whatever order they arrived in."""
    result = _result(
        _note(),
        _warning(),
        _error(),
        _warning("missing-gitignore"),
        _error("syntax-error-2"),
        _note("todo-markers-2"),
        _note("todo-markers-3"),
    )
    out = format_summary(result)

    errors_at = out.index("Errors (2)")
    warnings_at = out.index("Warnings (2)")
    notes_at = out.index("Notes (3)")
    assert errors_at < warnings_at < notes_at

    # Each finding sits under its own group heading.
    assert "syntax-error:" in out[errors_at:warnings_at]
    assert "syntax-error-2:" in out[errors_at:warnings_at]
    assert "missing-readme:" in out[warnings_at:notes_at]
    assert "missing-gitignore:" in out[warnings_at:notes_at]
    assert "todo-markers:" in out[notes_at:]
    assert "todo-markers-2:" in out[notes_at:]
    assert "todo-markers-3:" in out[notes_at:]

    # Each finding still carries its severity label.
    assert "[error] syntax-error:" in out
    assert "[warning] missing-readme:" in out
    assert "[info] todo-markers:" in out


def test_summary_line_mixed_counts() -> None:
    """The summary line counts each severity in a mixed set."""
    result = _result(
        _error(),
        _error("syntax-error-2"),
        _warning(),
        _note(),
        _note("todo-markers-2"),
        _note("todo-markers-3"),
    )
    assert "Found 2 errors, 1 warning and 3 notes." in format_summary(result)


@pytest.mark.parametrize(
    "findings, expected",
    [
        ([_error()], "Found 1 error."),
        ([_warning()], "Found 1 warning."),
        ([_note()], "Found 1 note."),
        ([_error(), _error("syntax-error-2")], "Found 2 errors."),
        (
            [_warning(), _warning("missing-gitignore"), _note()],
            "Found 2 warnings and 1 note.",
        ),
        (
            [_error(), _note()],
            "Found 1 error and 1 note.",
        ),
    ],
)
def test_summary_line_singular_and_plural(
    findings: list[Finding], expected: str
) -> None:
    """The summary line uses singular words for one finding and
    plural words for several."""
    assert expected in format_summary(_result(*findings))


def test_zero_findings_keeps_no_findings_message() -> None:
    """With no findings the report keeps its friendly message and
    shows no severity groups."""
    out = format_summary(_result())
    assert "  Findings:     none" in out
    assert "Found no findings." in out
    assert "Errors (" not in out
    assert "Warnings (" not in out
    assert "Notes (" not in out


def test_empty_severity_group_is_not_shown() -> None:
    """A severity with no findings gets no group heading."""
    out = format_summary(_result(_warning(), _warning("missing-gitignore")))
    assert "Warnings (2)" in out
    assert "Errors (" not in out
    assert "Notes (" not in out
    assert "Found 2 warnings." in out


def test_summary_facts_stay_above_findings() -> None:
    """The facts section still comes before the grouped findings."""
    out = format_summary(_result(_error(), _warning(), _note()))
    assert out.index("Files:") < out.index("Findings:")
    assert out.index("Findings:") < out.index("Errors (1)")
    assert "README:" in out


def test_json_carries_same_findings_and_severities() -> None:
    """The JSON output still carries the same findings, in the same
    order, with the same severities as the text grouping."""
    findings = [
        _note(),
        _warning(),
        _error(),
        _warning("missing-gitignore"),
    ]
    result = _result(*findings)

    payload = json.loads(format_json(result))
    assert [
        (finding["code"], finding["severity"]) for finding in payload["findings"]
    ] == [
        ("todo-markers", "info"),
        ("missing-readme", "warning"),
        ("syntax-error", "error"),
        ("missing-gitignore", "warning"),
    ]

    # The text report groups those same findings, so the codes and
    # severities agree between the two formats.
    text = format_summary(result)
    for finding in findings:
        assert f"[{finding.severity}] {finding.code}:" in text


def test_colour_labels_only_when_requested() -> None:
    """Colour appears only when asked for, and only on the severity
    label."""
    result = _result(_error(), _warning(), _note())

    plain = format_summary(result)
    assert "\x1b[" not in plain

    coloured = format_summary(result, use_color=True)
    assert "\x1b[31m[error]\x1b[0m" in coloured
    assert "\x1b[33m[warning]\x1b[0m" in coloured
    assert "\x1b[36m[info]\x1b[0m" in coloured
    # Headings and messages stay uncoloured.
    assert "Errors (1)" in coloured
    assert "A Python file has a syntax error." in coloured


def test_cli_text_output_groups_findings(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI text output on a folder with findings shows the
    groups and the summary count, and still exits 0."""
    (tmp_path / "broken.py").write_text("x = \n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(_marker_note(), encoding="utf-8")

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert out.index("Errors (1)") < out.index("Warnings (4)")
    assert out.index("Warnings (4)") < out.index("Notes (1)")
    assert "[error] syntax-error:" in out
    assert "[warning] missing-readme:" in out
    assert "[info] todo-markers:" in out
    assert "Found 1 error, 4 warnings and 1 note." in out
    # Piped (captured) output is never coloured.
    assert "\x1b[" not in out


def test_cli_no_color_flag_is_accepted(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--no-color`` is accepted and keeps the output plain."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    assert main([str(tmp_path), "--no-color"]) == 0
    assert "\x1b[" not in capsys.readouterr().out


def test_json_carries_schema_and_tool_version() -> None:
    """The JSON report names the tool, the format version and the
    tool version, so consumers can tell formats apart later."""
    payload = json.loads(format_json(_result()))
    assert payload["tool"] == "repodoctor"
    assert payload["schema_version"] == 1
    assert payload["schema_version"] == JSON_SCHEMA_VERSION
    assert payload["tool_version"] == __version__


def test_json_summary_counts_match_text_summary() -> None:
    """The JSON summary object counts the total and each severity,
    and its numbers agree with the text summary line."""
    result = _result(
        _error(),
        _error("syntax-error-2"),
        _warning(),
        _note(),
        _note("todo-markers-2"),
        _note("todo-markers-3"),
    )
    payload = json.loads(format_json(result))
    assert payload["summary"] == {
        "total": 6,
        "errors": 2,
        "warnings": 1,
        "notes": 3,
    }
    assert summary_counts(result) == payload["summary"]
    assert "Found 2 errors, 1 warning and 3 notes." in format_summary(result)


def test_json_summary_is_zero_when_no_findings() -> None:
    """With no findings the JSON summary is all zeros."""
    payload = json.loads(format_json(_result()))
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }
    assert "Found no findings." in format_summary(_result())


def test_json_carries_every_scan_fact() -> None:
    """Every fact the scanner collects appears in the JSON output,
    in a consistent shape, including facts the text report shows
    only as counts."""
    result = ScanResult(target=Path("example"))
    result.total_files = 4
    result.python_files = 2
    result.files = [
        Path("README.md"),
        Path("app.py"),
        Path("tests/test_app.py"),
        Path(".gitignore"),
    ]
    result.has_readme = True
    result.readme_path = Path("README.md")
    result.has_gitignore = True
    result.gitignore_path = Path(".gitignore")
    result.gitignore_entries = {"__pycache__/", ".venv/"}
    result.gitignore_missing_exclusions = []
    result.dependency_file = Path("pyproject.toml")
    result.test_files = 1
    result.large_files = [(Path("data.bin"), 2_000_000)]
    result.generated_dirs = [Path("__pycache__")]
    result.syntax_errors = [
        (Path("broken.py"), 3, "invalid syntax"),
    ]
    result.todo_markers = [(Path("notes.txt"), 2)]
    result.findings = [_error(), _warning()]

    payload = json.loads(format_json(result))
    assert payload["total_files"] == 4
    assert payload["python_files"] == 2
    assert payload["has_python_files"] is True
    assert payload["files"] == [
        "README.md",
        "app.py",
        "tests/test_app.py",
        ".gitignore",
    ]
    assert payload["has_readme"] is True
    assert payload["readme_path"] == "README.md"
    assert payload["has_gitignore"] is True
    assert payload["gitignore_path"] == ".gitignore"
    assert payload["gitignore_entries"] == [".venv/", "__pycache__/"]
    assert payload["gitignore_missing_exclusions"] == []
    assert payload["dependency_file"] == "pyproject.toml"
    assert payload["test_files"] == 1
    assert payload["has_tests"] is True
    assert payload["large_files"] == [
        {"path": "data.bin", "size_bytes": 2_000_000, "size": "1.9 MB"}
    ]
    assert payload["generated_dirs"] == ["__pycache__"]
    assert payload["syntax_errors"] == [
        {"path": "broken.py", "line": 3, "message": "invalid syntax"}
    ]
    assert payload["todo_markers"] == [{"path": "notes.txt", "count": 2}]
    assert payload["summary"] == {
        "total": 2,
        "errors": 1,
        "warnings": 1,
        "notes": 0,
    }


def test_cli_json_output_has_summary_and_version(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI JSON output on a real folder is valid JSON with the
    version fields and a summary that agrees with the text output."""
    (tmp_path / "broken.py").write_text("x = \n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(_marker_note(), encoding="utf-8")

    assert main([str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["tool_version"] == __version__
    assert payload["summary"] == {
        "total": 6,
        "errors": 1,
        "warnings": 4,
        "notes": 1,
    }
    assert payload["total_files"] == 2
    assert payload["files"] == ["broken.py", "notes.txt"]
    assert payload["syntax_errors"][0]["path"] == "broken.py"
    assert payload["todo_markers"] == [{"path": "notes.txt", "count": 1}]

    # The same folder in text form ends with the same counts.
    assert main([str(tmp_path)]) == 0
    assert "Found 1 error, 4 warnings and 1 note." in capsys.readouterr().out
