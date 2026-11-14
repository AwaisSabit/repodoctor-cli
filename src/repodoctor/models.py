"""Data models for RepoDoctor scan results and findings.

These models are deliberately plain dataclasses: the scanner builds
them, the check functions read them, and the reporters render them.
Keeping them separate from I/O makes them easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Severity = Literal["info", "warning", "error"]


def human_size(size_bytes: int) -> str:
    """Return a human-readable size, for example ``"1.2 MB"``."""
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} bytes"


@dataclass(frozen=True)
class Finding:
    """One observation about a scanned repository.

    ``code`` is a stable machine-readable identifier (for example
    ``"missing-readme"``) so CI consumers can filter on it.
    ``severity`` is ``"info"``, ``"warning"`` or ``"error"``.
    """

    code: str
    message: str
    severity: Severity = "warning"
    path: Path | None = None


@dataclass
class ScanResult:
    """Basic, read-only facts collected about a target directory.

    ``files`` holds paths relative to ``target`` so results stay
    portable and never leak absolute paths into JSON output.
    """

    target: Path
    total_files: int = 0
    python_files: int = 0
    has_readme: bool = False
    readme_path: Path | None = None
    has_gitignore: bool = False
    gitignore_path: Path | None = None
    gitignore_missing_exclusions: list[str] = field(default_factory=list)
    gitignore_entries: set[str] = field(default_factory=set)
    dependency_file: Path | None = None
    test_files: int = 0
    large_files: list[tuple[Path, int]] = field(default_factory=list)
    generated_dirs: list[Path] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def has_python_files(self) -> bool:
        """Return True when at least one ``.py`` file was found."""
        return self.python_files > 0

    @property
    def has_tests(self) -> bool:
        """Return True when at least one test file was found."""
        return self.test_files > 0
