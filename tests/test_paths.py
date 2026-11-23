"""Tests for bpdtools.paths."""

from pathlib import Path

from bpdtools.paths import repo_path


def test_repo_path_finds_the_package_file():
    """Check that the path of the paths module exists below the root."""
    assert repo_path("bpdtools", "paths.py").is_file()


def test_repo_path_without_parts_is_the_root():
    """Check that repo_path() returns the root folder that holds pyproject.toml."""
    # This test file is <root>/tests/test_paths.py, so its grandparent is the root.
    expected_root = Path(__file__).resolve().parents[1]
    assert repo_path() == expected_root
    assert (repo_path() / "pyproject.toml").is_file()
