"""Tests for the RepositoryAnalyst component."""

from pathlib import Path

import pytest

from eip.analyst.analyzer import RepositoryAnalyst
from eip.analyst.result import Confidence, ComponentType, FileReference, ComponentInfo
from eip.repository.tool import RepositoryTool


class TestRepositoryAnalystBasic:
    """Tests for RepositoryAnalyst initialization and basic analysis."""

    def test_analyst_initialization(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        assert analyst.repository_tool is repo_tool
        assert analyst.llm_client is None

    def test_analyst_initialization_with_llm(self, tmp_path: Path):
        from eip.llm.mock import MockLLMClient

        repo_tool = RepositoryTool(tmp_path)
        llm = MockLLMClient()
        analyst = RepositoryAnalyst(repo_tool, llm_client=llm)

        assert analyst.repository_tool is repo_tool
        assert analyst.llm_client is llm

    def test_analyst_rejects_non_repository_tool(self):
        with pytest.raises(TypeError, match="repository_tool must be a RepositoryTool"):
            RepositoryAnalyst("not a tool")

    def test_analyze_basic_requirement(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        result = analyst.analyze("Add user authentication")

        assert result.requirement == "Add user authentication"
        assert result.repository_understanding is not None
        assert len(result.repository_understanding) > 0

    def test_analyze_rejects_empty_requirement(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        with pytest.raises(ValueError, match="requirement cannot be empty"):
            analyst.analyze("")

    def test_analyze_returns_valid_result(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        result = analyst.analyze("Implement feature X")

        assert result.requirement == "Implement feature X"
        assert result.impact_analysis is not None
        assert result.verification_plan is not None

    def test_analyze_with_python_project(self, tmp_path: Path):
        # Create a simple Python project structure
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (tmp_path / "README.md").write_text("# Test Project\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass\n")

        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        result = analyst.analyze("Add feature Y")

        # Verify repository understanding was generated
        understanding = result.repository_understanding
        assert "Python" in understanding or "items detected" in understanding

    def test_analyze_without_llm_returns_low_confidence(self, tmp_path: Path):
        """Without LLM, analysis should return low confidence baseline."""
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool, llm_client=None)

        result = analyst.analyze("New feature")

        # Baseline results should have low confidence
        assert result.confidence == Confidence.LOW

    def test_multiple_analyses_independent(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        analyst = RepositoryAnalyst(repo_tool)

        result1 = analyst.analyze("Feature 1")
        result2 = analyst.analyze("Feature 2")

        assert result1.requirement == "Feature 1"
        assert result2.requirement == "Feature 2"
        assert result1 is not result2
