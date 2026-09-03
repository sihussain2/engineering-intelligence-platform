"""Tests for TestExecutionTool."""

from pathlib import Path

import pytest

from eip.repository.execution import TestExecutionTool


class TestTestExecutionTool:
    """Test controlled test execution."""

    def test_run_tests_success(self, tmp_path: Path):
        """Test successful test execution."""
        # Create a minimal test file
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_sample.py"
        test_file.write_text(
            "def test_pass():\n"
            "    assert 1 + 1 == 2\n"
        )

        # Create minimal setup for pytest
        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        assert result.success is True
        assert result.exit_code == 0
        assert "passed" in result.stdout.lower()

    def test_run_tests_failure(self, tmp_path: Path):
        """Test test execution with failures."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_fail.py"
        test_file.write_text(
            "def test_fail():\n"
            "    assert 1 + 1 == 3\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        assert result.success is False
        assert result.exit_code != 0
        assert result.summary.startswith("✗")

    def test_run_specific_test_file(self, tmp_path: Path):
        """Test running a specific test file."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        # Create multiple test files
        test1 = tests_dir / "test_one.py"
        test1.write_text(
            "def test_one():\n"
            "    assert True\n"
        )

        test2 = tests_dir / "test_two.py"
        test2.write_text(
            "def test_two():\n"
            "    assert False\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        # Run only the passing test
        result = tool.run_tests("tests/test_one.py")

        assert result.success is True
        assert result.exit_code == 0

    def test_invalid_test_path_outside_repo(self, tmp_path: Path):
        """Test that test paths outside repo are rejected."""
        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("../../../etc/passwd")

        assert result.success is False
        assert "outside the repository" in result.stderr.lower()

    def test_result_captures_output(self, tmp_path: Path):
        """Test that stdout/stderr are captured."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_output.py"
        test_file.write_text(
            "def test_with_output():\n"
            "    print('Test output')\n"
            "    assert True\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        assert result.stdout is not None
        assert isinstance(result.stderr, str)
        assert isinstance(result.summary, str)

    def test_result_summary_success(self, tmp_path: Path):
        """Test that success summary is generated."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_pass.py"
        test_file.write_text(
            "def test_pass():\n"
            "    assert True\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        assert result.success is True
        assert result.summary.startswith("✓")
        assert "passed" in result.summary.lower()

    def test_result_summary_failure(self, tmp_path: Path):
        """Test that failure summary is generated."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_fail.py"
        test_file.write_text(
            "def test_fail():\n"
            "    assert False\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        assert result.success is False
        assert result.summary.startswith("✗")

    def test_result_to_dict(self, tmp_path: Path):
        """Test that result can be converted to dict."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_dict.py"
        test_file.write_text(
            "def test_dict():\n"
            "    assert True\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests()

        result_dict = result.to_dict()
        assert "success" in result_dict
        assert "exit_code" in result_dict
        assert "stdout" in result_dict
        assert "stderr" in result_dict
        assert "summary" in result_dict

    def test_nonexistent_test_path(self, tmp_path: Path):
        """Test running tests from a nonexistent path."""
        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("tests/nonexistent.py")

        # pytest will fail with exit code != 0
        assert result.success is False
        assert result.exit_code != 0
