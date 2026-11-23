"""Tests for the readable text report: the Summary heading, the
plain-English closing line, blank lines between severity groups,
and wrapped long messages.

The JSON report is unchanged by all of this — its structure and its
finding messages stay exactly as they were, so these tests lock
that in too.
"""

from __future__ import annotations

import json
from pathlib import Path

from repodoctor.cli import main
from repodoctor.models import Finding, ScanResult
from repodoctor.reporters import FINDING_LINE_WIDTH, format_json, format_summary


def _result(*findings: Finding) -> ScanResult:
    """Build a scan result carrying exactly the given findings."""
    result = ScanResult(target=Path("example"))
    result.findings = list(findings)
    return result


def _error(message: str = "A Python file has a syntax error.") -> Finding:
    return Finding(code="syntax-error", message=message, severity="error")


def _warning(message: str = "Something worth a look is missing.") -> Finding:
    return Finding(code="missing-readme", message=message, severity="warning")


def _note(message: str = "A file contains a reminder left for later.") -> Finding:
    return Finding(code="todo-markers", message=message, severity="info")


def _marker_note() -> str:
    """Build a reminder-marker line without writing one literally.

    The tool counts a marker word followed by a colon, so this test
    file must not contain one literally, or the tool would flag its
    own test file when scanning its own repository.
    """
    return "TODO" + ": remember to tidy this up\n"


def test_summary_heading_sits_above_the_facts() -> None:
    """The report opens with a Summary heading, then the facts."""
    out = format_summary(_result())
    assert out.index("  Summary") < out.index("  Files:")
    assert out.index("  Files:") < out.index("  Findings:")


def test_clean_report_says_the_repo_looks_healthy() -> None:
    """With no findings the closing line says the repo looks
    healthy and nothing needs fixing."""
    out = format_summary(_result())
    assert "Found no findings." in out
    assert "The repository looks healthy — nothing needs fixing." in out
    # The closing line comes after the summary count line.
    assert out.index("Found no findings.") < out.index("looks healthy")


def test_closing_line_points_at_errors_first() -> None:
    """With findings of every severity the closing line says to
    fix the errors first."""
    out = format_summary(_result(_error(), _warning(), _note()))
    assert "Found 1 error, 1 warning and 1 note." in out
    assert "Fix the errors first, then look at the rest." in out


def test_closing_line_for_errors_only() -> None:
    """With only errors the closing line says that is all that
    needs attention."""
    out = format_summary(_result(_error()))
    assert "Fix the errors — that is all that needs attention." in out


def test_closing_line_for_warnings_only() -> None:
    """With only warnings the closing line starts with them and
    says there are no errors to fix."""
    out = format_summary(_result(_warning()))
    assert "Start with the warnings — that is all that needs attention." in out


def test_closing_line_for_warnings_and_notes() -> None:
    """With warnings and notes the closing line starts with the
    warnings and calls the notes reminders only."""
    out = format_summary(_result(_warning(), _note()))
    assert "Start with the warnings — the notes are reminders only." in out


def test_closing_line_for_notes_only() -> None:
    """With only notes the closing line says nothing is broken."""
    out = format_summary(_result(_note()))
    assert "Nothing is broken — the notes are reminders only." in out


def test_blank_line_between_severity_groups() -> None:
    """A blank line separates each severity group, so the groups
    are easy to scan."""
    out = format_summary(_result(_error(), _warning(), _note()))
    errors_at = out.index("Errors (1)")
    warnings_at = out.index("Warnings (1)")
    notes_at = out.index("Notes (1)")
    assert errors_at < warnings_at < notes_at
    assert "\n\n    Warnings (1)" in out
    assert "\n\n    Notes (1)" in out
    # No blank line before the first group heading.
    assert "Findings:\n    Errors (1)" in out


def test_long_messages_wrap_within_the_line_width() -> None:
    """A long finding message wraps so no line is wider than the
    report width, and the wrapped lines line up under the
    message."""
    message = (
        "No dependency file found (pyproject.toml, requirements.txt, "
        "setup.py or setup.cfg). Add one so others can install this "
        "project's dependencies."
    )
    out = format_summary(_result(_warning(message)))

    lines = out.splitlines()
    assert all(len(line) <= FINDING_LINE_WIDTH for line in lines)
    assert len(lines) > 1  # the message really did wrap

    first = next(line for line in lines if "[warning] missing-readme:" in line)
    # The wrapped lines sit under the message, not under the label:
    # they start where the message starts on the first line.
    indent = " " * first.index("No dependency")
    # Collect only the wrapped lines — stop at the summary count
    # line, so the closing lines are not swept in.
    wrapped: list[str] = []
    for line in lines[lines.index(first) + 1 :]:
        if line.strip().startswith("Found"):
            break
        if line.strip():
            wrapped.append(line)
    assert wrapped
    for line in wrapped:
        assert line.startswith(indent)
    # The message reads whole again once the lines are joined.
    joined = " ".join(line.strip() for line in [first] + wrapped)
    assert message in joined


def test_short_messages_are_not_wrapped() -> None:
    """A short message stays on one line with its label and code."""
    out = format_summary(_result(_error()))
    assert "[error] syntax-error: A Python file has a syntax error." in out


def test_wrapped_output_keeps_colour_on_the_label_only() -> None:
    """Colour still appears only on the severity label, even when
    the message wraps."""
    message = (
        "No dependency file found (pyproject.toml, requirements.txt, "
        "setup.py or setup.cfg). Add one so others can install this "
        "project's dependencies."
    )
    out = format_summary(_result(_warning(message)), use_color=True)
    assert "\x1b[33m[warning]\x1b[0m" in out
    assert all(
        len(line.replace("\x1b[33m", "").replace("\x1b[0m", "")) <= FINDING_LINE_WIDTH
        for line in out.splitlines()
    )


def test_json_output_is_unchanged_by_readability_work() -> None:
    """The JSON report keeps the same structure and the same
    unwrapped finding messages — readability is a text-only
    change."""
    message = (
        "No dependency file found (pyproject.toml, requirements.txt, "
        "setup.py or setup.cfg). Add one so others can install this "
        "project's dependencies."
    )
    result = _result(_error(), _warning(message), _note())
    payload = json.loads(format_json(result))
    assert payload["schema_version"] == 1
    assert payload["summary"] == {
        "total": 3,
        "errors": 1,
        "warnings": 1,
        "notes": 1,
    }
    assert [finding["message"] for finding in payload["findings"]] == [
        "A Python file has a syntax error.",
        message,
        "A file contains a reminder left for later.",
    ]
    # The text report wraps that same message; the JSON does not.
    text_lines = format_summary(result).splitlines()
    assert not any(message in line for line in text_lines)


def test_cli_text_output_shows_the_new_readability_lines(tmp_path, capsys) -> None:
    """The real command on a messy folder shows the Summary
    heading, the grouped findings with blank lines, and the
    closing line — and still exits 0."""
    (tmp_path / "broken.py").write_text("x = \n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(_marker_note(), encoding="utf-8")

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "  Summary" in out
    assert "Errors (1)" in out
    assert "Warnings (4)" in out
    assert "Notes (1)" in out
    assert "\n\n    Warnings (4)" in out
    assert "\n\n    Notes (1)" in out
    assert "Found 1 error, 4 warnings and 1 note." in out
    assert "Fix the errors first, then look at the rest." in out
    assert all(len(line) <= FINDING_LINE_WIDTH for line in out.splitlines())
