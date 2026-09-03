"""Controlled test execution tool for the Engineering Intelligence Platform."""

import subprocess
from dataclasses import dataclass
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

    def to_dict(self) -> dict:
        """Convert to dict for LLM consumption."""
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "summary": self.summary,
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
                    )
                pytest_target = test_path
            except (ValueError, OSError) as e:
                return TestResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Invalid test path: {str(e)}",
                    summary="Invalid test path",
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
            )
        except Exception as e:
            return TestResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Test execution failed: {str(e)}",
                summary="Test execution error",
            )

        # Parse results
        success = result.returncode == 0
        stdout = result.stdout
        stderr = result.stderr

        # Generate summary from output
        summary = self._generate_summary(success, stdout, stderr, result.returncode)

        return TestResult(
            success=success,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            summary=summary,
        )

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
