"""Basic repository-hygiene checks run on a :class:`ScanResult`.

Each check returns a :class:`~repodoctor.models.Finding` (or nothing).
Checks are pure functions of the scan result, so they are easy to unit
test without touching the filesystem. They are heuristics, not security
findings: a warning means "worth a look", not "definitely broken".
"""

from __future__ import annotations

from .models import Finding, ScanResult


def check_readme(result: ScanResult) -> Finding | None:
    """Warn when the repository has no README file."""
    if result.has_readme:
        return None
    return Finding(
        code="missing-readme",
        message="No README file found. Add a README.md describing what this project does.",
        severity="warning",
    )


def check_python_files(result: ScanResult) -> Finding | None:
    """Note (info level) when no Python files were found at all."""
    if result.has_python_files:
        return None
    return Finding(
        code="no-python-files",
        message="No Python (.py) files found in the scanned directory.",
        severity="info",
    )


def check_empty(result: ScanResult) -> Finding | None:
    """Warn when the scanned directory contains no files at all."""
    if result.total_files > 0:
        return None
    return Finding(
        code="empty-directory",
        message="The scanned directory contains no files.",
        severity="warning",
    )


#: Day 1 check set, in the order findings are reported.
CHECKS = (check_empty, check_readme, check_python_files)


def run_checks(result: ScanResult) -> list[Finding]:
    """Run all Day 1 checks against ``result`` and return findings."""
    findings: list[Finding] = []
    for check in CHECKS:
        finding = check(result)
        if finding is not None:
            findings.append(finding)
    result.findings = findings
    return findings
