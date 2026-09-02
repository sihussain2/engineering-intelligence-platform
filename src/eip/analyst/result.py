"""Data structures for repository analysis results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Confidence(Enum):
    """Confidence level for analysis components."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class DependencyType(Enum):
    """Type of dependency."""

    INTERNAL = "internal"
    EXTERNAL = "external"
    STDLIB = "stdlib"


class RiskSeverity(Enum):
    """Severity level of identified risks."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComponentType(Enum):
    """Type of software component."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    INTERFACE = "interface"
    OTHER = "other"


@dataclass
class FileReference:
    """Reference to a file location."""

    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    def __post_init__(self):
        if not self.path:
            raise ValueError("path cannot be empty")
        if self.start_line is not None and self.end_line is not None:
            if self.start_line > self.end_line:
                raise ValueError("start_line must be <= end_line")


@dataclass
class ComponentInfo:
    """Information about a software component."""

    name: str
    component_type: ComponentType
    file_reference: FileReference
    description: str
    purpose: str
    complexity: int = 1  # 1-10 scale

    def __post_init__(self):
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not self.purpose:
            raise ValueError("purpose cannot be empty")
        if not (1 <= self.complexity <= 10):
            raise ValueError("complexity must be between 1 and 10")


@dataclass
class DependencyInfo:
    """Information about a dependency."""

    name: str
    dependency_type: DependencyType
    description: str
    required_version: Optional[str] = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")


@dataclass
class ImpactAnalysis:
    """Impact analysis for a requirement."""

    affected_files: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    affected_interfaces: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    scope: str = "unknown"  # "local", "module", "platform", "unknown"
    estimated_complexity: int = 1  # 1-10 scale

    def __post_init__(self):
        if not (1 <= self.estimated_complexity <= 10):
            raise ValueError("estimated_complexity must be between 1 and 10")
        if self.scope not in ("local", "module", "platform", "unknown"):
            raise ValueError(
                'scope must be "local", "module", "platform", or "unknown"'
            )


@dataclass
class Risk:
    """Identified risk."""

    description: str
    severity: RiskSeverity
    mitigation: str
    likelihood: int = 1  # 1-10 scale

    def __post_init__(self):
        if not self.description:
            raise ValueError("description cannot be empty")
        if not self.mitigation:
            raise ValueError("mitigation cannot be empty")
        if not (1 <= self.likelihood <= 10):
            raise ValueError("likelihood must be between 1 and 10")


@dataclass
class ImplementationStep:
    """Single step in implementation plan."""

    order: int
    title: str
    description: str
    affected_files: list[str] = field(default_factory=list)
    complexity: int = 1  # 1-10 scale

    def __post_init__(self):
        if self.order < 1:
            raise ValueError("order must be >= 1")
        if not self.title:
            raise ValueError("title cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not (1 <= self.complexity <= 10):
            raise ValueError("complexity must be between 1 and 10")


@dataclass
class VerificationPlan:
    """Plan for verifying and testing the implementation."""

    unit_tests: list[str] = field(default_factory=list)
    integration_tests: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    manual_tests: list[str] = field(default_factory=list)
    estimated_coverage: int = 0  # 0-100 scale


@dataclass
class RepositoryAnalystResult:
    """Complete analysis result for a software requirement."""

    requirement: str
    repository_understanding: str
    relevant_components: list[ComponentInfo] = field(default_factory=list)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    impact_analysis: ImpactAnalysis = field(default_factory=ImpactAnalysis)
    identified_risks: list[Risk] = field(default_factory=list)
    implementation_steps: list[ImplementationStep] = field(default_factory=list)
    verification_plan: VerificationPlan = field(default_factory=VerificationPlan)
    open_questions: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.UNKNOWN

    def __post_init__(self):
        if not self.requirement:
            raise ValueError("requirement cannot be empty")
        if not self.repository_understanding:
            raise ValueError("repository_understanding cannot be empty")

    def to_dict(self) -> dict:
        """Convert result to dictionary representation."""
        return {
            "requirement": self.requirement,
            "repository_understanding": self.repository_understanding,
            "relevant_components": [
                {
                    "name": c.name,
                    "component_type": c.component_type.value,
                    "file_reference": {
                        "path": c.file_reference.path,
                        "start_line": c.file_reference.start_line,
                        "end_line": c.file_reference.end_line,
                    },
                    "description": c.description,
                    "purpose": c.purpose,
                    "complexity": c.complexity,
                }
                for c in self.relevant_components
            ],
            "dependencies": [
                {
                    "name": d.name,
                    "dependency_type": d.dependency_type.value,
                    "description": d.description,
                    "required_version": d.required_version,
                }
                for d in self.dependencies
            ],
            "impact_analysis": {
                "affected_files": self.impact_analysis.affected_files,
                "affected_components": self.impact_analysis.affected_components,
                "affected_interfaces": self.impact_analysis.affected_interfaces,
                "breaking_changes": self.impact_analysis.breaking_changes,
                "scope": self.impact_analysis.scope,
                "estimated_complexity": self.impact_analysis.estimated_complexity,
            },
            "identified_risks": [
                {
                    "description": r.description,
                    "severity": r.severity.value,
                    "mitigation": r.mitigation,
                    "likelihood": r.likelihood,
                }
                for r in self.identified_risks
            ],
            "implementation_steps": [
                {
                    "order": s.order,
                    "title": s.title,
                    "description": s.description,
                    "affected_files": s.affected_files,
                    "complexity": s.complexity,
                }
                for s in self.implementation_steps
            ],
            "test_plan": {
                "unit_tests": self.verification_plan.unit_tests,
                "integration_tests": self.verification_plan.integration_tests,
                "edge_cases": self.verification_plan.edge_cases,
                "manual_tests": self.verification_plan.manual_tests,
                "estimated_coverage": self.verification_plan.estimated_coverage,
            },
            "open_questions": self.open_questions,
            "confidence": self.confidence.value,
        }
