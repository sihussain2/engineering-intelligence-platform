"""Verification and requirement evaluation for engineering tasks."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class RequirementStatus(Enum):
    """Status of requirement satisfaction."""

    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    NOT_SATISFIED = "not_satisfied"
    VERIFICATION_INCOMPLETE = "verification_incomplete"


@dataclass
class ImplementationSummary:
    """Summary of implementation changes."""

    files_changed: list[str] = field(default_factory=list)
    changes_description: str = ""
    modifications_attempted: int = 0
    iterations_required: int = 0


@dataclass
class VerificationSummary:
    """Summary of verification results."""

    tests_passed: bool = False
    test_summary: str = ""
    total_tests_run: int = 0
    passed_count: int = 0
    failed_count: int = 0
    failures_diagnosed: list[str] = field(default_factory=list)
    recovery_attempts: int = 0


@dataclass
class ReviewFindings:
    """Review findings about the implementation."""

    requirement_addressed: bool = False
    implementation_correct: bool = False
    test_coverage_adequate: bool = False
    risks: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EngineringResult:
    """Final structured result of an engineering task."""

    status: RequirementStatus
    requirement: str
    implementation: ImplementationSummary
    verification: VerificationSummary
    review: ReviewFindings
    evidence: str = ""  # Free-form evidence supporting the conclusion
    agent_reasoning: str = ""  # Agent's final reasoning

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "requirement": self.requirement,
            "implementation": {
                "files_changed": self.implementation.files_changed,
                "changes_description": self.implementation.changes_description,
                "modifications_attempted": self.implementation.modifications_attempted,
                "iterations_required": self.implementation.iterations_required,
            },
            "verification": {
                "tests_passed": self.verification.tests_passed,
                "test_summary": self.verification.test_summary,
                "total_tests_run": self.verification.total_tests_run,
                "passed_count": self.verification.passed_count,
                "failed_count": self.verification.failed_count,
                "failures_diagnosed": self.verification.failures_diagnosed,
                "recovery_attempts": self.verification.recovery_attempts,
            },
            "review": {
                "requirement_addressed": self.review.requirement_addressed,
                "implementation_correct": self.review.implementation_correct,
                "test_coverage_adequate": self.review.test_coverage_adequate,
                "risks": self.review.risks,
                "limitations": self.review.limitations,
                "recommendations": self.review.recommendations,
            },
            "evidence": self.evidence,
            "agent_reasoning": self.agent_reasoning,
        }
