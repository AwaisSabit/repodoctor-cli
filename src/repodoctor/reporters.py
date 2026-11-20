"""Output formatters for RepoDoctor results.

Reporters take a :class:`~repodoctor.models.ScanResult` and return a
string; they never print or write files themselves, so the CLI stays
in charge of output and exit codes.
"""

from __future__ import annotations

import json

from . import __version__
from .models import Finding, ScanResult, human_size

#: Version of the JSON report format. Bump it when a field is added,
#: removed or renamed, so CI consumers can tell formats apart.
JSON_SCHEMA_VERSION = 1

#: Severities in the order findings are reported: errors first, then
#: warnings, then informational notes.
SEVERITY_ORDER = ("error", "warning", "info")

#: Heading shown for each severity group in the text report.
SEVERITY_HEADINGS = {
    "error": "Errors",
    "warning": "Warnings",
    "info": "Notes",
}

#: Singular and plural words used in the summary count line.
SEVERITY_COUNT_WORDS = {
    "error": ("error", "errors"),
    "warning": ("warning", "warnings"),
    "info": ("note", "notes"),
}

#: ANSI colour codes for severity labels, used only when the output
#: goes to a terminal (never when piped) and --no-color was not given.
SEVERITY_COLOURS = {"error": "31", "warning": "33", "info": "36"}


def _count_phrase(count: int, singular: str, plural: str) -> str:
    """Return a count with the right singular/plural word."""
    return f"{count} {singular if count == 1 else plural}"


def _summary_line(counts: dict[str, int]) -> str:
    """Return the closing summary line, for example ``"Found 2 errors,
    1 warning and 3 notes."`` Severities with no findings are left
    out; with no findings at all the line says so plainly."""
    parts = []
    for severity in SEVERITY_ORDER:
        count = counts.get(severity, 0)
        if count:
            singular, plural = SEVERITY_COUNT_WORDS[severity]
            parts.append(_count_phrase(count, singular, plural))
    if not parts:
        return "Found no findings."
    if len(parts) == 1:
        return f"Found {parts[0]}."
    return f"Found {', '.join(parts[:-1])} and {parts[-1]}."


def _severity_label(severity: str, use_color: bool) -> str:
    """Return the ``[severity]`` label, coloured when asked for."""
    label = f"[{severity}]"
    if use_color:
        return f"\x1b[{SEVERITY_COLOURS[severity]}m{label}\x1b[0m"
    return label


def format_summary(result: ScanResult, use_color: bool = False) -> str:
    """Return a short human-readable summary of a scan.

    Findings are grouped by severity — errors first, then warnings,
    then informational notes — each group under its own heading, with
    a summary count line at the end. When there are no findings the
    report keeps its friendly ``Findings: none`` message.
    """
    gitignore = (
        f"yes ({result.gitignore_path.as_posix()})"
        if result.has_gitignore
        else "no"
    )
    dependency = (
        result.dependency_file.as_posix() if result.dependency_file else "no"
    )
    large_files = (
        ", ".join(
            f"{path.as_posix()} ({human_size(size)})"
            for path, size in result.large_files
        )
        if result.large_files
        else "none"
    )
    generated_dirs = (
        ", ".join(directory.as_posix() for directory in result.generated_dirs)
        if result.generated_dirs
        else "none"
    )
    syntax_errors = (
        ", ".join(
            f"{path.as_posix()}: line {line}"
            for path, line, _ in result.syntax_errors
        )
        if result.syntax_errors
        else "none"
    )
    todo_markers = (
        ", ".join(
            f"{path.as_posix()} ({count})" for path, count in result.todo_markers
        )
        if result.todo_markers
        else "none"
    )
    lines = [
        f"RepoDoctor — {result.target.as_posix()}",
        f"  Files:        {result.total_files}",
        f"  Python files: {result.python_files}",
        f"  README:       {'yes' + (f' ({result.readme_path.as_posix()})' if result.readme_path else '') if result.has_readme else 'no'}",
        f"  Gitignore:    {gitignore}",
        f"  Dependency:   {dependency}",
        f"  Test files:   {result.test_files}",
        f"  Large files:  {large_files}",
        f"  Generated dirs: {generated_dirs}",
        f"  Syntax errors: {syntax_errors}",
        f"  TODO markers: {todo_markers}",
    ]
    if result.findings:
        lines.append("  Findings:")
        counts: dict[str, int] = {}
        for severity in SEVERITY_ORDER:
            group = [
                finding
                for finding in result.findings
                if finding.severity == severity
            ]
            if not group:
                continue
            counts[severity] = len(group)
            lines.append(f"    {SEVERITY_HEADINGS[severity]} ({len(group)})")
            for finding in group:
                label = _severity_label(finding.severity, use_color)
                lines.append(
                    f"      {label} {finding.code}: {finding.message}"
                )
        lines.append(f"  {_summary_line(counts)}")
    else:
        lines.append("  Findings:     none")
        lines.append(f"  {_summary_line({})}")
    return "\n".join(lines)


def summary_counts(result: ScanResult) -> dict[str, int]:
    """Return the finding counts, by severity, for a scan result.

    The keys are ``"total"``, ``"errors"``, ``"warnings"`` and
    ``"notes"`` (informational findings are called notes, as in the
    text summary line). The numbers here match the text report's
    closing summary line, so both formats always agree.
    """
    counts = {"total": 0, "errors": 0, "warnings": 0, "notes": 0}
    for finding in result.findings:
        counts["total"] += 1
        if finding.severity == "error":
            counts["errors"] += 1
        elif finding.severity == "warning":
            counts["warnings"] += 1
        else:
            counts["notes"] += 1
    return counts


def format_json(result: ScanResult) -> str:
    """Return the scan result as a JSON document (for CI use).

    The document carries every fact the scanner collected — the file
    list, README, gitignore, dependency file, test files, large
    files, generated directories, syntax errors and reminder markers
    — plus the findings and a ``"summary"`` object with the total
    finding count and the counts per severity. ``"schema_version"``
    marks the format (currently 1) and ``"tool_version"`` is the
    RepoDoctor version that produced the report.
    """
    payload = {
        "tool": "repodoctor",
        "schema_version": JSON_SCHEMA_VERSION,
        "tool_version": __version__,
        "target": result.target.as_posix(),
        "total_files": result.total_files,
        "python_files": result.python_files,
        "has_python_files": result.has_python_files,
        "files": [path.as_posix() for path in result.files],
        "has_readme": result.has_readme,
        "readme_path": (
            result.readme_path.as_posix() if result.readme_path else None
        ),
        "has_gitignore": result.has_gitignore,
        "gitignore_path": (
            result.gitignore_path.as_posix()
            if result.gitignore_path
            else None
        ),
        "gitignore_entries": sorted(result.gitignore_entries),
        "gitignore_missing_exclusions": list(
            result.gitignore_missing_exclusions
        ),
        "dependency_file": (
            result.dependency_file.as_posix()
            if result.dependency_file
            else None
        ),
        "test_files": result.test_files,
        "has_tests": result.has_tests,
        "large_files": [
            {
                "path": path.as_posix(),
                "size_bytes": size,
                "size": human_size(size),
            }
            for path, size in result.large_files
        ],
        "generated_dirs": [
            directory.as_posix() for directory in result.generated_dirs
        ],
        "syntax_errors": [
            {
                "path": path.as_posix(),
                "line": line,
                "message": message,
            }
            for path, line, message in result.syntax_errors
        ],
        "todo_markers": [
            {"path": path.as_posix(), "count": count}
            for path, count in result.todo_markers
        ],
        "findings": [
            {
                "code": finding.code,
                "message": finding.message,
                "severity": finding.severity,
                "path": (
                    finding.path.as_posix() if finding.path else None
                ),
            }
            for finding in result.findings
        ],
        "summary": summary_counts(result),
    }
    return json.dumps(payload, indent=2)
