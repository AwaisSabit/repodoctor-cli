"""Tests for the sample project."""

from pathlib import Path


def test_readme_names_the_project():
    """The sample README names the project it describes."""
    text = (Path(__file__).resolve().parents[1] / "README.md").read_text(
        encoding="utf-8"
    )
    assert "Sample Project" in text
