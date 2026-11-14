"""Tests for the .gitignore, dependency-file, test-structure, large-file
and generated-directory checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repodoctor.checks import run_checks
from repodoctor.cli import main
from repodoctor.scanner import LARGE_FILE_THRESHOLD_BYTES, scan_path

FULL_GITIGNORE = ".venv/\n__pycache__/\n"


def _codes(findings) -> list[str]:
    return [finding.code for finding in findings]


def _healthy_folder(tmp_path: Path) -> Path:
    """Build a folder that passes every check."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text(
        "def test_nothing():\n    pass\n", encoding="utf-8"
    )
    return tmp_path


# --- .gitignore check ---


def test_gitignore_missing_warns(tmp_path: Path) -> None:
    """A folder with no .gitignore gets the missing-gitignore warning."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.has_gitignore is False
    assert "missing-gitignore" in _codes(findings)


def test_gitignore_present_with_both_exclusions_passes(
    tmp_path: Path,
) -> None:
    """A .gitignore with .venv/ and __pycache__/ produces no finding."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.has_gitignore is True
    assert result.gitignore_path == Path(".gitignore")
    assert result.gitignore_missing_exclusions == []
    assert "missing-gitignore" not in _codes(findings)
    assert "gitignore-missing-exclusions" not in _codes(findings)


def test_gitignore_missing_pycache_exclusion_warns(tmp_path: Path) -> None:
    """A .gitignore with only .venv/ warns about __pycache__/."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.gitignore_missing_exclusions == ["__pycache__/"]
    codes = _codes(findings)
    assert "gitignore-missing-exclusions" in codes
    assert "missing-gitignore" not in codes
    message = next(
        f.message for f in findings if f.code == "gitignore-missing-exclusions"
    )
    assert "__pycache__/" in message


def test_gitignore_missing_venv_exclusion_warns(tmp_path: Path) -> None:
    """A .gitignore with only __pycache__/ warns about .venv/."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.gitignore_missing_exclusions == [".venv/"]
    assert "gitignore-missing-exclusions" in _codes(run_checks(result))


def test_gitignore_entries_without_slash_still_count(tmp_path: Path) -> None:
    """Entries written as `.venv` and `__pycache__` (no slash) count."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(
        ".venv\n__pycache__\n", encoding="utf-8"
    )

    result = scan_path(tmp_path)

    assert result.gitignore_missing_exclusions == []


# --- Dependency / packaging check ---


def test_dependency_file_missing_warns(tmp_path: Path) -> None:
    """A folder with no dependency file gets the warning."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.dependency_file is None
    assert "missing-dependency-file" in _codes(run_checks(result))


@pytest.mark.parametrize(
    "name", ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"]
)
def test_each_dependency_file_counts(tmp_path: Path, name: str) -> None:
    """Each recognised dependency file is found and passes the check."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / name).write_text("# dependencies\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.dependency_file == Path(name)
    assert "missing-dependency-file" not in _codes(findings)


def test_pyproject_preferred_when_several_exist(tmp_path: Path) -> None:
    """When several dependency files exist, pyproject.toml is reported."""
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.dependency_file == Path("pyproject.toml")


# --- Test-structure check ---


def test_tests_missing_warns(tmp_path: Path) -> None:
    """A folder with no tests directory or test files gets the warning."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.test_files == 0
    assert result.has_tests is False
    assert "missing-tests" in _codes(run_checks(result))


def test_tests_directory_counts(tmp_path: Path) -> None:
    """Two files under tests/ count as two test files and pass."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.test_files == 2
    assert result.has_tests is True
    assert "missing-tests" not in _codes(findings)


def test_test_file_at_root_counts(tmp_path: Path) -> None:
    """A test_*.py file at the root counts as a test file."""
    (tmp_path / "test_app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.test_files == 1
    assert "missing-tests" not in _codes(run_checks(result))


# --- Wiring: healthy folder and CLI output ---


def test_healthy_folder_has_no_findings(tmp_path: Path) -> None:
    """A folder passing every check reports no findings at all."""
    result = scan_path(_healthy_folder(tmp_path))

    assert run_checks(result) == []
    assert result.dependency_file == Path("pyproject.toml")
    assert result.test_files == 1


def test_cli_text_output_shows_new_checks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Text output lists the new findings and the new summary lines."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "missing-gitignore" in out
    assert "missing-dependency-file" in out
    assert "missing-tests" in out
    assert "Gitignore:    no" in out
    assert "Dependency:   no" in out
    assert "Test files:   0" in out


def test_cli_json_output_shows_new_facts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON output carries the new gitignore/dependency/test facts."""
    _healthy_folder(tmp_path)

    assert main([str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["has_gitignore"] is True
    assert payload["gitignore_path"] == ".gitignore"
    assert payload["gitignore_missing_exclusions"] == []
    assert payload["dependency_file"] == "pyproject.toml"
    assert payload["test_files"] == 1
    assert payload["has_tests"] is True
    assert payload["findings"] == []


# --- Large-file check ---


def test_large_file_just_over_threshold_is_flagged(tmp_path: Path) -> None:
    """A file one byte over 1 MB is flagged, with its path and size."""
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * (LARGE_FILE_THRESHOLD_BYTES + 1))

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.large_files == [(Path("big.bin"), LARGE_FILE_THRESHOLD_BYTES + 1)]
    large = [f for f in findings if f.code == "large-file"]
    assert len(large) == 1
    assert large[0].severity == "warning"
    assert large[0].path == Path("big.bin")
    assert "big.bin" in large[0].message
    assert "1.0 MB" in large[0].message


def test_large_file_just_under_threshold_is_not_flagged(
    tmp_path: Path,
) -> None:
    """A file one byte under 1 MB produces no large-file finding."""
    (tmp_path / "almost.bin").write_bytes(
        b"x" * (LARGE_FILE_THRESHOLD_BYTES - 1)
    )

    result = scan_path(tmp_path)

    assert result.large_files == []
    assert "large-file" not in _codes(run_checks(result))


def test_large_file_inside_skipped_directory_is_not_flagged(
    tmp_path: Path,
) -> None:
    """A large file under .venv is never counted and never flagged."""
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "huge.bin").write_bytes(
        b"x" * (LARGE_FILE_THRESHOLD_BYTES + 1)
    )
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")

    result = scan_path(tmp_path)

    assert result.total_files == 1
    assert result.large_files == []
    assert "large-file" not in _codes(run_checks(result))


# --- Generated-directory check ---


def test_generated_dir_listed_in_gitignore_passes(tmp_path: Path) -> None:
    """A dist/ folder listed in .gitignore produces no finding."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(
        FULL_GITIGNORE + "dist/\n", encoding="utf-8"
    )
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "app-0.1.0.tar.gz").write_text(
        "archive\n", encoding="utf-8"
    )

    result = scan_path(tmp_path)
    findings = run_checks(result)

    assert result.generated_dirs == [Path("dist")]
    assert result.total_files == 2  # dist contents are skipped
    assert "generated-dir-not-ignored" not in _codes(findings)


def test_generated_dir_not_listed_in_gitignore_warns(tmp_path: Path) -> None:
    """A build/ folder missing from .gitignore is flagged by name."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "out.txt").write_text("built\n", encoding="utf-8")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    generated = [f for f in findings if f.code == "generated-dir-not-ignored"]
    assert len(generated) == 1
    assert generated[0].severity == "warning"
    assert generated[0].path == Path("build")
    assert "build" in generated[0].message
    assert ".gitignore" in generated[0].message


def test_generated_dir_flagged_when_no_gitignore(tmp_path: Path) -> None:
    """With no .gitignore at all, every generated directory is flagged."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"\x00")

    result = scan_path(tmp_path)
    findings = run_checks(result)

    generated = [f for f in findings if f.code == "generated-dir-not-ignored"]
    assert len(generated) == 1
    assert generated[0].path == Path("__pycache__")
    assert "no .gitignore" in generated[0].message


def test_generated_dir_entry_without_slash_still_counts(tmp_path: Path) -> None:
    """An entry written as `dist` (no slash) still covers dist/."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(
        FULL_GITIGNORE + "dist\n", encoding="utf-8"
    )
    (tmp_path / "dist").mkdir()

    result = scan_path(tmp_path)

    assert result.generated_dirs == [Path("dist")]
    assert "generated-dir-not-ignored" not in _codes(run_checks(result))


def test_nested_generated_dir_covered_by_name_entry(tmp_path: Path) -> None:
    """A nested __pycache__ is covered by a `__pycache__/` entry."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "src" / "__pycache__" / "app.pyc").write_bytes(b"\x00")

    result = scan_path(tmp_path)

    assert result.generated_dirs == [Path("src/__pycache__")]
    assert "generated-dir-not-ignored" not in _codes(run_checks(result))


def test_generated_dir_inside_skipped_dir_not_recorded_twice(
    tmp_path: Path,
) -> None:
    """``.venv/__pycache__`` is not recorded apart from ``.venv``."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(FULL_GITIGNORE, encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "__pycache__").mkdir()
    (tmp_path / ".venv" / "__pycache__" / "lib.pyc").write_bytes(b"\x00")

    result = scan_path(tmp_path)

    assert result.generated_dirs == [Path(".venv")]


# --- Wiring: healthy folder and CLI output ---


def test_healthy_folder_still_has_no_findings(tmp_path: Path) -> None:
    """A healthy folder has no large files and no generated dirs."""
    result = scan_path(_healthy_folder(tmp_path))

    assert result.large_files == []
    assert result.generated_dirs == []
    assert run_checks(result) == []


def test_cli_text_output_shows_large_files_and_generated_dirs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Text output lists large files (with size) and generated dirs."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "big.bin").write_bytes(
        b"x" * (LARGE_FILE_THRESHOLD_BYTES + 1)
    )
    (tmp_path / "dist").mkdir()

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "large-file" in out
    assert "generated-dir-not-ignored" in out
    assert "Large files:  big.bin (1.0 MB)" in out
    assert "Generated dirs: dist" in out


def test_cli_json_output_shows_large_files_and_generated_dirs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON output carries the large-file and generated-dir facts."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "big.bin").write_bytes(
        b"x" * (LARGE_FILE_THRESHOLD_BYTES + 1)
    )
    (tmp_path / "dist").mkdir()

    assert main([str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["large_files"] == [
        {
            "path": "big.bin",
            "size_bytes": LARGE_FILE_THRESHOLD_BYTES + 1,
            "size": "1.0 MB",
        }
    ]
    assert payload["generated_dirs"] == ["dist"]
    assert [f["code"] for f in payload["findings"]] == [
        "missing-readme",
        "missing-gitignore",
        "missing-dependency-file",
        "missing-tests",
        "large-file",
        "generated-dir-not-ignored",
    ]
