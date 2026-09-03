"""Tests for agent failure recovery (Milestone 5)."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from eip.repository.tool import RepositoryTool
from eip.llm.agent import SimpleAgent, AgentSession
from eip.llm.dispatcher import ToolResult


class MockLLMClientFailureRecovery:
    """Mock LLM client that simulates a failure/recovery cycle."""

    def __init__(self, test_scenario: str = "simple"):
        self.test_scenario = test_scenario
        self.call_count = 0
        self.dispatcher = None

    def complete(self, messages, tools, system_prompt):
        """Simulate LLM responses for failure/recovery scenarios."""
        self.call_count += 1

        if self.test_scenario == "simple_recovery":
            # Scenario: Make a change, see it fail, then fix it
            if self.call_count == 1:
                # First call: inspect
                return {
                    "content": "I'll investigate and modify the implementation.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "src/config.py"},
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 2:
                # Second call: make modification
                return {
                    "content": "I'll change the value.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "src/config.py",
                                "old_content": "MAX = 10",
                                "new_content": "MAX = 20",
                            },
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 3:
                # Third call: run tests (will fail)
                return {
                    "content": "Running tests to verify.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.run_tests",
                            "arguments": {},
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 4:
                # Fourth call: diagnose failure and fix
                return {
                    "content": "Tests failed. I see the issue - let me fix it.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "tests/test_config.py"},
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 5:
                # Fifth call: apply fix
                return {
                    "content": "Applying the corrected modification.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "src/config.py",
                                "old_content": "MAX = 20",
                                "new_content": "MAX = 20",
                            },
                        }
                    ],
                    "done": False,
                }
            else:
                # Final: confirm success
                return {
                    "content": "Tests now pass. Requirement satisfied.",
                    "tool_calls": [],
                    "done": True,
                }

        return {"content": "Done", "tool_calls": [], "done": True}


class TestAgentRecoveryLoop:
    """Test agent's capability to recover from test failures."""

    def test_agent_session_tracks_test_status(self):
        """AgentSession should track whether tests passed."""
        session = AgentSession(requirement="test")
        assert session.tests_passed is None

        # Simulate recording a failed test result
        session.tests_passed = False
        assert session.tests_passed is False
        assert session.recovery_attempts == 0

    def test_agent_session_tracks_recovery_attempts(self):
        """AgentSession should count recovery attempts."""
        session = AgentSession(requirement="test")

        session.tests_passed = False
        session.recovery_attempts += 1
        assert session.recovery_attempts == 1

        session.recovery_attempts += 1
        assert session.recovery_attempts == 2

    def test_agent_session_tracks_modifications(self):
        """AgentSession should track which files were modified."""
        session = AgentSession(requirement="test")
        assert session.modifications_made == []

        session.record_modification("src/config.py")
        assert "src/config.py" in session.modifications_made

        # Duplicate modifications not recorded twice
        session.record_modification("src/config.py")
        assert session.modifications_made.count("src/config.py") == 1

    def test_agent_continues_after_test_failure(self, tmp_path: Path):
        """Agent should continue iterating after test failure."""
        # Create a minimal repo
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "src" / "config.py").write_text("MAX = 10")
        (tmp_path / "tests" / "test_config.py").write_text(
            "def test_max():\n    from src.config import MAX\n    assert MAX == 20"
        )

        repo_tool = RepositoryTool(tmp_path)
        llm_client = MockLLMClientFailureRecovery("simple_recovery")
        agent = SimpleAgent(llm_client, repo_tool, max_iterations=10)

        session = agent.run("Fix the MAX value")

        # Agent should have made multiple iterations
        assert session.iterations > 1
        # Agent should have attempted recovery
        assert session.recovery_attempts > 0 or session.iterations >= 4

    def test_agent_respects_max_iterations(self, tmp_path: Path):
        """Agent should respect max_iterations limit."""
        repo_tool = RepositoryTool(tmp_path)

        # Create an LLM that never signals done
        mock_llm = Mock()
        mock_llm.complete = Mock(
            return_value={"content": "continuing", "tool_calls": [], "done": False}
        )
        mock_llm.dispatcher = None

        agent = SimpleAgent(mock_llm, repo_tool, max_iterations=3)
        session = agent.run("test requirement")

        # Should stop at max_iterations
        assert session.iterations == 3

    def test_agent_records_last_response(self, tmp_path: Path):
        """Agent should record final response even if not explicitly marked done."""
        repo_tool = RepositoryTool(tmp_path)

        mock_llm = Mock()
        mock_llm.complete = Mock(
            return_value={"content": "Final response", "tool_calls": [], "done": False}
        )
        mock_llm.dispatcher = None

        agent = SimpleAgent(mock_llm, repo_tool, max_iterations=2)
        session = agent.run("test")

        # Should have a final response
        assert session.final_response is not None

    def test_verification_prompt_guides_diagnosis(self):
        """Verification prompt should guide failure diagnosis."""
        prompt = SimpleAgent._get_verification_prompt(
            "Change MAX from 10 to 20", is_first_iteration=True
        )

        # Should guide through workflow
        assert "WORKFLOW" in prompt
        assert "INVESTIGATE" in prompt
        assert "VERIFY" in prompt
        assert "FAIL" in prompt or "ITERATE" in prompt

    def test_continuation_prompt_emphasizes_recovery(self):
        """Continuation prompt should emphasize recovery strategy."""
        prompt = SimpleAgent._get_verification_prompt(
            "Change MAX from 10 to 20", is_first_iteration=False
        )

        # Should encourage diagnosis and fixing
        assert "diagnose" in prompt.lower() or "fix" in prompt.lower()
        assert "continue" in prompt.lower() or "iterate" in prompt.lower()


class TestVerificationModel:
    """Test the verification result model."""

    def test_engineering_result_status_enum(self):
        """EngineringResult should support different status values."""
        from eip.llm.verification import RequirementStatus

        assert RequirementStatus.SATISFIED.value == "satisfied"
        assert RequirementStatus.PARTIALLY_SATISFIED.value == "partially_satisfied"
        assert RequirementStatus.NOT_SATISFIED.value == "not_satisfied"
        assert RequirementStatus.VERIFICATION_INCOMPLETE.value == "verification_incomplete"

    def test_engineering_result_to_dict(self):
        """EngineringResult should serialize to dict."""
        from eip.llm.verification import (
            EngineringResult,
            RequirementStatus,
            ImplementationSummary,
            VerificationSummary,
            ReviewFindings,
        )

        result = EngineringResult(
            status=RequirementStatus.SATISFIED,
            requirement="Change MAX to 20",
            implementation=ImplementationSummary(
                files_changed=["src/config.py"],
                changes_description="Changed MAX from 10 to 20",
                modifications_attempted=1,
                iterations_required=1,
            ),
            verification=VerificationSummary(
                tests_passed=True,
                test_summary="All tests passed",
                passed_count=5,
                failed_count=0,
            ),
            review=ReviewFindings(
                requirement_addressed=True,
                implementation_correct=True,
            ),
        )

        result_dict = result.to_dict()
        assert result_dict["status"] == "satisfied"
        assert result_dict["implementation"]["files_changed"] == ["src/config.py"]
        assert result_dict["verification"]["tests_passed"] is True
