"""Tests for repository analyst result data structures."""

from pathlib import Path

import pytest

from eip.analyst.result import (
    Confidence,
    ComponentInfo,
    ComponentType,
    DependencyInfo,
    DependencyType,
    FileReference,
    ImpactAnalysis,
    ImplementationStep,
    RepositoryAnalystResult,
    Risk,
    RiskSeverity,
    VerificationPlan,
)


class TestFileReference:
    """Tests for FileReference data structure."""

    def test_file_reference_creation(self):
        ref = FileReference(path="src/main.py")
        assert ref.path == "src/main.py"
        assert ref.start_line is None
        assert ref.end_line is None

    def test_file_reference_with_line_numbers(self):
        ref = FileReference(path="src/main.py", start_line=10, end_line=20)
        assert ref.path == "src/main.py"
        assert ref.start_line == 10
        assert ref.end_line == 20

    def test_file_reference_rejects_empty_path(self):
        with pytest.raises(ValueError, match="path cannot be empty"):
            FileReference(path="")

    def test_file_reference_rejects_invalid_line_range(self):
        with pytest.raises(ValueError, match="start_line must be <= end_line"):
            FileReference(path="src/main.py", start_line=20, end_line=10)


class TestComponentInfo:
    """Tests for ComponentInfo data structure."""

    def test_component_info_creation(self):
        ref = FileReference(path="src/analyzer.py")
        component = ComponentInfo(
            name="RepositoryAnalyst",
            component_type=ComponentType.CLASS,
            file_reference=ref,
            description="Main analysis component",
            purpose="Analyze requirements",
            complexity=5,
        )
        assert component.name == "RepositoryAnalyst"
        assert component.component_type == ComponentType.CLASS
        assert component.complexity == 5

    def test_component_info_rejects_empty_name(self):
        ref = FileReference(path="src/main.py")
        with pytest.raises(ValueError, match="name cannot be empty"):
            ComponentInfo(
                name="",
                component_type=ComponentType.CLASS,
                file_reference=ref,
                description="desc",
                purpose="purpose",
            )

    def test_component_info_rejects_invalid_complexity(self):
        ref = FileReference(path="src/main.py")
        with pytest.raises(ValueError, match="complexity must be between 1 and 10"):
            ComponentInfo(
                name="Test",
                component_type=ComponentType.CLASS,
                file_reference=ref,
                description="desc",
                purpose="purpose",
                complexity=11,
            )


class TestDependencyInfo:
    """Tests for DependencyInfo data structure."""

    def test_dependency_info_creation(self):
        dep = DependencyInfo(
            name="pytest",
            dependency_type=DependencyType.EXTERNAL,
            description="Testing framework",
            required_version=">=9.0",
        )
        assert dep.name == "pytest"
        assert dep.dependency_type == DependencyType.EXTERNAL
        assert dep.required_version == ">=9.0"

    def test_dependency_info_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            DependencyInfo(
                name="",
                dependency_type=DependencyType.EXTERNAL,
                description="desc",
            )


class TestImpactAnalysis:
    """Tests for ImpactAnalysis data structure."""

    def test_impact_analysis_default(self):
        impact = ImpactAnalysis()
        assert impact.affected_files == []
        assert impact.scope == "unknown"
        assert impact.estimated_complexity == 1

    def test_impact_analysis_with_data(self):
        impact = ImpactAnalysis(
            affected_files=["src/main.py", "tests/test_main.py"],
            scope="module",
            estimated_complexity=7,
        )
        assert len(impact.affected_files) == 2
        assert impact.scope == "module"
        assert impact.estimated_complexity == 7

    def test_impact_analysis_rejects_invalid_scope(self):
        with pytest.raises(ValueError, match='scope must be "local"'):
            ImpactAnalysis(scope="invalid")


class TestRisk:
    """Tests for Risk data structure."""

    def test_risk_creation(self):
        risk = Risk(
            description="Performance degradation",
            severity=RiskSeverity.HIGH,
            mitigation="Add caching layer",
            likelihood=7,
        )
        assert risk.description == "Performance degradation"
        assert risk.severity == RiskSeverity.HIGH
        assert risk.likelihood == 7

    def test_risk_rejects_invalid_likelihood(self):
        with pytest.raises(ValueError, match="likelihood must be between 1 and 10"):
            Risk(
                description="test",
                severity=RiskSeverity.LOW,
                mitigation="mitigation",
                likelihood=11,
            )


class TestImplementationStep:
    """Tests for ImplementationStep data structure."""

    def test_implementation_step_creation(self):
        step = ImplementationStep(
            order=1,
            title="Setup database",
            description="Create schema and migrations",
            affected_files=["src/db.py", "migrations/001_init.sql"],
            complexity=4,
        )
        assert step.order == 1
        assert step.title == "Setup database"
        assert len(step.affected_files) == 2
        assert step.complexity == 4

    def test_implementation_step_rejects_invalid_order(self):
        with pytest.raises(ValueError, match="order must be >= 1"):
            ImplementationStep(
                order=0,
                title="test",
                description="desc",
            )

    def test_implementation_step_rejects_empty_title(self):
        with pytest.raises(ValueError, match="title cannot be empty"):
            ImplementationStep(
                order=1,
                title="",
                description="desc",
            )


class TestVerificationPlan:
    """Tests for VerificationPlan data structure."""

    def test_verification_plan_default(self):
        plan = VerificationPlan()
        assert plan.unit_tests == []
        assert plan.integration_tests == []
        assert plan.estimated_coverage == 0

    def test_verification_plan_with_tests(self):
        plan = VerificationPlan(
            unit_tests=["test_analyzer", "test_result"],
            integration_tests=["test_e2e"],
            estimated_coverage=85,
        )
        assert len(plan.unit_tests) == 2
        assert len(plan.integration_tests) == 1
        assert plan.estimated_coverage == 85


class TestRepositoryAnalystResult:
    """Tests for RepositoryAnalystResult data structure."""

    def test_result_creation_minimal(self):
        result = RepositoryAnalystResult(
            requirement="Add user authentication",
            repository_understanding="Python project with Flask",
        )
        assert result.requirement == "Add user authentication"
        assert result.repository_understanding == "Python project with Flask"
        assert result.confidence == Confidence.UNKNOWN
        assert result.relevant_components == []
        assert result.identified_risks == []

    def test_result_creation_full(self):
        ref = FileReference(path="src/auth.py")
        component = ComponentInfo(
            name="AuthModule",
            component_type=ComponentType.MODULE,
            file_reference=ref,
            description="Authentication",
            purpose="Handle user auth",
        )
        risk = Risk(
            description="Security vulnerability",
            severity=RiskSeverity.CRITICAL,
            mitigation="Implement input validation",
        )
        step = ImplementationStep(
            order=1,
            title="Design schema",
            description="Create auth tables",
        )

        result = RepositoryAnalystResult(
            requirement="Add authentication",
            repository_understanding="Python Flask app",
            relevant_components=[component],
            identified_risks=[risk],
            implementation_steps=[step],
            confidence=Confidence.HIGH,
        )

        assert len(result.relevant_components) == 1
        assert len(result.identified_risks) == 1
        assert len(result.implementation_steps) == 1
        assert result.confidence == Confidence.HIGH

    def test_result_rejects_empty_requirement(self):
        with pytest.raises(ValueError, match="requirement cannot be empty"):
            RepositoryAnalystResult(
                requirement="",
                repository_understanding="test",
            )

    def test_result_to_dict(self):
        result = RepositoryAnalystResult(
            requirement="Test requirement",
            repository_understanding="Test repo",
            confidence=Confidence.MEDIUM,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["requirement"] == "Test requirement"
        assert result_dict["confidence"] == "medium"
        assert isinstance(result_dict["relevant_components"], list)
        assert isinstance(result_dict["impact_analysis"], dict)
        assert isinstance(result_dict["test_plan"], dict)

    def test_result_to_dict_with_complex_data(self):
        ref = FileReference(path="src/main.py", start_line=10, end_line=20)
        component = ComponentInfo(
            name="MainClass",
            component_type=ComponentType.CLASS,
            file_reference=ref,
            description="Main component",
            purpose="Core functionality",
            complexity=7,
        )
        dep = DependencyInfo(
            name="requests",
            dependency_type=DependencyType.EXTERNAL,
            description="HTTP library",
        )
        risk = Risk(
            description="Test risk",
            severity=RiskSeverity.MEDIUM,
            mitigation="Test mitigation",
        )

        result = RepositoryAnalystResult(
            requirement="Complex requirement",
            repository_understanding="Complex repo",
            relevant_components=[component],
            dependencies=[dep],
            identified_risks=[risk],
        )

        result_dict = result.to_dict()

        assert len(result_dict["relevant_components"]) == 1
        assert result_dict["relevant_components"][0]["name"] == "MainClass"
        assert result_dict["relevant_components"][0]["component_type"] == "class"
        assert result_dict["relevant_components"][0]["file_reference"]["path"] == "src/main.py"
        assert result_dict["relevant_components"][0]["file_reference"]["start_line"] == 10

        assert len(result_dict["dependencies"]) == 1
        assert result_dict["dependencies"][0]["name"] == "requests"

        assert len(result_dict["identified_risks"]) == 1
        assert result_dict["identified_risks"][0]["severity"] == "medium"
