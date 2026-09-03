"""Unit tests for GitHub Copilot SDK adapter."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eip.llm.copilot import CopilotLLMClient


class TestCopilotLLMClientInitialization:
    """Test CopilotLLMClient initialization."""

    def test_client_initialization_with_default_model(self):
        """Client initializes with default Claude Haiku 4.5 model."""
        with patch.dict(os.environ, {}, clear=True):
            client = CopilotLLMClient()
            assert client.model == "claude-haiku-4.5"
            assert client.github_token is None
            assert client.working_directory is None

    def test_client_initialization_with_custom_model(self):
        """Client accepts custom model."""
        with patch.dict(os.environ, {}, clear=True):
            client = CopilotLLMClient(model="claude-sonnet-4.5")
            assert client.model == "claude-sonnet-4.5"

    def test_client_uses_provided_github_token(self):
        """Client uses explicitly provided GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            client = CopilotLLMClient(github_token="ghp_test123")
            assert client.github_token == "ghp_test123"

    def test_client_reads_copilot_github_token_env_var(self):
        """Client reads COPILOT_GITHUB_TOKEN if no explicit token."""
        with patch.dict(
            os.environ, {"COPILOT_GITHUB_TOKEN": "ghp_copilot123"}
        ):
            client = CopilotLLMClient()
            assert client.github_token == "ghp_copilot123"

    def test_client_reads_gh_token_env_var(self):
        """Client falls back to GH_TOKEN."""
        with patch.dict(os.environ, {"GH_TOKEN": "ghp_gh123"}):
            client = CopilotLLMClient()
            assert client.github_token == "ghp_gh123"

    def test_client_reads_github_token_env_var(self):
        """Client falls back to GITHUB_TOKEN."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_github123"}):
            client = CopilotLLMClient()
            assert client.github_token == "ghp_github123"

    def test_client_token_priority(self):
        """Explicit token takes priority over env vars."""
        with patch.dict(
            os.environ,
            {
                "COPILOT_GITHUB_TOKEN": "ghp_copilot123",
                "GH_TOKEN": "ghp_gh123",
            },
        ):
            client = CopilotLLMClient(github_token="ghp_explicit")
            assert client.github_token == "ghp_explicit"

    def test_client_working_directory(self):
        """Client accepts working directory."""
        client = CopilotLLMClient(working_directory="/tmp/work")
        assert client.working_directory == "/tmp/work"


class TestCopilotLLMClientComplete:
    """Test complete() method."""

    def test_complete_rejects_async_context(self):
        """complete() rejects if called from async context."""

        async def async_test():
            client = CopilotLLMClient()
            with pytest.raises(RuntimeError, match="cannot be called from async"):
                client.complete([{"role": "user", "content": "test"}])

        asyncio.run(async_test())


class TestCopilotLLMClientMessageConversion:
    """Test message and tool format conversion."""

    def test_convert_messages_passthrough(self):
        """_convert_messages passes through message format."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        result = CopilotLLMClient._convert_messages(messages)
        assert result == messages

    def test_convert_tools_empty_list(self):
        """_convert_tools handles empty tool list."""
        result = CopilotLLMClient._convert_tools([])
        assert result == []

    def test_convert_tools_basic(self):
        """_convert_tools converts tool definitions."""
        tools = [
            {
                "tool_id": "repo.read_file",
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            }
        ]
        result = CopilotLLMClient._convert_tools(tools)
        assert len(result) == 1
        assert result[0]["name"] == "read_file"
        assert result[0]["description"] == "Read a file"
        assert "parameters" in result[0]

    def test_convert_tools_fallback_to_tool_id(self):
        """_convert_tools uses tool_id if name missing."""
        tools = [
            {
                "tool_id": "repo.search_code",
                "description": "Search code",
                "parameters": {},
            }
        ]
        result = CopilotLLMClient._convert_tools(tools)
        assert result[0]["name"] == "repo.search_code"

    def test_convert_tool_call_basic(self):
        """_convert_tool_call converts tool call event."""
        mock_call = MagicMock()
        mock_call.tool_name = "repo.list_files"
        mock_call.tool_arguments = {"path": "."}

        result = CopilotLLMClient._convert_tool_call(mock_call)
        assert result["tool_id"] == "repo.list_files"
        assert result["arguments"] == {"path": "."}

    def test_convert_tool_call_missing_name(self):
        """_convert_tool_call handles missing tool name."""
        mock_call = MagicMock()
        mock_call.tool_name = None
        mock_call.tool_arguments = {}

        result = CopilotLLMClient._convert_tool_call(mock_call)
        assert result["tool_id"] == "unknown"


class TestCopilotLLMClientWithTools:
    """Test tool handling in complete()."""

    def test_tools_convert_to_copilot_format(self):
        """Tool definitions are converted for Copilot session."""
        tools = [
            {
                "tool_id": "repo.list_files",
                "name": "list_files",
                "description": "List files",
                "parameters": {"type": "object"},
            }
        ]

        converted = CopilotLLMClient._convert_tools(tools)
        assert len(converted) == 1
        assert converted[0]["name"] == "list_files"
        assert converted[0]["description"] == "List files"
        assert "parameters" in converted[0]


class TestCopilotLLMClientProtocolCompliance:
    """Test compliance with LLMClient protocol."""

    def test_implements_complete_method(self):
        """CopilotLLMClient has complete() method."""
        client = CopilotLLMClient()
        assert hasattr(client, "complete")
        assert callable(client.complete)

    def test_complete_returns_correct_type(self):
        """complete() signature returns dict."""
        # Verify the method signature
        import inspect
        
        client = CopilotLLMClient()
        sig = inspect.signature(client.complete)
        assert "messages" in sig.parameters
        assert "tools" in sig.parameters
        assert "system_prompt" in sig.parameters


class TestCopilotLLMClientEventHandling:
    """Test response handling in _run_session method."""

    def _run_async_test(self, async_func):
        """Helper to run async test functions."""
        return asyncio.run(async_func())

    def test_run_session_with_response(self):
        """_run_session returns content from send_and_wait response."""
        async def test():
            client = CopilotLLMClient()
            
            # Mock session with send_and_wait
            mock_session = AsyncMock()
            
            # Mock the response event
            mock_response_event = MagicMock()
            mock_response_event.data = MagicMock()
            mock_response_event.data.content = "Hello, how can I help?"
            
            mock_session.send_and_wait = AsyncMock(return_value=mock_response_event)
            
            result = await client._run_session(
                mock_session, 
                [{"role": "user", "content": "Hello"}]
            )
            
            assert result["content"] == "Hello, how can I help?"
            assert result["done"] is True
            assert result["tool_calls"] == []  # Empty list when no tools executed (Milestone 5)
            mock_session.send_and_wait.assert_called_once()
        
        self._run_async_test(test)

    def test_run_session_none_response(self):
        """_run_session raises error if send_and_wait returns None."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            mock_session.send_and_wait = AsyncMock(return_value=None)
            
            with pytest.raises(RuntimeError, match="did not return a response"):
                await client._run_session(
                    mock_session, 
                    [{"role": "user", "content": "Hello"}]
                )
        
        self._run_async_test(test)

    def test_run_session_empty_response(self):
        """_run_session raises error if response content is empty."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            
            # Mock response with empty content
            mock_response_event = MagicMock()
            mock_response_event.data = MagicMock()
            mock_response_event.data.content = ""
            
            mock_session.send_and_wait = AsyncMock(return_value=mock_response_event)
            
            with pytest.raises(RuntimeError, match="returned an empty response"):
                await client._run_session(
                    mock_session, 
                    [{"role": "user", "content": "Hello"}]
                )
        
        self._run_async_test(test)

    def test_run_session_none_content_attribute(self):
        """_run_session raises error if content attribute is missing."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            
            # Mock response with no content attribute
            mock_response_event = MagicMock()
            mock_response_event.data = MagicMock(spec=[])  # No attributes
            
            mock_session.send_and_wait = AsyncMock(return_value=mock_response_event)
            
            with pytest.raises(RuntimeError, match="returned an empty response"):
                await client._run_session(
                    mock_session, 
                    [{"role": "user", "content": "Hello"}]
                )
        
        self._run_async_test(test)

    def test_run_session_validates_user_message(self):
        """_run_session raises error if last message not from user."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            mock_session.send_and_wait = AsyncMock()
            
            with pytest.raises(ValueError, match="Last message must be from user"):
                await client._run_session(
                    mock_session, 
                    [{"role": "assistant", "content": "Hi"}]
                )
        
        self._run_async_test(test)

    def test_run_session_validates_empty_messages(self):
        """_run_session raises error if messages list is empty."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            mock_session.send_and_wait = AsyncMock()
            
            with pytest.raises(ValueError, match="Messages list cannot be empty"):
                await client._run_session(mock_session, [])
        
        self._run_async_test(test)

    def test_run_session_calls_send_and_wait_with_content(self):
        """_run_session sends correct message to send_and_wait."""
        async def test():
            client = CopilotLLMClient()
            
            mock_session = AsyncMock()
            
            # Mock response
            mock_response_event = MagicMock()
            mock_response_event.data = MagicMock()
            mock_response_event.data.content = "Response"
            
            mock_session.send_and_wait = AsyncMock(return_value=mock_response_event)
            
            await client._run_session(
                mock_session, 
                [{"role": "user", "content": "Test question"}]
            )
            
            # Verify send_and_wait was called with the correct message
            mock_session.send_and_wait.assert_called_once_with(
                "Test question",
                timeout=30.0
            )
        
        self._run_async_test(test)
