"""Basic repository-hygiene checks run on a :class:`ScanResult`.

Each check returns a :class:`~repodoctor.models.Finding` (or nothing).
Checks are pure functions of the scan result, so they are easy to unit
test without touching the filesystem. They are heuristics, not security
findings: a warning means "worth a look", not "definitely broken".
"""

from __future__ import annotations

from pathlib import Path

from .models import Finding, ScanResult, human_size


def _is_ignored_by_gitignore(directory: Path, gitignore_entries: set[str]) -> bool:
    """Return True when a .gitignore entry names ``directory``.

    An entry counts with or without a trailing slash, and it may name
    the directory itself (``__pycache__/``) or its full relative path
    (``src/__pycache__/``). Entries written with backslash separators
    (a Windows-written ``.gitignore`` listing ``src\\__pycache__``)
    count the same as the forward-slash form, and a directory given
    as a Windows-style path matches too: both sides are compared in
    forward-slash form.
    """
    names = {directory.name, directory.as_posix()}
    return any(
        entry.replace("\\", "/").rstrip("/") in names for entry in gitignore_entries
    )


def check_readme(result: ScanResult) -> Finding | None:
    """Warn when the repository has no README file."""
    if result.has_readme:
        return None
    return Finding(
        code="missing-readme",
        message=(
            "No README file found. Add a README.md describing what this project does."
        ),
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
                f"The .gitignore file is missing common Python exclusions: {missing}."
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
                    f"File {path.as_posix()} is large ({human_size(size)}). "
                    f"Large files slow down clones and do not belong in "
                    f"version control — consider splitting it or storing "
                    f"it outside the repository."
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
                f"Generated directory {directory.as_posix()} exists but "
                f"is not listed in .gitignore. Add {directory.name}/ to "
                f".gitignore so it is not committed by accident."
            )
        else:
            message = (
                f"Generated directory {directory.as_posix()} exists and "
                f"there is no .gitignore file. Add {directory.name}/ to "
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


def check_syntax_errors(result: ScanResult) -> list[Finding]:
    """Report each Python file that does not compile, as an error.

    The scanner only compiles the source; it never runs it, so a
    file with broken (or dangerous) code is still safe to scan.
    The finding names the file and the line number of the error.
    """
    findings = []
    for path, line, message in result.syntax_errors:
        findings.append(
            Finding(
                code="syntax-error",
                message=(
                    f"File {path.as_posix()} has a Python syntax error "
                    f"on line {line}: {message}."
                ),
                severity="error",
                path=path,
            )
        )
    return findings


def check_todo_markers(result: ScanResult) -> list[Finding]:
    """Report reminder markers in text files, as information only.

    One informational finding per file, with the file and the number
    of markers found. Markers are notes left for later work, not
    problems, so they are never warnings or errors.
    """
    findings = []
    for path, count in result.todo_markers:
        word = "marker" if count == 1 else "markers"
        findings.append(
            Finding(
                code="todo-markers",
                message=(
                    f"File {path.as_posix()} contains {count} reminder "
                    f"{word} (TODO, FIXME, XXX or HACK). This is "
                    f"information only, not a problem."
                ),
                severity="info",
                path=path,
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
    check_syntax_errors,
    check_todo_markers,
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
