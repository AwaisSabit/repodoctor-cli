"""Read-only scanner for a target directory.

The scanner never writes to, deletes, or executes anything inside the
target. It walks the tree with :meth:`pathlib.Path.rglob`, skipping
version-control and generated directories, and collects basic facts:
how many files exist, how many are Python files, whether a README
is present, which files are larger than 1 MB, which generated
or cache directories exist (even though their contents are skipped),
which Python files do not compile, and how many reminder markers
(TODO, FIXME, XXX or HACK, each followed by a colon) text files
contain. Python files are only compiled, never executed.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import ScanResult

#: Directories that are generated, cached, or version-control metadata.
#: Skipping them keeps counts meaningful and avoids scanning a virtual
#: environment or a ``.git`` directory.
SKIPPED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".mypy_cache",
        "dist",
        "build",
    }
)

#: Directories that are generated or cached. Their contents are
#: skipped (see ``SKIPPED_DIRS``), but the scanner still records that
#: the directory exists, so the checks can warn when it is not
#: covered by ``.gitignore``.
GENERATED_DIRS = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
    }
)

#: Files larger than this are flagged by the large-file check.
LARGE_FILE_THRESHOLD_BYTES = 1_048_576  # 1 MB

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


def _normalize_entry(entry: str) -> str:
    """Return a .gitignore entry with forward slashes.

    A .gitignore written on Windows may list entries with backslash
    separators (``src\\__pycache__`` or ``.venv\\``); those must match
    the same directory as the forward-slash form, so entries are
    stored in forward-slash form whatever platform wrote the file.
    The entry text itself (apart from the separator) is untouched.
    """
    return entry.replace("\\", "/")


def _gitignore_entries(gitignore_path: Path) -> set[str]:
    """Return the entries of ``gitignore_path``, ignoring blanks and comments.

    Reading the file is a read-only operation; a file that cannot be
    read as text is treated as if it had no entries at all. Entries
    are stored with forward slashes (see ``_normalize_entry``), so
    matching and JSON output are identical on every platform.
    """
    try:
        text = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    return {
        _normalize_entry(line.strip())
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _gitignore_missing_exclusions(gitignore_path: Path) -> list[str]:
    """Return the required exclusions missing from ``gitignore_path``."""
    entries = _gitignore_entries(gitignore_path)
    missing = []
    for exclusion in REQUIRED_GITIGNORE_EXCLUSIONS:
        if exclusion not in entries and exclusion.rstrip("/") not in entries:
            missing.append(exclusion)
    return missing


#: File name suffixes treated as text for the reminder-marker check.
#: Other files (images, archives, compiled files and the like) are
#: not scanned for markers.
TEXT_FILE_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".rst",
        ".toml",
        ".cfg",
        ".ini",
        ".json",
        ".yaml",
        ".yml",
        ".js",
        ".ts",
        ".sh",
        ".html",
        ".css",
    }
)

#: Reminder-marker words. A marker is one of these words followed by
#: a colon, the usual style for a note left in code or docs. The
#: colon matters: the words on their own (for example in this
#: module's own marker list, or in a sentence about markers) are
#: not counted, so the tool does not flag its own source.
TODO_MARKERS = ("TODO", "FIXME", "XXX", "HACK")

#: Matches a reminder marker: one of the marker words, as a whole
#: word, followed by a colon.
TODO_MARKER_PATTERN = re.compile(r"\b(?:TODO|FIXME|XXX|HACK):")


def _read_text(path: Path) -> str | None:
    """Return ``path`` as text, or None when it cannot be read.

    A file that cannot be read as UTF-8 text is skipped by the
    syntax and marker checks instead of being reported: the tool
    cannot judge what it cannot read. Reading is read-only.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _check_syntax(source: str, relative: Path, result: ScanResult) -> None:
    """Compile ``source`` and record a syntax error, if there is one.

    :func:`compile` only parses the source; it never runs it, so a
    file with dangerous or broken code is still safe to scan. It also
    never writes bytecode: unlike importing a module, compiling a
    string creates no ``.pyc`` file. The file name is passed in
    forward-slash form so error messages read the same on Windows,
    macOS and Linux.
    """
    try:
        compile(source, relative.as_posix(), "exec")
    except SyntaxError as exc:
        result.syntax_errors.append((relative, exc.lineno or 1, exc.msg or str(exc)))


def _count_todo_markers(source: str, relative: Path, result: ScanResult) -> None:
    """Count reminder markers in ``source`` and record them per file."""
    count = len(TODO_MARKER_PATTERN.findall(source))
    if count:
        result.todo_markers.append((relative, count))


def _path_parts(path: Path) -> tuple[str, ...]:
    """Return the parts of ``path``, splitting on either separator.

    ``pathlib`` splits on the host platform's separator only, so a
    relative path written with the other platform's separator (for
    example a Windows-style ``src\\__pycache__`` on Linux) would
    arrive as a single part and the skipped-directory check would
    miss it. Splitting on both ``/`` and ``\\`` keeps the skipped
    and generated-directory logic working with either separator.
    """
    return tuple(
        part for part in re.split(r"[/\\]", str(path)) if part not in ("", ".")
    )


def _is_skipped(path: Path) -> bool:
    """Return True if any part of ``path`` is a skipped directory.

    Either separator counts, so a Windows-style path is recognised
    on Linux and macOS too (see ``_path_parts``).
    """
    return any(part in SKIPPED_DIRS for part in _path_parts(path))


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
        raise FileNotFoundError(f"target does not exist: {target_path.as_posix()}")
    if not target_path.is_dir():
        raise NotADirectoryError(f"target is not a directory: {target_path.as_posix()}")

    result = ScanResult(target=target_path.resolve())
    for path in sorted(target_path.rglob("*")):
        relative = path.relative_to(target_path)
        if path.is_dir():
            # A generated directory is recorded even though its
            # contents are skipped. A generated directory nested
            # inside another skipped directory (for example
            # ``.venv/__pycache__``) is not recorded twice.
            if path.name in GENERATED_DIRS and not _is_skipped(relative.parent):
                result.generated_dirs.append(relative)
            continue
        if _is_skipped(relative):
            continue
        if not path.is_file():
            continue
        result.files.append(relative)
        result.total_files += 1
        size = path.stat().st_size
        if size > LARGE_FILE_THRESHOLD_BYTES:
            result.large_files.append((relative, size))
        if path.suffix == ".py":
            result.python_files += 1
        # A test file is a .py file inside a tests/ or test/ folder, or
        # a file named test_*.py or *_test.py anywhere in the repo.
        # Either separator counts for the folder names (see
        # ``_path_parts``), so a Windows-style path is recognised
        # on Linux and macOS too.
        parts = _path_parts(relative)
        if path.suffix == ".py" and (
            "tests" in parts
            or "test" in parts
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
            result.gitignore_entries = _gitignore_entries(path)
            result.gitignore_missing_exclusions = _gitignore_missing_exclusions(path)
        # Python files are compiled (never executed) and text files
        # are scanned for reminder markers. Each file is read once.
        if path.suffix in TEXT_FILE_SUFFIXES:
            source = _read_text(path)
            if source is not None:
                if path.suffix == ".py":
                    _check_syntax(source, relative, result)
                _count_todo_markers(source, relative, result)
    # A dependency file is only looked for at the repository root, in
    # the preferred order above when more than one is present.
    for name in DEPENDENCY_FILES:
        if Path(name) in result.files:
            result.dependency_file = Path(name)
            break
    return result
