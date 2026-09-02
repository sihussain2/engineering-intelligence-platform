"""Repository analyst component for requirements analysis."""

from eip.repository.tool import RepositoryTool
from eip.analyst.result import (
    RepositoryAnalystResult,
    Confidence,
    ImpactAnalysis,
    VerificationPlan,
)


class RepositoryAnalyst:
    """
    Analyzes software requirements against a repository.

    Currently provides a skeleton for manual analysis. Future versions will
    integrate with LLM providers and autonomous exploration strategies.
    """

    def __init__(self, repository_tool: RepositoryTool):
        """
        Initialize the analyst with a repository tool.

        Args:
            repository_tool: RepositoryTool instance for repository access.
        """
        if not isinstance(repository_tool, RepositoryTool):
            raise TypeError("repository_tool must be a RepositoryTool instance")
        self.repository_tool = repository_tool

    def analyze(self, requirement: str) -> RepositoryAnalystResult:
        """
        Analyze a software requirement against the repository.

        Args:
            requirement: Description of the software requirement.

        Returns:
            RepositoryAnalystResult with analysis findings.

        Raises:
            ValueError: If requirement is empty.
        """
        if not requirement:
            raise ValueError("requirement cannot be empty")

        # Generate placeholder understanding by exploring repository structure
        repo_understanding = self._generate_repository_understanding()

        # Create baseline result
        result = RepositoryAnalystResult(
            requirement=requirement,
            repository_understanding=repo_understanding,
            impact_analysis=ImpactAnalysis(),
            verification_plan=VerificationPlan(),
            confidence=Confidence.LOW,
        )

        return result

    def _generate_repository_understanding(self) -> str:
        """
        Generate initial understanding of the repository.

        Returns:
            String description of repository structure and purpose.
        """
        try:
            # Try to read project metadata
            files = self.repository_tool.list_files()
            file_count = len(files)

            # Look for key files
            has_readme = any("README" in f for f in files)
            has_pyproject = any("pyproject.toml" in f for f in files)
            has_tests = any("tests" in f for f in files)

            understanding = f"Repository structure: {file_count} items detected. "
            if has_readme:
                understanding += "README found. "
            if has_pyproject:
                understanding += "Python project (pyproject.toml found). "
            if has_tests:
                understanding += "Test suite present. "

            understanding += "Detailed analysis requires LLM integration."

            return understanding
        except Exception as e:
            return f"Repository exploration attempted. Error: {str(e)}"
