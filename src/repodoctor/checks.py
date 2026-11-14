"""Basic repository-hygiene checks run on a :class:`ScanResult`.

Each check returns a :class:`~repodoctor.models.Finding` (or nothing).
Checks are pure functions of the scan result, so they are easy to unit
test without touching the filesystem. They are heuristics, not security
findings: a warning means "worth a look", not "definitely broken".
"""

from __future__ import annotations

from pathlib import Path

from .models import Finding, ScanResult, human_size


def _is_ignored_by_gitignore(
    directory: Path, gitignore_entries: set[str]
) -> bool:
    """Return True when a .gitignore entry names ``directory``.

    An entry counts with or without a trailing slash, and it may name
    the directory itself (``__pycache__/``) or its full relative path
    (``src/__pycache__/``).
    """
    names = {directory.name, str(directory)}
    return any(entry.rstrip("/") in names for entry in gitignore_entries)


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


def check_gitignore(result: ScanResult) -> Finding | None:
    """Warn when there is no .gitignore, or it misses common exclusions."""
    if not result.has_gitignore:
        return Finding(
            code="missing-gitignore",
            message=(
                "No .gitignore file found. Add one so virtual environments "
                "and cache files are not committed by accident."
            ),
            severity="warning",
        )
    if result.gitignore_missing_exclusions:
        missing = ", ".join(result.gitignore_missing_exclusions)
        return Finding(
            code="gitignore-missing-exclusions",
            message=(
                f"The .gitignore file is missing common Python exclusions: "
                f"{missing}."
            ),
            severity="warning",
        )
    return None


def check_dependency_file(result: ScanResult) -> Finding | None:
    """Warn when no dependency/packaging file exists."""
    if result.dependency_file is not None:
        return None
    return Finding(
        code="missing-dependency-file",
        message=(
            "No dependency file found (pyproject.toml, requirements.txt, "
            "setup.py or setup.cfg). Add one so others can install this "
            "project's dependencies."
        ),
        severity="warning",
    )


def check_tests(result: ScanResult) -> Finding | None:
    """Warn when no tests directory or test files exist."""
    if result.has_tests:
        return None
    return Finding(
        code="missing-tests",
        message=(
            "No tests directory or test files found. Add a tests/ folder "
            "with at least one test so changes can be checked."
        ),
        severity="warning",
    )


def check_large_files(result: ScanResult) -> list[Finding]:
    """Warn once for each file larger than the scanner's threshold."""
    findings = []
    for path, size in result.large_files:
        findings.append(
            Finding(
                code="large-file",
                message=(
                    f"File {path} is large ({human_size(size)}). Large "
                    f"files slow down clones and do not belong in version "
                    f"control — consider splitting it or storing it "
                    f"outside the repository."
                ),
                severity="warning",
                path=path,
            )
        )
    return findings


def check_generated_dirs(result: ScanResult) -> list[Finding]:
    """Warn for each generated directory not covered by .gitignore.

    A directory counts as covered when a .gitignore entry names it,
    with or without a trailing slash. When there is no .gitignore at
    all, every generated directory found is a warning.
    """
    findings = []
    for directory in result.generated_dirs:
        if _is_ignored_by_gitignore(directory, result.gitignore_entries):
            continue
        if result.has_gitignore:
            message = (
                f"Generated directory {directory} exists but is not "
                f"listed in .gitignore. Add {directory.name}/ to "
                f".gitignore so it is not committed by accident."
            )
        else:
            message = (
                f"Generated directory {directory} exists and there is "
                f"no .gitignore file. Add {directory.name}/ to "
                f".gitignore so it is not committed by accident."
            )
        findings.append(
            Finding(
                code="generated-dir-not-ignored",
                message=message,
                severity="warning",
                path=directory,
            )
        )
    return findings


#: The check set, in the order findings are reported.
CHECKS = (
    check_empty,
    check_readme,
    check_python_files,
    check_gitignore,
    check_dependency_file,
    check_tests,
    check_large_files,
    check_generated_dirs,
)


def run_checks(result: ScanResult) -> list[Finding]:
    """Run all checks against ``result`` and return findings."""
    findings: list[Finding] = []
    for check in CHECKS:
        outcome = check(result)
        if outcome is None:
            continue
        if isinstance(outcome, list):
            findings.extend(outcome)
        else:
            findings.append(outcome)
    result.findings = findings
    return findings
