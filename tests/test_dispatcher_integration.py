"""Tests for dispatcher integration with new tools."""

from pathlib import Path

import pytest

from eip.repository.tool import RepositoryTool
from eip.llm.dispatcher import ToolDispatcher, ToolCall


class TestDispatcherIntegration:
    """Test dispatcher integration with new tools."""

    def test_dispatcher_has_modify_file_tool(self, tmp_path: Path):
        """Test that modify_file tool is available."""
        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)
        tools = dispatcher.get_tools()

        tool_ids = [t["tool_id"] for t in tools]
        assert "repo.modify_file" in tool_ids

    def test_dispatcher_has_run_tests_tool(self, tmp_path: Path):
        """Test that run_tests tool is available."""
        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)
        tools = dispatcher.get_tools()

        tool_ids = [t["tool_id"] for t in tools]
        assert "repo.run_tests" in tool_ids

    def test_modify_file_routed_correctly(self, tmp_path: Path):
        """Test that modify_file calls are routed correctly."""
        file_path = tmp_path / "config.py"
        file_path.write_text("MAX = 10\n")

        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        call = ToolCall(
            tool_id="repo.modify_file",
            arguments={
                "path": "config.py",
                "old_content": "MAX = 10",
                "new_content": "MAX = 20",
            },
        )

        result = dispatcher.execute_call(call)

        assert result.success is True
        assert file_path.read_text() == "MAX = 20\n"

    def test_modify_file_failure_routed_correctly(self, tmp_path: Path):
        """Test that modify_file failures are handled correctly."""
        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        call = ToolCall(
            tool_id="repo.modify_file",
            arguments={
                "path": "nonexistent.py",
                "old_content": "old",
                "new_content": "new",
            },
        )

        result = dispatcher.execute_call(call)

        assert result.success is False
        assert result.error is not None

    def test_run_tests_routed_correctly(self, tmp_path: Path):
        """Test that run_tests calls are routed correctly."""
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
        dispatcher = ToolDispatcher(repo)

        call = ToolCall(
            tool_id="repo.run_tests",
            arguments={},
        )

        result = dispatcher.execute_call(call)

        assert result.success is True
        assert result.result is not None
        assert "success" in result.result

    def test_modify_file_missing_argument(self, tmp_path: Path):
        """Test that modify_file with missing arguments returns error."""
        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        call = ToolCall(
            tool_id="repo.modify_file",
            arguments={
                "path": "config.py",
                # Missing old_content and new_content
            },
        )

        result = dispatcher.execute_call(call)

        assert result.success is False
        assert "required" in result.error.lower()

    def test_unknown_tool_rejected(self, tmp_path: Path):
        """Test that unknown tools are rejected."""
        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        call = ToolCall(
            tool_id="unknown.tool",
            arguments={},
        )

        result = dispatcher.execute_call(call)

        assert result.success is False
        assert "unknown" in result.error.lower()

    def test_all_read_tools_still_available(self, tmp_path: Path):
        """Test that read tools are still available."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello")

        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        tools = dispatcher.get_tools()
        tool_ids = [t["tool_id"] for t in tools]

        assert "repo.list_files" in tool_ids
        assert "repo.read_file" in tool_ids
        assert "repo.search_code" in tool_ids

    def test_read_operations_still_work(self, tmp_path: Path):
        """Test that read operations still work through dispatcher."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def test():\n    pass\n")

        repo = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo)

        # Test list_files
        list_call = ToolCall(
            tool_id="repo.list_files",
            arguments={"path": "."},
        )
        list_result = dispatcher.execute_call(list_call)
        assert list_result.success is True

        # Test read_file
        read_call = ToolCall(
            tool_id="repo.read_file",
            arguments={"path": "test.py"},
        )
        read_result = dispatcher.execute_call(read_call)
        assert read_result.success is True
        assert "def test():" in read_result.result

        # Test search_code
        search_call = ToolCall(
            tool_id="repo.search_code",
            arguments={"query": "def test"},
        )
        search_result = dispatcher.execute_call(search_call)
        assert search_result.success is True
