"""Tests for SimpleAgent with new modification and test execution capabilities."""

from pathlib import Path

import pytest

from eip.repository.tool import RepositoryTool
from eip.llm.agent import SimpleAgent
from eip.llm.mock import MockLLMClient


class TestAgentWithModification:
    """Test agent with modification capability."""

    def test_agent_handles_modification_result(self, tmp_path: Path):
        """Test that agent can handle modification results."""
        file_path = tmp_path / "config.py"
        file_path.write_text("MAX = 10\n")

        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "I'll modify the config file.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "config.py",
                                "old_content": "MAX = 10",
                                "new_content": "MAX = 20",
                            },
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "File modified successfully. MAX is now 20.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Change MAX from 10 to 20")

        assert file_path.read_text() == "MAX = 20\n"
        assert "modified" in session.final_response.lower()

    def test_agent_continues_after_modification(self, tmp_path: Path):
        """Test that agent can continue reasoning after modification."""
        file_path = tmp_path / "test.py"
        file_path.write_text("value = 0\n")

        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "First, I'll modify the value.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "test.py",
                                "old_content": "value = 0",
                                "new_content": "value = 42",
                            },
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Now I'll verify by reading the file.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "test.py"},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Verified: value is now 42.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Modify and verify the value")

        assert file_path.read_text() == "value = 42\n"
        assert len(session.tool_results) >= 2
        assert "verified" in session.final_response.lower()

    def test_agent_handles_modification_error(self, tmp_path: Path):
        """Test that agent handles modification errors gracefully."""
        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "Attempting to modify a nonexistent file.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "nonexistent.py",
                                "old_content": "old",
                                "new_content": "new",
                            },
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Error: File does not exist.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Try to modify a file that doesn't exist")

        # Tool should have failed
        assert not all(r.success for r in session.tool_results)
        # But agent should have produced a response
        assert session.final_response is not None


class TestAgentWithTestExecution:
    """Test agent with test execution capability."""

    def test_agent_can_request_test_execution(self, tmp_path: Path):
        """Test that agent can request test execution."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_sample.py"
        test_file.write_text(
            "def test_pass():\n"
            "    assert True\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "I'll run the tests.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.run_tests",
                            "arguments": {},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Tests passed successfully.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Run the tests")

        # Should have executed tests
        assert any(r.tool_id == "repo.run_tests" for r in session.tool_results)
        assert "passed" in session.final_response.lower()

    def test_agent_receives_test_results(self, tmp_path: Path):
        """Test that agent receives complete test results."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_simple.py"
        test_file.write_text(
            "def test_one():\n"
            "    assert 1 + 1 == 2\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "Running tests...",
                    "tool_calls": [
                        {
                            "tool_id": "repo.run_tests",
                            "arguments": {},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Test results indicate success.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Run the tests and report")

        # Verify test tool result was captured
        test_results = [r for r in session.tool_results if r.tool_id == "repo.run_tests"]
        assert len(test_results) > 0
        # Result should contain test output
        assert test_results[0].result is not None

    def test_agent_modification_and_test_flow(self, tmp_path: Path):
        """Test agent modifying file and running tests."""
        # Create a file and test
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        config_file = src_dir / "config.py"
        config_file.write_text("THRESHOLD = 5\n")

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_config.py"
        test_file.write_text(
            "import sys\n"
            "sys.path.insert(0, 'src')\n"
            "from config import THRESHOLD\n"
            "def test_threshold():\n"
            "    assert THRESHOLD == 10\n"
        )

        init_file = tests_dir / "__init__.py"
        init_file.touch()

        repo = RepositoryTool(tmp_path)
        llm_client = MockLLMClient(
            [
                {
                    "content": "I'll modify the threshold.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "src/config.py",
                                "old_content": "THRESHOLD = 5",
                                "new_content": "THRESHOLD = 10",
                            },
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Now I'll run the tests.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.run_tests",
                            "arguments": {},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Modification complete and tests pass.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        agent = SimpleAgent(llm_client, repo)
        session = agent.run("Update threshold and verify tests pass")

        # Verify both operations occurred
        assert config_file.read_text() == "THRESHOLD = 10\n"
        assert len(session.tool_results) >= 2
        assert "complete" in session.final_response.lower()

    def test_agent_maintains_max_iterations(self, tmp_path: Path):
        """Test that agent respects max_iterations limit."""
        repo = RepositoryTool(tmp_path)

        # Create a mock that keeps requesting more turns
        def make_responses():
            for i in range(20):
                yield {
                    "content": f"Response {i}",
                    "tool_calls": [],
                    "done": False,  # Never signals done
                }

        llm_client = MockLLMClient(list(make_responses()))

        agent = SimpleAgent(llm_client, repo, max_iterations=5)
        session = agent.run("This will hit max iterations")

        # Should stop at max_iterations
        assert session.iterations == 5
