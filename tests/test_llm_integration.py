"""Tests for LLM tool calling and agent loop."""

from pathlib import Path

import pytest

from eip.repository.tool import RepositoryTool
from eip.llm.dispatcher import ToolCall, ToolDispatcher
from eip.llm.agent import SimpleAgent
from eip.llm.mock import MockLLMClient, ConversationalMockLLM


class TestToolDispatcher:
    """Tests for ToolDispatcher."""

    def test_dispatcher_initialization(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        assert dispatcher.repository_tool is repo_tool

    def test_dispatcher_rejects_non_repository_tool(self):
        with pytest.raises(TypeError):
            ToolDispatcher("not a tool")

    def test_get_tools_returns_three_tools(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        tools = dispatcher.get_tools()

        # Now returns 5 tools: 3 read + 1 write + 1 execute
        assert len(tools) == 5
        assert any(t["tool_id"] == "repo.list_files" for t in tools)
        assert any(t["tool_id"] == "repo.read_file" for t in tools)
        assert any(t["tool_id"] == "repo.search_code" for t in tools)
        assert any(t["tool_id"] == "repo.modify_file" for t in tools)
        assert any(t["tool_id"] == "repo.run_tests" for t in tools)

    def test_execute_list_files(self, tmp_path: Path):
        (tmp_path / "file1.py").write_text("x = 1")
        (tmp_path / "file2.py").write_text("y = 2")

        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        call = ToolCall(tool_id="repo.list_files", arguments={"path": "."})
        result = dispatcher.execute_call(call)

        assert result.success
        assert isinstance(result.result, list)
        assert "file1.py" in result.result
        assert "file2.py" in result.result

    def test_execute_read_file(self, tmp_path: Path):
        (tmp_path / "test.txt").write_text("hello world")

        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        call = ToolCall(tool_id="repo.read_file", arguments={"path": "test.txt"})
        result = dispatcher.execute_call(call)

        assert result.success
        assert result.result == "hello world"

    def test_execute_read_file_requires_path(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        call = ToolCall(tool_id="repo.read_file", arguments={})
        result = dispatcher.execute_call(call)

        assert not result.success
        assert "path" in result.error.lower()

    def test_execute_search_code(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def hello():\n    pass")
        (tmp_path / "config.py").write_text("DEBUG = True")

        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        call = ToolCall(
            tool_id="repo.search_code",
            arguments={"query": "def", "max_results": 10},
        )
        result = dispatcher.execute_call(call)

        assert result.success
        assert len(result.result) == 1
        assert result.result[0]["file"] == "app.py"

    def test_execute_unknown_tool(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        call = ToolCall(tool_id="unknown.tool", arguments={})
        result = dispatcher.execute_call(call)

        assert not result.success
        assert "Unknown tool" in result.error

    def test_execute_tool_with_error(self, tmp_path: Path):
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        # Try to read file that doesn't exist
        call = ToolCall(tool_id="repo.read_file", arguments={"path": "nonexistent.txt"})
        result = dispatcher.execute_call(call)

        assert not result.success
        assert result.error is not None


class TestToolResult:
    """Tests for ToolResult message formatting."""

    def test_tool_result_success_message(self):
        from eip.llm.dispatcher import ToolResult

        result = ToolResult(tool_id="repo.list_files", success=True, result=["a", "b"])
        msg = result.to_llm_message()

        assert msg["role"] == "tool"
        assert msg["tool_use_id"] == "repo.list_files"
        assert "a" in msg["content"]
        assert "b" in msg["content"]

    def test_tool_result_error_message(self):
        from eip.llm.dispatcher import ToolResult

        result = ToolResult(
            tool_id="repo.read_file",
            success=False,
            error="File not found",
        )
        msg = result.to_llm_message()

        assert msg["role"] == "tool"
        assert "Error" in msg["content"]


class TestSimpleAgent:
    """Tests for SimpleAgent loop."""

    def test_agent_initialization(self, tmp_path: Path):
        mock_llm = MockLLMClient()
        repo_tool = RepositoryTool(tmp_path)

        agent = SimpleAgent(mock_llm, repo_tool)

        assert agent.llm_client is mock_llm
        assert agent.dispatcher.repository_tool is repo_tool

    def test_agent_single_turn_no_tools(self, tmp_path: Path):
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "The repository looks good.",
                    "tool_calls": [],
                    "done": True,
                }
            ]
        )
        repo_tool = RepositoryTool(tmp_path)
        agent = SimpleAgent(mock_llm, repo_tool)

        session = agent.run("Analyze the repository")

        assert session.requirement == "Analyze the repository"
        assert session.final_response == "The repository looks good."
        assert session.iterations == 1

    def test_agent_tool_call_single_turn(self, tmp_path: Path):
        (tmp_path / "file.py").write_text("x = 1")

        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "Let me list the files.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.list_files",
                            "arguments": {"path": "."},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Found files: file.py",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )
        repo_tool = RepositoryTool(tmp_path)
        agent = SimpleAgent(mock_llm, repo_tool)

        session = agent.run("List repository files")

        assert session.iterations == 2
        assert len(session.tool_results) == 1
        assert session.tool_results[0].success
        assert "file.py" in session.tool_results[0].result

    def test_agent_multi_turn_with_multiple_tools(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("def main():\n    pass")

        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "Searching for functions...",
                    "tool_calls": [
                        {
                            "tool_id": "repo.search_code",
                            "arguments": {"query": "def"},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Now reading the file...",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "app.py"},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "Analysis complete.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )
        repo_tool = RepositoryTool(tmp_path)
        agent = SimpleAgent(mock_llm, repo_tool)

        session = agent.run("Analyze the code")

        assert session.iterations == 3
        assert len(session.tool_results) == 2
        assert session.tool_results[0].success  # search_code
        assert session.tool_results[1].success  # read_file

    def test_agent_handles_tool_errors(self, tmp_path: Path):
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "Trying to read a file...",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "nonexistent.txt"},
                        }
                    ],
                    "done": False,
                },
                {
                    "content": "That file doesn't exist.",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )
        repo_tool = RepositoryTool(tmp_path)
        agent = SimpleAgent(mock_llm, repo_tool)

        session = agent.run("Find a file")

        assert len(session.tool_results) == 1
        assert not session.tool_results[0].success
        assert session.tool_results[0].error is not None

    def test_agent_max_iterations(self, tmp_path: Path):
        # LLM that never signals done
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": f"Response {i}",
                    "tool_calls": [],
                    "done": False,
                }
                for i in range(15)  # More than default max_iterations
            ]
        )
        repo_tool = RepositoryTool(tmp_path)
        agent = SimpleAgent(mock_llm, repo_tool, max_iterations=5)

        session = agent.run("Test")

        assert session.iterations == 5  # Stopped at max

    def test_agent_with_conversational_mock(self, tmp_path: Path):
        (tmp_path / "example.py").write_text("class Example:\n    pass")
        (tmp_path / "src").mkdir()

        repo_tool = RepositoryTool(tmp_path)
        mock_llm = ConversationalMockLLM()
        agent = SimpleAgent(mock_llm, repo_tool)

        session = agent.run("Analyze this repository")

        assert session.iterations >= 2
        assert len(session.tool_results) >= 1
        # First result should be from search_code
        assert session.tool_results[0].tool_id == "repo.search_code"
        # Tool should have succeeded
        assert session.tool_results[0].success


class TestMockLLMs:
    """Tests for mock LLM implementations."""

    def test_mock_llm_canned_responses(self):
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "First response",
                    "tool_calls": [],
                    "done": False,
                },
                {
                    "content": "Second response",
                    "tool_calls": [],
                    "done": True,
                },
            ]
        )

        resp1 = mock_llm.complete([], [])
        assert resp1["content"] == "First response"

        resp2 = mock_llm.complete([], [])
        assert resp2["content"] == "Second response"

    def test_mock_llm_exhaustion(self):
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "Only response",
                    "tool_calls": [],
                    "done": True,
                }
            ]
        )

        mock_llm.complete([], [])

        with pytest.raises(IndexError):
            mock_llm.complete([], [])

    def test_mock_llm_reset(self):
        mock_llm = MockLLMClient(
            responses=[
                {
                    "content": "Response",
                    "tool_calls": [],
                    "done": True,
                }
            ]
        )

        mock_llm.complete([], [])
        mock_llm.reset()

        resp = mock_llm.complete([], [])
        assert resp["content"] == "Response"

    def test_conversational_mock_turns(self):
        mock_llm = ConversationalMockLLM()

        resp1 = mock_llm.complete([], [])
        assert "search" in resp1["content"].lower()
        assert len(resp1["tool_calls"]) == 1

        resp2 = mock_llm.complete([], [])
        assert "examine" in resp2["content"].lower()
        assert len(resp2["tool_calls"]) == 1

        resp3 = mock_llm.complete([], [])
        assert resp3["done"] is True
