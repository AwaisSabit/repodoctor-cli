"""Tests that scanning never writes to the scanned folder.

RepoDoctor promises a read-only scan: it only reads files, it never
writes, deletes or executes anything in the target. These tests prove
it by snapshotting a temporary folder — every name, every file's
contents and every modification time — and checking the snapshot is
byte-identical after a scan. They also check the two ways a scan
could still write by accident: compiling a broken Python file must
not create a ``.pyc`` file, and scanning a read-only directory must
still succeed.

This file contains no literal reminder-marker text, so the tool
still reports no findings on its own repository.
"""

from __future__ import annotations

import os
from pathlib import Path

from repodoctor.checks import run_checks
from repodoctor.scanner import scan_path


def _snapshot(folder: Path) -> dict[str, tuple]:
    """Snapshot ``folder``: every relative path with its kind, its
    contents (for files) and its modification time."""
    snapshot: dict[str, tuple] = {}
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder).as_posix()
        stat = path.stat()
        if path.is_dir():
            snapshot[relative] = ("dir", stat.st_mtime_ns)
        elif path.is_file():
            snapshot[relative] = (
                "file",
                path.read_bytes(),
                stat.st_mtime_ns,
            )
    return snapshot


def _folder_with_broken_file(tmp_path: Path) -> Path:
    """Build a folder with a clean file, a broken Python file and a
    notes file, plus the usual healthy-project files."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text(
        "def broken(:\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "notes.txt").write_text(
        "Remember to tidy this up later.\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text(
        "VALUE = 42\n", encoding="utf-8"
    )
    return tmp_path


def test_scan_leaves_folder_byte_identical(tmp_path: Path) -> None:
    """A scan changes nothing: names, contents and modification
    times are identical afterwards, and no new file appears."""
    folder = _folder_with_broken_file(tmp_path)
    before = _snapshot(folder)

    result = scan_path(folder)
    run_checks(result)

    assert _snapshot(folder) == before
    assert not any(
        "__pycache__" in relative.split("/")
        for relative in _snapshot(folder)
    )


def test_scan_broken_python_file_creates_no_bytecode(
    tmp_path: Path,
) -> None:
    """Compiling a broken Python file writes no .pyc file: the
    scanner uses compile() on the source text, which never writes
    bytecode the way importing a module would."""
    folder = _folder_with_broken_file(tmp_path)

    result = scan_path(folder)

    assert result.syntax_errors != []
    assert list(folder.rglob("*.pyc")) == []
    assert list(folder.rglob("__pycache__")) == []


def test_scan_does_not_change_any_mtime(tmp_path: Path) -> None:
    """No file in the scanned tree gets a newer modification time:
    the scanner never opens a file for writing."""
    folder = _folder_with_broken_file(tmp_path)
    mtimes_before = {
        path.relative_to(folder).as_posix(): path.stat().st_mtime_ns
        for path in folder.rglob("*")
        if path.is_file()
    }

    scan_path(folder)

    mtimes_after = {
        path.relative_to(folder).as_posix(): path.stat().st_mtime_ns
        for path in folder.rglob("*")
        if path.is_file()
    }
    assert mtimes_after == mtimes_before


def _make_writable(folder: Path) -> None:
    """Restore write permission so the temporary folder can be
    cleaned up."""
    for path in sorted(folder.rglob("*"), reverse=True):
        if path.is_dir():
            os.chmod(path, 0o755)
        elif path.is_file():
            os.chmod(path, 0o644)
    os.chmod(folder, 0o755)


def test_scan_read_only_directory_still_succeeds(
    tmp_path: Path,
) -> None:
    """A scan of a read-only directory still succeeds and still
    reports its findings: nothing the scanner does needs write
    access to the target."""
    folder = _folder_with_broken_file(tmp_path)
    before = _snapshot(folder)
    try:
        for path in sorted(folder.rglob("*"), reverse=True):
            if path.is_dir():
                os.chmod(path, 0o555)
            elif path.is_file():
                os.chmod(path, 0o444)
        os.chmod(folder, 0o555)

        result = scan_path(folder)
        findings = run_checks(result)

        assert result.syntax_errors != []
        assert any(
            finding.code == "syntax-error" for finding in findings
        )
        assert _snapshot(folder) == before
        assert list(folder.rglob("*.pyc")) == []
    finally:
        _make_writable(folder)


def test_scan_read_only_directory_reports_no_new_files(
    tmp_path: Path,
) -> None:
    """A scan of a read-only directory creates no files at all —
    not even a cache directory — inside the target."""
    folder = _folder_with_broken_file(tmp_path)
    try:
        for path in sorted(folder.rglob("*"), reverse=True):
            if path.is_dir():
                os.chmod(path, 0o555)
            elif path.is_file():
                os.chmod(path, 0o444)
        os.chmod(folder, 0o555)

        scan_path(folder)

        assert sorted(
            path.relative_to(folder).as_posix()
            for path in folder.rglob("*")
        ) == sorted(
            [
                "README.md",
                "app.py",
                "broken.py",
                "notes.txt",
                "src",
                "src/mod.py",
            ]
        )
    finally:
        _make_writable(folder)
