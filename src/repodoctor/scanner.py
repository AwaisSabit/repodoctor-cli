"""Read-only scanner for a target directory.

The scanner never writes to, deletes, or executes anything inside the
target. It walks the tree with :meth:`pathlib.Path.rglob`, skipping
version-control and generated directories, and collects basic facts:
how many files exist, how many are Python files, and whether a README
is present.
"""

from __future__ import annotations

from pathlib import Path

from .models import ScanResult

#: Directories that are generated, cached, or version-control metadata.
#: Skipping them keeps counts meaningful and avoids scanning a virtual
#: environment or a ``.git`` directory.
SKIPPED_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".tox", ".mypy_cache"}
)

#: File names accepted as a README (case-insensitive).
README_NAMES = frozenset({"readme.md", "readme.rst", "readme.txt", "readme"})

#: Dependency/packaging files, in the order they are preferred when
#: more than one is present. Only files at the repository root count.
DEPENDENCY_FILES = (
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
)

#: Exclusions a Python project's .gitignore should normally contain.
#: An entry counts as present with or without a trailing slash.
REQUIRED_GITIGNORE_EXCLUSIONS = (".venv/", "__pycache__/")


def _gitignore_missing_exclusions(gitignore_path: Path) -> list[str]:
    """Return the required exclusions missing from ``gitignore_path``.

    Reading the file is a read-only operation; a file that cannot be
    read as text is treated as if it had no exclusions at all.
    """
    try:
        text = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return list(REQUIRED_GITIGNORE_EXCLUSIONS)
    entries = {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    missing = []
    for exclusion in REQUIRED_GITIGNORE_EXCLUSIONS:
        if exclusion not in entries and exclusion.rstrip("/") not in entries:
            missing.append(exclusion)
    return missing


def _is_skipped(path: Path) -> bool:
    """Return True if any part of ``path`` is a skipped directory."""
    return any(part in SKIPPED_DIRS for part in path.parts)


def scan_path(target: str | Path) -> ScanResult:
    """Scan ``target`` read-only and return a :class:`ScanResult`.

    Args:
        target: Directory to scan. It must exist and be a directory.

    Raises:
        FileNotFoundError: If ``target`` does not exist.
        NotADirectoryError: If ``target`` is not a directory.
    """
    target_path = Path(target)
    if not target_path.exists():
        raise FileNotFoundError(f"target does not exist: {target_path}")
    if not target_path.is_dir():
        raise NotADirectoryError(f"target is not a directory: {target_path}")

    result = ScanResult(target=target_path.resolve())
    for path in sorted(target_path.rglob("*")):
        if _is_skipped(path.relative_to(target_path)):
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(target_path)
        result.files.append(relative)
        result.total_files += 1
        if path.suffix == ".py":
            result.python_files += 1
        # A test file is a .py file inside a tests/ or test/ folder, or
        # a file named test_*.py or *_test.py anywhere in the repo.
        if path.suffix == ".py" and (
            "tests" in relative.parts
            or "test" in relative.parts
            or path.name.startswith("test_")
            or path.name.endswith("_test.py")
        ):
            result.test_files += 1
        # Only a README at the repository root counts: a README buried in
        # a subfolder (or in a cache directory) is not the project README.
        if (
            relative.parent == Path(".")
            and path.name.lower() in README_NAMES
            and result.readme_path is None
        ):
            result.has_readme = True
            result.readme_path = relative
        # Only a .gitignore at the repository root counts.
        if relative.parent == Path(".") and path.name == ".gitignore":
            result.has_gitignore = True
            result.gitignore_path = relative
            result.gitignore_missing_exclusions = _gitignore_missing_exclusions(
                path
            )
    # A dependency file is only looked for at the repository root, in
    # the preferred order above when more than one is present.
    for name in DEPENDENCY_FILES:
        if Path(name) in result.files:
            result.dependency_file = Path(name)
            break
    return result
