"""Tests that the scanner never follows symbolic links.

A crafted repository could contain a link pointing outside the folder
being scanned. Following it would make the tool read — and report
on — files the user never asked it to scan, so every link is
skipped: a link to a file is not counted or read, a link to a
folder is never descended into, and a link that loops back into the
scanned folder cannot make the scan hang.

The marker text in the outside file is built by joining pieces so
this test file itself contains no literal marker text — the tool
would otherwise flag its own repository.
"""

from __future__ import annotations

import os
from pathlib import Path

from repodoctor.scanner import scan_path


def _outside_file_with_marker(outside: Path) -> Path:
    """Write a file outside the target carrying a reminder marker."""
    marker = "TO" + "DO" + ": a note left outside the scanned folder"
    secret = outside / "secret.py"
    secret.write_text(f"SECRET = 1\n# {marker}\n", encoding="utf-8")
    return secret


def test_link_to_outside_file_is_not_counted_or_read(
    tmp_path: Path,
) -> None:
    """A link to a file outside the target is skipped entirely: the
    file is not counted, and nothing in it is reported."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = _outside_file_with_marker(outside)
    (target / "linkfile.py").symlink_to(secret)

    result = scan_path(target)

    assert [path.as_posix() for path in result.files] == ["app.py"]
    assert result.total_files == 1
    assert result.python_files == 1
    assert result.todo_markers == []


def test_link_to_outside_folder_is_not_descended_into(
    tmp_path: Path,
) -> None:
    """A link to a folder outside the target is skipped: the files
    inside it are never counted or read."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden.py").write_text("hidden = True\n", encoding="utf-8")
    _outside_file_with_marker(outside)
    (target / "escape").symlink_to(outside, target_is_directory=True)

    result = scan_path(target)

    assert [path.as_posix() for path in result.files] == ["app.py"]
    assert result.total_files == 1
    assert result.todo_markers == []


def test_link_loop_back_into_target_does_not_hang(
    tmp_path: Path,
) -> None:
    """A link that points back at the scanned folder itself does
    not loop the walk: the scan finishes and counts real files
    once."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    (target / "loop").symlink_to(target, target_is_directory=True)

    result = scan_path(target)

    assert [path.as_posix() for path in result.files] == ["app.py"]
    assert result.total_files == 1


def test_link_to_a_file_inside_the_target_is_not_counted_twice(
    tmp_path: Path,
) -> None:
    """A link to a file that is already inside the target is
    skipped too: the file is counted once, as itself, not twice."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    (target / "alias.py").symlink_to(target / "app.py")

    result = scan_path(target)

    assert [path.as_posix() for path in result.files] == ["app.py"]
    assert result.total_files == 1
    assert result.python_files == 1


def test_scan_with_links_leaves_everything_untouched(
    tmp_path: Path,
) -> None:
    """Scanning a folder full of links changes nothing anywhere:
    the outside file keeps its contents and modification time, and
    no new file appears in the target."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = _outside_file_with_marker(outside)
    before = (secret.read_bytes(), os.stat(secret).st_mtime_ns)
    (target / "linkfile.py").symlink_to(secret)
    (target / "escape").symlink_to(outside, target_is_directory=True)

    scan_path(target)

    assert (secret.read_bytes(), os.stat(secret).st_mtime_ns) == before
    assert sorted(
        path.relative_to(target).as_posix() for path in target.rglob("*")
    ) == ["app.py", "escape", "linkfile.py"]


def test_link_named_like_a_generated_directory_is_skipped(
    tmp_path: Path,
) -> None:
    """A link named like a generated directory (``.venv``) is not
    recorded as one: it is a link, not a directory in the tree."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / ".venv").symlink_to(outside, target_is_directory=True)

    result = scan_path(target)

    assert result.generated_dirs == []
    assert [path.as_posix() for path in result.files] == ["app.py"]
