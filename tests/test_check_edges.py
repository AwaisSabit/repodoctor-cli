"""Scanner edge cases for the RepoDoctor checks.

These tests cover the boundaries and corners the earlier check tests
did not reach, each through a temporary directory so nothing touches
the real repository: the large-file threshold itself, README name
variants, dependency files outside the root, the remaining ways a
test file can be recognised, a .gitignore holding only comments,
files the scanner cannot read as text, marker words that look like
markers but are not, and the generated directories not yet exercised.
"""

from __future__ import annotations

from pathlib import Path

from repodoctor.checks import run_checks
from repodoctor.scanner import (
    LARGE_FILE_THRESHOLD_BYTES,
    TODO_MARKERS,
    scan_path,
)

FULL_GITIGNORE = ".venv/\n__pycache__/\n"


def _codes(findings) -> list[str]:
    return [finding.code for finding in findings]


def _marker_text(*markers: str) -> str:
    """Build text holding one marker per line, from marker words."""
    return "".join(f"# {marker}: note here\n" for marker in markers)


# --- Large-file threshold boundary ---


def test_large_file_exactly_at_threshold_is_not_flagged(
    tmp_path: Path,
) -> None:
    """A file of exactly 1 MB is not large: the rule is "over 1 MB"."""
    (tmp_path / "exact.bin").write_bytes(b"x" * LARGE_FILE_THRESHOLD_BYTES)

    result = scan_path(tmp_path)

    assert result.large_files == []
    assert "large-file" not in _codes(run_checks(result))


# --- README name variants ---


def test_readme_without_an_extension_counts(tmp_path: Path) -> None:
    """A plain file named README at the root is the project README."""
    (tmp_path / "README").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.has_readme is True
    assert result.readme_path == Path("README")
    assert "missing-readme" not in _codes(run_checks(result))


def test_readme_with_mixed_case_counts(tmp_path: Path) -> None:
    """README names match case-insensitively (Readme.md counts)."""
    (tmp_path / "Readme.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.has_readme is True
    assert result.readme_path == Path("Readme.md")
    assert "missing-readme" not in _codes(run_checks(result))


# --- Dependency files outside the root, and preference order ---


def test_nested_dependency_file_does_not_count(tmp_path: Path) -> None:
    """A pyproject.toml under src/ is not the project's dependency file."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.dependency_file is None
    assert "missing-dependency-file" in _codes(run_checks(result))


def test_requirements_preferred_over_setup_py(tmp_path: Path) -> None:
    """When both exist, requirements.txt is reported before setup.py."""
    (tmp_path / "setup.py").write_text("# setup\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.dependency_file == Path("requirements.txt")


# --- Test-file recognition: the remaining shapes ---


def test_singular_test_directory_counts(tmp_path: Path) -> None:
    """A file under a test/ folder (singular) counts as a test file."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "helpers.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.test_files == 1
    assert "missing-tests" not in _codes(run_checks(result))


def test_underscore_test_suffix_at_root_counts(tmp_path: Path) -> None:
    """A file named *_test.py at the root counts as a test file."""
    (tmp_path / "app_test.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.test_files == 1
    assert "missing-tests" not in _codes(run_checks(result))


def test_non_python_file_under_tests_does_not_count(tmp_path: Path) -> None:
    """A text file under tests/ is not a test file."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "notes.txt").write_text("notes\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.test_files == 0
    assert "missing-tests" in _codes(run_checks(result))


# --- .gitignore corners ---


def test_gitignore_with_only_comments_misses_both_exclusions(
    tmp_path: Path,
) -> None:
    """Comments and blank lines in .gitignore add no exclusions."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(
        "# ignore nothing yet\n\n# another comment\n", encoding="utf-8"
    )

    result = scan_path(tmp_path)

    assert result.has_gitignore is True
    assert result.gitignore_entries == set()
    assert result.gitignore_missing_exclusions == [
        ".venv/",
        "__pycache__/",
    ]
    finding = next(
        f for f in run_checks(result) if f.code == "gitignore-missing-exclusions"
    )
    assert ".venv/" in finding.message
    assert "__pycache__/" in finding.message


def test_nested_gitignore_does_not_count(tmp_path: Path) -> None:
    """A .gitignore under docs/ is not the project's .gitignore."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.has_gitignore is False
    assert "missing-gitignore" in _codes(run_checks(result))


# --- Files the scanner cannot read ---


def test_unreadable_python_file_is_skipped_not_reported(
    tmp_path: Path,
) -> None:
    """A .py file that is not valid UTF-8 is skipped, never flagged."""
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe\x00not text")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.python_files == 2
    assert result.syntax_errors == []
    assert "syntax-error" not in _codes(run_checks(result))


# --- Syntax errors in nested files ---


def test_syntax_error_in_nested_file_reports_relative_path(
    tmp_path: Path,
) -> None:
    """A broken file under src/ is reported by its relative path."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "bad.py").write_text("def broken(:\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.syntax_errors == [(Path("src/bad.py"), 1, "invalid syntax")]
    error = next(f for f in findings if f.code == "syntax-error")
    assert "src/bad.py" in error.message
    assert "line 1" in error.message


# --- Reminder markers that are not markers ---


def test_lowercase_marker_word_is_not_counted(tmp_path: Path) -> None:
    """A lowercase marker word with a colon is not a reminder marker."""
    (tmp_path / "notes.md").write_text("todo: fix this later\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.todo_markers == []
    assert "todo-markers" not in _codes(run_checks(result))


def test_marker_word_inside_a_longer_word_is_not_counted(
    tmp_path: Path,
) -> None:
    """A marker word glued to other letters is not a marker."""
    (tmp_path / "notes.md").write_text(
        f"{TODO_MARKERS[0]}S: fix this later\n", encoding="utf-8"
    )

    result = scan_path(tmp_path)

    assert result.todo_markers == []
    assert "todo-markers" not in _codes(run_checks(result))


def test_markers_counted_in_txt_and_json_files(tmp_path: Path) -> None:
    """Markers are counted in every text suffix, not just code and docs."""
    (tmp_path / "notes.txt").write_text(_marker_text(TODO_MARKERS[0]), encoding="utf-8")
    (tmp_path / "data.json").write_text(
        _marker_text(TODO_MARKERS[1], TODO_MARKERS[2]), encoding="utf-8"
    )

    result = scan_path(tmp_path)

    assert result.todo_markers == [
        (Path("data.json"), 2),
        (Path("notes.txt"), 1),
    ]
    infos = [f for f in run_checks(result) if f.code == "todo-markers"]
    assert len(infos) == 2
    assert all(f.severity == "info" for f in infos)


# --- Generated directories: the remaining names ---


def test_git_directory_is_not_a_generated_directory(tmp_path: Path) -> None:
    """A .git folder is skipped but never reported as generated."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.generated_dirs == []
    assert "generated-dir-not-ignored" not in _codes(run_checks(result))


def test_tox_directory_is_flagged_when_not_ignored(tmp_path: Path) -> None:
    """A .tox folder not listed in .gitignore is a generated-dir warning."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / ".tox").mkdir()
    (tmp_path / ".tox" / "py312").mkdir()

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.generated_dirs == [Path(".tox")]
    generated = [f for f in findings if f.code == "generated-dir-not-ignored"]
    assert len(generated) == 1
    assert generated[0].path == Path(".tox")
    assert ".tox" in generated[0].message


def test_multiple_generated_dirs_each_get_a_warning(tmp_path: Path) -> None:
    """Two unlisted generated directories produce two warnings."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "build").mkdir()

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.generated_dirs == [Path("build"), Path("dist")]
    generated = [f for f in findings if f.code == "generated-dir-not-ignored"]
    assert [f.path for f in generated] == [Path("build"), Path("dist")]
