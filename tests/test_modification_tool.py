"""Tests for RepositoryModificationTool."""

from pathlib import Path

import pytest

from eip.repository.modification import RepositoryModificationTool


class TestRepositoryModificationTool:
    """Test controlled file modification."""

    def test_successful_exact_replacement(self, tmp_path: Path):
        """Test successful replacement of exact content."""
        file_path = tmp_path / "config.py"
        original_content = "MAX_ITEMS = 10\nOTHER = 20\n"
        file_path.write_text(original_content)

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "config.py",
            old_content="MAX_ITEMS = 10",
            new_content="MAX_ITEMS = 20",
        )

        assert result.success is True
        assert result.changes == 1
        assert result.operation == "replace"
        assert file_path.read_text() == "MAX_ITEMS = 20\nOTHER = 20\n"

    def test_path_outside_repository_rejected(self, tmp_path: Path):
        """Test that paths outside repository are rejected."""
        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "../../../etc/passwd",
            old_content="old",
            new_content="new",
        )

        assert result.success is False
        assert "outside the repository" in result.error.lower()

    def test_nonexistent_file_rejected(self, tmp_path: Path):
        """Test that nonexistent files are rejected."""
        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "nonexistent.txt",
            old_content="old",
            new_content="new",
        )

        assert result.success is False
        assert "does not exist" in result.error.lower()

    def test_old_content_mismatch_rejected(self, tmp_path: Path):
        """Test that mismatched old_content is rejected."""
        file_path = tmp_path / "config.py"
        file_path.write_text("MAX_ITEMS = 10\n")

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "config.py",
            old_content="WRONG_CONTENT",
            new_content="new",
        )

        assert result.success is False
        assert "not found" in result.error.lower()
        # Verify file was not modified
        assert file_path.read_text() == "MAX_ITEMS = 10\n"

    def test_multiple_occurrences_rejected(self, tmp_path: Path):
        """Test that multiple occurrences are rejected."""
        file_path = tmp_path / "code.py"
        content = "TODO: fix this\nTODO: fix this\nTODO: fix this\n"
        file_path.write_text(content)

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "code.py",
            old_content="TODO: fix this",
            new_content="DONE: fixed",
        )

        assert result.success is False
        assert "appears 3 times" in result.error
        # Verify file was not modified
        assert file_path.read_text() == content

    def test_only_one_occurrence_changed(self, tmp_path: Path):
        """Test that only one occurrence is changed when there's exactly one."""
        file_path = tmp_path / "script.py"
        original = "def foo():\n    value = 10\n    return value\n"
        file_path.write_text(original)

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "script.py",
            old_content="value = 10",
            new_content="value = 20",
        )

        assert result.success is True
        assert result.changes == 1
        expected = "def foo():\n    value = 20\n    return value\n"
        assert file_path.read_text() == expected

    def test_preserves_rest_of_file(self, tmp_path: Path):
        """Test that the rest of the file is preserved exactly."""
        file_path = tmp_path / "complex.py"
        original = (
            "import os\n"
            "import sys\n"
            "\n"
            "CONFIG = {\n"
            "    'max': 10,\n"
            "    'min': 5,\n"
            "}\n"
            "\n"
            "def main():\n"
            "    pass\n"
        )
        file_path.write_text(original)

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "complex.py",
            old_content="'max': 10,",
            new_content="'max': 100,",
        )

        assert result.success is True
        modified = file_path.read_text()
        # Check that the change was made
        assert "'max': 100," in modified
        # Check that the rest is preserved
        assert "import os" in modified
        assert "import sys" in modified
        assert "'min': 5," in modified
        assert "def main():" in modified

    def test_directory_rejected(self, tmp_path: Path):
        """Test that directories are rejected."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "subdir",
            old_content="old",
            new_content="new",
        )

        assert result.success is False
        assert "not a file" in result.error.lower()

    def test_multiline_replacement(self, tmp_path: Path):
        """Test replacing multiline content."""
        file_path = tmp_path / "multi.py"
        original = (
            "def old_function():\n"
            "    return 42\n"
            "\n"
            "def other():\n"
            "    pass\n"
        )
        file_path.write_text(original)

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "multi.py",
            old_content="def old_function():\n    return 42",
            new_content="def new_function():\n    return 100",
        )

        assert result.success is True
        modified = file_path.read_text()
        assert "def new_function():" in modified
        assert "return 100" in modified
        assert "def other():" in modified

    def test_result_includes_evidence(self, tmp_path: Path):
        """Test that successful result includes evidence."""
        file_path = tmp_path / "test.py"
        file_path.write_text("value = 10\n")

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "test.py",
            old_content="value = 10",
            new_content="value = 20",
        )

        assert result.success is True
        assert result.old_content == "value = 10"
        assert result.new_content == "value = 20"
        assert result.path == "test.py"

    def test_nested_file_modification(self, tmp_path: Path):
        """Test modifying files in nested directories."""
        subdir = tmp_path / "src" / "config"
        subdir.mkdir(parents=True)
        file_path = subdir / "settings.py"
        file_path.write_text("DEBUG = True\n")

        tool = RepositoryModificationTool(tmp_path)
        result = tool.modify_file(
            "src/config/settings.py",
            old_content="DEBUG = True",
            new_content="DEBUG = False",
        )

        assert result.success is True
        assert file_path.read_text() == "DEBUG = False\n"
