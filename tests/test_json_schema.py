"""Tests that the JSON report follows its documented structure.

The JSON report is the machine-readable form of a scan, used by
scripts and CI, so its shape is part of the tool's promise: the
top-level keys, the type of every field, the summary counts matching
the findings list, and the schema version. These tests check that
shape with plain assertions — no extra validation library is needed.
"""

from __future__ import annotations

import json

import pytest

from repodoctor import __version__
from repodoctor.cli import main
from repodoctor.reporters import JSON_SCHEMA_VERSION

#: Every top-level key the JSON report must carry, no more and no
#: fewer. A field added, removed or renamed is a schema change, so
#: this set has to be updated deliberately, with a schema bump.
EXPECTED_TOP_LEVEL_KEYS = {
    "tool",
    "schema_version",
    "tool_version",
    "target",
    "total_files",
    "python_files",
    "has_python_files",
    "files",
    "has_readme",
    "readme_path",
    "has_gitignore",
    "gitignore_path",
    "gitignore_entries",
    "gitignore_missing_exclusions",
    "dependency_file",
    "test_files",
    "has_tests",
    "large_files",
    "generated_dirs",
    "syntax_errors",
    "todo_markers",
    "findings",
    "summary",
}

#: The keys every finding entry must carry, no more and no fewer.
EXPECTED_FINDING_KEYS = {"code", "message", "severity", "path"}

#: The severities a finding may carry.
SEVERITIES = {"error", "warning", "info"}


def _healthy_folder(tmp_path) -> None:
    """Fill ``tmp_path`` with a folder that has no findings at all."""
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n', encoding="utf-8"
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        "def test_nothing():\n    assert True\n", encoding="utf-8"
    )


def _messy_folder(tmp_path) -> None:
    """Fill ``tmp_path`` with a folder that has findings of every
    severity: a Python file that does not compile (an error), a
    missing README, ``.gitignore``, dependency file and tests plus
    one file over 1 MB (warnings), and a file carrying one reminder
    marker (a note)."""
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    # The marker word is built from pieces so this test file itself
    # contains no literal marker text and the tool's own scan stays
    # clean.
    marker = ("TO" + "DO") + ": remember this\n"
    (tmp_path / "notes.txt").write_text(marker, encoding="utf-8")
    (tmp_path / "big.bin").write_bytes(b"x" * 1_048_577)


def _json_report(tmp_path, capsys) -> tuple[int, dict]:
    """Run the CLI in JSON mode on ``tmp_path`` and return the exit
    code and the parsed JSON document."""
    exit_code = main([str(tmp_path), "--format", "json"])
    return exit_code, json.loads(capsys.readouterr().out)


def test_json_has_exactly_the_documented_top_level_keys(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The report carries every documented key and no extra ones."""
    _healthy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert set(payload) == EXPECTED_TOP_LEVEL_KEYS


def test_json_top_level_keys_are_the_same_with_findings(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Findings do not add or remove top-level keys."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert set(payload) == EXPECTED_TOP_LEVEL_KEYS


def test_json_schema_version_and_tool_version(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The report names the tool, the schema version and the tool
    version, and the schema version matches the reporter's
    constant."""
    _healthy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["tool"] == "repodoctor"
    assert payload["schema_version"] == JSON_SCHEMA_VERSION
    assert payload["schema_version"] == 1
    assert type(payload["schema_version"]) is int
    assert payload["tool_version"] == __version__
    assert isinstance(payload["tool_version"], str)


def test_json_field_types_on_a_clean_repo(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every field has the documented type on a clean repo."""
    _healthy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["target"] == str(tmp_path)
    assert type(payload["total_files"]) is int
    assert type(payload["python_files"]) is int
    assert type(payload["has_python_files"]) is bool
    assert payload["has_python_files"] is True
    assert isinstance(payload["files"], list)
    assert all(isinstance(name, str) for name in payload["files"])
    assert payload["has_readme"] is True
    assert payload["readme_path"] == "README.md"
    assert payload["has_gitignore"] is True
    assert payload["gitignore_path"] == ".gitignore"
    assert payload["gitignore_entries"] == [".venv/", "__pycache__/"]
    assert payload["gitignore_missing_exclusions"] == []
    assert payload["dependency_file"] == "pyproject.toml"
    assert type(payload["test_files"]) is int
    assert payload["has_tests"] is True
    assert payload["large_files"] == []
    assert payload["generated_dirs"] == []
    assert payload["syntax_errors"] == []
    assert payload["todo_markers"] == []
    assert payload["findings"] == []
    assert payload["summary"] == {
        "total": 0,
        "errors": 0,
        "warnings": 0,
        "notes": 0,
    }


def test_json_field_types_when_facts_are_missing(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing facts are null or false, never the wrong type."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["has_readme"] is False
    assert payload["readme_path"] is None
    assert payload["has_gitignore"] is False
    assert payload["gitignore_path"] is None
    assert payload["gitignore_entries"] == []
    assert payload["dependency_file"] is None
    assert payload["has_tests"] is False
    assert payload["test_files"] == 0


def test_json_summary_counts_match_the_findings_list(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The summary is counted from the same findings list it
    describes, so the two can never disagree."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert set(payload["summary"]) == {"total", "errors", "warnings", "notes"}
    findings = payload["findings"]
    expected = {
        "total": len(findings),
        "errors": sum(1 for f in findings if f["severity"] == "error"),
        "warnings": sum(1 for f in findings if f["severity"] == "warning"),
        "notes": sum(1 for f in findings if f["severity"] == "info"),
    }
    assert payload["summary"] == expected
    assert all(type(value) is int for value in payload["summary"].values())


def test_json_summary_covers_each_severity(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A folder with findings of every severity reports at least
    one of each in the summary."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "syntax-error" in codes
    assert "missing-readme" in codes
    assert "large-file" in codes
    assert "todo-markers" in codes
    assert payload["summary"]["errors"] == 1
    assert payload["summary"]["warnings"] == 5
    assert payload["summary"]["notes"] == 1
    assert payload["summary"]["total"] == 7


def test_json_finding_entries_have_the_documented_shape(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every finding has exactly code, message, severity and path,
    with the right types and a known severity."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["findings"]
    for finding in payload["findings"]:
        assert set(finding) == EXPECTED_FINDING_KEYS
        assert isinstance(finding["code"], str) and finding["code"]
        assert isinstance(finding["message"], str) and finding["message"]
        assert finding["severity"] in SEVERITIES
        assert finding["path"] is None or isinstance(finding["path"], str)


def test_json_large_file_entries(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file over 1 MB is reported with its path, its size in bytes
    and a human-readable size."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["large_files"] == [
        {"path": "big.bin", "size_bytes": 1_048_577, "size": "1.0 MB"}
    ]
    entry = payload["large_files"][0]
    assert set(entry) == {"path", "size_bytes", "size"}
    assert type(entry["size_bytes"]) is int
    assert entry["size_bytes"] > 1_048_576


def test_json_syntax_error_entries(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that does not compile is reported with its path, the
    line number and the error message."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert len(payload["syntax_errors"]) == 1
    entry = payload["syntax_errors"][0]
    assert set(entry) == {"path", "line", "message"}
    assert entry["path"] == "broken.py"
    assert type(entry["line"]) is int
    assert entry["line"] == 1
    assert isinstance(entry["message"], str) and entry["message"]


def test_json_marker_entries(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file with reminder markers is reported with its path and
    how many markers it has."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert payload["todo_markers"] == [{"path": "notes.txt", "count": 1}]
    entry = payload["todo_markers"][0]
    assert set(entry) == {"path", "count"}
    assert type(entry["count"]) is int


def test_json_files_are_relative_forward_slash_paths(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Listed files are paths relative to the target, never
    absolute and never using backslashes."""
    _messy_folder(tmp_path)
    _, payload = _json_report(tmp_path, capsys)
    assert sorted(payload["files"]) == ["big.bin", "broken.py", "notes.txt"]
    for name in payload["files"]:
        assert not name.startswith("/")
        assert "\\" not in name
        assert str(tmp_path) not in name


def test_json_gitignore_entries_are_sorted(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The gitignore entries are listed in sorted order, so the
    output is stable from run to run."""
    _healthy_folder(tmp_path)
    (tmp_path / ".gitignore").write_text("zeta/\n.alpha/\nmid/\n", encoding="utf-8")
    _, payload = _json_report(tmp_path, capsys)
    assert payload["gitignore_entries"] == [".alpha/", "mid/", "zeta/"]


def test_json_empty_folder_summary_matches_its_findings(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Even an empty folder keeps its summary in step with its
    findings."""
    _, payload = _json_report(tmp_path, capsys)
    assert payload["total_files"] == 0
    assert payload["has_python_files"] is False
    assert payload["findings"]
    assert payload["summary"]["total"] == len(payload["findings"])
    assert payload["summary"]["errors"] == sum(
        1 for f in payload["findings"] if f["severity"] == "error"
    )
