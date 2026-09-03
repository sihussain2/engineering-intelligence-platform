"""Controlled test execution tool for the Engineering Intelligence Platform."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    """Result of test execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    summary: str  # Human-readable summary
    failure_type: Optional[str] = None  # "test_failure", "execution_error", "timeout"
    failed_tests: list[str] = field(default_factory=list)  # Names of failed tests
    passed_count: int = 0  # Number of passed tests
    failed_count: int = 0  # Number of failed tests

    def to_dict(self) -> dict:
        """Convert to dict for LLM consumption."""
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "summary": self.summary,
            "failure_type": self.failure_type,
            "failed_tests": self.failed_tests,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
        }


class TestExecutionTool:
    """Controlled test execution interface for a software repository."""

    def __init__(self, root: Path):
        """
        Initialize test execution tool.

        Args:
            root: Path to the repository root directory.
        """
        self.root = Path(root).resolve()

    def run_tests(self, test_path: Optional[str] = None) -> TestResult:
        """
        Execute the project's pytest test suite.

        Args:
            test_path: Optional repository-relative path to specific test file or directory.
                       If None, runs the entire test suite.

        Returns:
            TestResult with success status and test output details
        """
        # Resolve test path if provided
        if test_path:
            try:
                target = (self.root / test_path).resolve()
                if not target.is_relative_to(self.root):
                    return TestResult(
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr="Test path is outside the repository",
                        summary="Invalid test path",
                        failure_type="execution_error",
                    )
                pytest_target = test_path
            except (ValueError, OSError) as e:
                return TestResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Invalid test path: {str(e)}",
                    summary="Invalid test path",
                    failure_type="execution_error",
                )
        else:
            # Run all tests from repository root
            pytest_target = "tests"

        # Build pytest command
        cmd = ["python3", "-m", "pytest", pytest_target, "-v", "--tb=short"]

        # Execute test suite
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Test execution timed out after 120 seconds",
                summary="Test execution timed out",
                failure_type="timeout",
            )
        except Exception as e:
            return TestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Test execution failed: {str(e)}",
                summary="Test execution error",
                failure_type="execution_error",
            )

        # Parse results
        success = result.returncode == 0
        stdout = result.stdout
        stderr = result.stderr

        # Determine failure type and extract test counts
        failure_type = None if success else "test_failure"
        passed_count, failed_count, failed_tests = self._parse_test_output(stdout, stderr)

        # Generate summary from output
        summary = self._generate_summary(success, stdout, stderr, result.returncode)

        return TestResult(
            success=success,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            summary=summary,
            failure_type=failure_type,
            failed_tests=failed_tests,
            passed_count=passed_count,
            failed_count=failed_count,
        )

    @staticmethod
    def _parse_test_output(stdout: str, stderr: str) -> tuple[int, int, list[str]]:
        """
        Parse pytest output to extract test counts and failed test names.

        Returns:
            (passed_count, failed_count, list of failed test names)
        """
        passed_count = 0
        failed_count = 0
        failed_tests = []

        # Look for pytest summary line like "5 passed, 2 failed in 0.25s"
        summary_pattern = r"(\d+)\s+passed"
        passed_match = re.search(summary_pattern, stdout)
        if passed_match:
            passed_count = int(passed_match.group(1))

        summary_pattern = r"(\d+)\s+failed"
        failed_match = re.search(summary_pattern, stdout)
        if failed_match:
            failed_count = int(failed_match.group(1))

        # Extract failed test names from FAILED lines
        # Pattern: "FAILED path/to/test.py::TestClass::test_method - ..."
        failed_pattern = r"FAILED\s+([^\s]+(?:::[\w_]+)*)\s+"
        for match in re.finditer(failed_pattern, stdout):
            failed_tests.append(match.group(1))

        return passed_count, failed_count, failed_tests

    @staticmethod
    def _generate_summary(
        success: bool, stdout: str, stderr: str, exit_code: int
    ) -> str:
        """Generate a human-readable summary of test results."""
        if success:
            # Try to extract passed/failed counts from pytest output
            lines = stdout.split("\n")
            for line in reversed(lines):
                if "passed" in line:
                    return f"✓ Tests passed: {line.strip()}"
            return "✓ All tests passed"
        else:
            if stderr:
                first_error = stderr.split("\n")[0]
                return f"✗ Tests failed: {first_error[:100]}"
            # Try to extract failure info from stdout
            lines = stdout.split("\n")
            for line in reversed(lines):
                if "failed" in line or "error" in line:
                    return f"✗ {line.strip()[:100]}"
            return f"✗ Tests failed with exit code {exit_code}"
