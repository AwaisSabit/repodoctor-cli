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
        # Only a README at the repository root counts: a README buried in
        # a subfolder (or in a cache directory) is not the project README.
        if (
            relative.parent == Path(".")
            and path.name.lower() in README_NAMES
            and result.readme_path is None
        ):
            result.has_readme = True
            result.readme_path = relative
    return result
