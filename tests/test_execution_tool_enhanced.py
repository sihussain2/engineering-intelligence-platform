"""Tests for test execution tool enhancements (Milestone 5)."""

import pytest
from pathlib import Path
from eip.repository.execution import TestExecutionTool, TestResult


class TestTestResultEnhanced:
    """Test enhanced TestResult model with failure diagnostics."""

    def test_result_has_failure_type(self):
        """TestResult should capture failure type."""
        result = TestResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="",
            summary="Test failed",
            failure_type="test_failure",
        )
        assert result.failure_type == "test_failure"

    def test_result_distinguishes_timeout(self):
        """TestResult should distinguish timeout failures."""
        result = TestResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="Timeout",
            summary="Test timed out",
            failure_type="timeout",
        )
        assert result.failure_type == "timeout"

    def test_result_captures_test_counts(self):
        """TestResult should capture passed/failed counts."""
        result = TestResult(
            success=False,
            exit_code=1,
            stdout="5 passed, 2 failed",
            stderr="",
            summary="2 tests failed",
            failure_type="test_failure",
            passed_count=5,
            failed_count=2,
        )
        assert result.passed_count == 5
        assert result.failed_count == 2

    def test_result_tracks_failed_tests(self):
        """TestResult should track which tests failed."""
        result = TestResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="",
            summary="test_max_items failed",
            failure_type="test_failure",
            failed_tests=["tests/test_config.py::test_max_items"],
        )
        assert "tests/test_config.py::test_max_items" in result.failed_tests

    def test_result_to_dict_includes_diagnostics(self):
        """to_dict should include failure diagnostics."""
        result = TestResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="",
            summary="Test failed",
            failure_type="test_failure",
            passed_count=3,
            failed_count=1,
            failed_tests=["tests/test_app.py::test_feature"],
        )
        result_dict = result.to_dict()
        assert result_dict["failure_type"] == "test_failure"
        assert result_dict["passed_count"] == 3
        assert result_dict["failed_count"] == 1
        assert "test_feature" in result_dict["failed_tests"][0]


class TestExecutionToolEnhanced:
    """Test enhanced TestExecutionTool with better diagnostics."""

    def test_execution_tool_returns_failure_type_on_test_failure(self, tmp_path: Path):
        """TestExecutionTool should return failure_type on test failure."""
        # Create a simple test file that fails
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_fail.py"
        test_file.write_text(
            """
def test_failure():
    assert False, "This test always fails"
"""
        )

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("tests/test_fail.py")

        assert result.success is False
        assert result.failure_type == "test_failure"
        assert result.failed_count == 1

    def test_execution_tool_parses_test_counts(self, tmp_path: Path):
        """TestExecutionTool should extract test counts from output."""
        # Create tests: 2 pass, 1 fails
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_mixed.py"
        test_file.write_text(
            """
def test_pass_1():
    assert True

def test_pass_2():
    assert True

def test_fail():
    assert False
"""
        )

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("tests/test_mixed.py")

        assert result.success is False
        assert result.passed_count == 2
        assert result.failed_count == 1

    def test_execution_tool_identifies_failed_tests(self, tmp_path: Path):
        """TestExecutionTool should identify which tests failed."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_identify.py"
        test_file.write_text(
            """
def test_works():
    assert True

def test_breaks():
    assert False
"""
        )

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("tests/test_identify.py")

        assert result.success is False
        assert len(result.failed_tests) > 0
        # Should identify the specific failing test
        assert any("test_breaks" in name for name in result.failed_tests)

    def test_timeout_has_correct_failure_type(self, tmp_path: Path):
        """Timeout should have failure_type='timeout'."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_timeout.py"
        test_file.write_text(
            """
import time
def test_hangs():
    time.sleep(150)  # Longer than 120s timeout
"""
        )

        tool = TestExecutionTool(tmp_path)
        result = tool.run_tests("tests/test_timeout.py")

        assert result.success is False
        assert result.failure_type == "timeout"
