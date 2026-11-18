"""Direct unit tests for the RepoDoctor check functions.

The checks in :mod:`repodoctor.checks` are pure functions of a
:class:`~repodoctor.models.ScanResult`, so they are tested here in
isolation, with hand-built scan results and no filesystem at all.
The scanner-level tests live in ``test_checks.py`` (checks reached
through ``scan_path``) and ``test_check_edges.py`` (scanner edge
cases); this file covers the happy path, the finding path and the
edge cases of each check function itself.
"""

from __future__ import annotations

from pathlib import Path

from repodoctor.checks import (
    CHECKS,
    check_dependency_file,
    check_empty,
    check_generated_dirs,
    check_gitignore,
    check_large_files,
    check_python_files,
    check_readme,
    check_syntax_errors,
    check_tests,
    check_todo_markers,
    run_checks,
)
from repodoctor.models import ScanResult, human_size


def _result(**kwargs) -> ScanResult:
    """Build a scan result with the given facts, defaults otherwise."""
    return ScanResult(target=Path("."), **kwargs)


# --- Empty-directory check ---


def test_empty_directory_check_flags_an_empty_result() -> None:
    """A result with no files at all gets the empty-directory warning."""
    finding = check_empty(_result(total_files=0))

    assert finding is not None
    assert finding.code == "empty-directory"
    assert finding.severity == "warning"
    assert "no files" in finding.message


def test_empty_directory_check_passes_a_non_empty_result() -> None:
    """A result with files gets no empty-directory finding."""
    assert check_empty(_result(total_files=3)) is None


def test_run_checks_on_an_empty_result_reports_all_six_findings() -> None:
    """An empty folder fails every presence check, in check order."""
    result = _result()
    findings = run_checks(result)

    assert [f.code for f in findings] == [
        "empty-directory",
        "missing-readme",
        "no-python-files",
        "missing-gitignore",
        "missing-dependency-file",
        "missing-tests",
    ]
    # The findings are stored on the result as well as returned.
    assert result.findings == findings


# --- README check ---


def test_readme_check_flags_a_missing_readme() -> None:
    """A result with no README gets the missing-readme warning."""
    finding = check_readme(_result(has_readme=False))

    assert finding is not None
    assert finding.code == "missing-readme"
    assert finding.severity == "warning"
    assert "README" in finding.message


def test_readme_check_passes_when_a_readme_is_present() -> None:
    """A result with a README gets no finding."""
    assert check_readme(
        _result(has_readme=True, readme_path=Path("README.md"))
    ) is None


# --- No-Python-files check ---


def test_no_python_files_check_is_an_informational_note() -> None:
    """A result with no .py files gets an info-level note, not a warning."""
    finding = check_python_files(_result(python_files=0))

    assert finding is not None
    assert finding.code == "no-python-files"
    assert finding.severity == "info"
    assert ".py" in finding.message


def test_no_python_files_check_passes_when_python_files_exist() -> None:
    """A result with .py files gets no finding."""
    assert check_python_files(_result(python_files=2)) is None


# --- .gitignore check ---


def test_gitignore_check_flags_a_missing_gitignore() -> None:
    """A result with no .gitignore gets the missing-gitignore warning."""
    finding = check_gitignore(_result(has_gitignore=False))

    assert finding is not None
    assert finding.code == "missing-gitignore"
    assert finding.severity == "warning"
    assert ".gitignore" in finding.message


def test_gitignore_check_names_both_missing_exclusions() -> None:
    """A .gitignore missing both exclusions names both in the message."""
    finding = check_gitignore(
        _result(
            has_gitignore=True,
            gitignore_missing_exclusions=[".venv/", "__pycache__/"],
        )
    )

    assert finding is not None
    assert finding.code == "gitignore-missing-exclusions"
    assert finding.severity == "warning"
    assert ".venv/" in finding.message
    assert "__pycache__/" in finding.message


def test_gitignore_check_passes_when_nothing_is_missing() -> None:
    """A .gitignore with every exclusion gets no finding."""
    assert check_gitignore(
        _result(
            has_gitignore=True,
            gitignore_missing_exclusions=[],
        )
    ) is None


# --- Dependency-file check ---


def test_dependency_check_flags_a_missing_dependency_file() -> None:
    """A result with no dependency file gets the warning."""
    finding = check_dependency_file(_result(dependency_file=None))

    assert finding is not None
    assert finding.code == "missing-dependency-file"
    assert finding.severity == "warning"
    assert "pyproject.toml" in finding.message


def test_dependency_check_passes_when_a_dependency_file_exists() -> None:
    """A result naming a dependency file gets no finding."""
    assert check_dependency_file(
        _result(dependency_file=Path("requirements.txt"))
    ) is None


# --- Test-structure check ---


def test_tests_check_flags_missing_tests() -> None:
    """A result with no test files gets the missing-tests warning."""
    finding = check_tests(_result(test_files=0))

    assert finding is not None
    assert finding.code == "missing-tests"
    assert finding.severity == "warning"
    assert "tests" in finding.message


def test_tests_check_passes_when_test_files_exist() -> None:
    """A result with test files gets no finding."""
    assert check_tests(_result(test_files=4)) is None


# --- Large-file check ---


def test_large_files_check_reports_each_file_with_its_size() -> None:
    """Each large file gets its own warning, with path and size."""
    findings = check_large_files(
        _result(
            large_files=[
                (Path("a.bin"), 2_097_152),
                (Path("sub/b.bin"), 1_572_864),
            ]
        )
    )

    assert len(findings) == 2
    assert [f.code for f in findings] == ["large-file", "large-file"]
    assert all(f.severity == "warning" for f in findings)
    assert [f.path for f in findings] == [
        Path("a.bin"),
        Path("sub/b.bin"),
    ]
    assert "a.bin" in findings[0].message
    assert "2.0 MB" in findings[0].message
    assert "sub/b.bin" in findings[1].message
    assert "1.5 MB" in findings[1].message


def test_large_files_check_passes_when_nothing_is_large() -> None:
    """A result with no large files gets no findings."""
    assert check_large_files(_result(large_files=[])) == []


# --- Generated-directory check ---


def test_generated_dirs_check_flags_each_unlisted_directory() -> None:
    """Each generated directory not in .gitignore gets its own warning."""
    findings = check_generated_dirs(
        _result(
            has_gitignore=True,
            gitignore_entries=set(),
            generated_dirs=[Path("dist"), Path("build")],
        )
    )

    assert len(findings) == 2
    assert [f.code for f in findings] == [
        "generated-dir-not-ignored",
        "generated-dir-not-ignored",
    ]
    assert all(f.severity == "warning" for f in findings)
    assert [f.path for f in findings] == [Path("dist"), Path("build")]
    assert "not listed in .gitignore" in findings[0].message


def test_generated_dirs_check_names_the_missing_gitignore() -> None:
    """With no .gitignore, the message says so instead."""
    findings = check_generated_dirs(
        _result(
            has_gitignore=False,
            gitignore_entries=set(),
            generated_dirs=[Path("__pycache__")],
        )
    )

    assert len(findings) == 1
    assert findings[0].code == "generated-dir-not-ignored"
    assert "no .gitignore" in findings[0].message


def test_generated_dirs_check_accepts_a_full_path_entry() -> None:
    """A nested generated dir is covered by its full-path entry."""
    findings = check_generated_dirs(
        _result(
            has_gitignore=True,
            gitignore_entries={"src/__pycache__/"},
            generated_dirs=[Path("src/__pycache__")],
        )
    )

    assert findings == []


def test_generated_dirs_check_passes_when_nothing_is_generated() -> None:
    """A result with no generated directories gets no findings."""
    assert check_generated_dirs(_result(generated_dirs=[])) == []


# --- Syntax-error check ---


def test_syntax_check_reports_file_line_and_message() -> None:
    """Each syntax error becomes an error finding naming file and line."""
    findings = check_syntax_errors(
        _result(
            syntax_errors=[
                (Path("src/bad.py"), 7, "invalid syntax"),
                (Path("other.py"), 2, "unexpected indent"),
            ]
        )
    )

    assert len(findings) == 2
    assert [f.code for f in findings] == ["syntax-error", "syntax-error"]
    assert all(f.severity == "error" for f in findings)
    assert findings[0].path == Path("src/bad.py")
    assert "src/bad.py" in findings[0].message
    assert "line 7" in findings[0].message
    assert "invalid syntax" in findings[0].message
    assert "other.py" in findings[1].message
    assert "line 2" in findings[1].message


def test_syntax_check_passes_when_nothing_is_broken() -> None:
    """A result with no syntax errors gets no findings."""
    assert check_syntax_errors(_result(syntax_errors=[])) == []


# --- Reminder-marker check ---


def test_todo_markers_check_uses_singular_wording_for_one_marker() -> None:
    """One marker in a file is reported as "1 reminder marker"."""
    findings = check_todo_markers(
        _result(todo_markers=[(Path("app.py"), 1)])
    )

    assert len(findings) == 1
    assert findings[0].code == "todo-markers"
    assert findings[0].severity == "info"
    assert findings[0].path == Path("app.py")
    assert "1 reminder marker" in findings[0].message
    assert "1 reminder markers" not in findings[0].message


def test_todo_markers_check_uses_plural_wording_for_several() -> None:
    """Several markers in a file are reported as "N reminder markers"."""
    findings = check_todo_markers(
        _result(todo_markers=[(Path("notes.md"), 5)])
    )

    assert len(findings) == 1
    assert "5 reminder markers" in findings[0].message


def test_todo_markers_check_passes_when_there_are_no_markers() -> None:
    """A result with no markers gets no findings."""
    assert check_todo_markers(_result(todo_markers=[])) == []


# --- Check set and runner wiring ---


def test_every_check_is_registered_in_order() -> None:
    """The check set holds the ten checks, in reporting order."""
    assert [check.__name__ for check in CHECKS] == [
        "check_empty",
        "check_readme",
        "check_python_files",
        "check_gitignore",
        "check_dependency_file",
        "check_tests",
        "check_large_files",
        "check_generated_dirs",
        "check_syntax_errors",
        "check_todo_markers",
    ]


def test_run_checks_on_a_healthy_result_reports_nothing() -> None:
    """A result passing every check produces no findings at all."""
    result = _result(
        total_files=5,
        python_files=2,
        has_readme=True,
        readme_path=Path("README.md"),
        has_gitignore=True,
        gitignore_missing_exclusions=[],
        dependency_file=Path("pyproject.toml"),
        test_files=1,
    )

    assert run_checks(result) == []
    assert result.findings == []


# --- human_size, used by the large-file messages ---


def test_human_size_reports_bytes_below_one_kilobyte() -> None:
    """Sizes under 1024 bytes are shown as a plain byte count."""
    assert human_size(0) == "0 bytes"
    assert human_size(512) == "512 bytes"
    assert human_size(1023) == "1023 bytes"


def test_human_size_reports_kilobytes() -> None:
    """Sizes from 1 KB up to 1 MB are shown in kilobytes."""
    assert human_size(1024) == "1.0 KB"
    assert human_size(1536) == "1.5 KB"
    assert human_size(1_048_575) == "1024.0 KB"


def test_human_size_reports_megabytes() -> None:
    """Sizes from 1 MB up are shown in megabytes."""
    assert human_size(1_048_576) == "1.0 MB"
    assert human_size(2_621_440) == "2.5 MB"
