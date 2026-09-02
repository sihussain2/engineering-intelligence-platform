"""GitHub Copilot SDK adapter implementing LLMClient protocol."""

import asyncio
import os
from typing import Any, Optional

try:
    from copilot import CopilotClient
    from copilot.session import PermissionHandler
    from copilot.session_events import (
        AssistantMessageData,
        SessionIdleData,
    )
except ImportError:
    raise ImportError(
        "github-copilot-sdk is required. Install with: pip install github-copilot-sdk"
    )


class CopilotLLMClient:
    """
    LLMClient implementation using GitHub Copilot SDK.

    Adapts the Copilot SDK's async event-based interface to our synchronous
    complete() interface. Preserves provider-independence by keeping all
    Copilot SDK specifics inside this adapter.

    Uses GitHub's stored OAuth credentials from `copilot` CLI login.
    Falls back to COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN env vars.
    """

    def __init__(
        self,
        model: str = "gpt-5",
        github_token: Optional[str] = None,
        working_directory: Optional[str] = None,
    ):
        """
        Initialize Copilot LLM client.

        Args:
            model: Model to use. Default "gpt-5" (Copilot's latest).
            github_token: GitHub token. If None, uses copilot CLI auth or env vars.
            working_directory: Working directory for Copilot operations.
        """
        self.model = model
        self.github_token = github_token or os.environ.get(
            "COPILOT_GITHUB_TOKEN"
        ) or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.working_directory = working_directory

    def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Request a completion from Copilot LLM.

        Runs async event loop internally to adapt Copilot SDK's async API
        to our sync interface.

        Args:
            messages: Conversation history.
            tools: Optional tool definitions (JSON schema format).
            system_prompt: Optional system prompt.

        Returns:
            Normalized dict with keys:
            {
                "content": str,
                "tool_calls": Optional[list[dict]],
                    # Each tool call: {"tool_id": str, "arguments": dict}
                "done": bool,
            }

        Raises:
            RuntimeError: If running inside an existing async event loop.
        """
        try:
            # Check if we're already in an async context
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "CopilotLLMClient.complete() cannot be called from async context. "
                "Use asyncio.run() or call from sync code."
            )
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                raise

        # Run async complete in new event loop
        return asyncio.run(self._complete_async(messages, tools, system_prompt))

    async def _complete_async(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Async implementation of complete().

        Manages Copilot client lifecycle and handles event-based responses.
        """
        # Convert our message format to Copilot format
        copilot_messages = self._convert_messages(messages)

        # Build session config
        session_config: dict[str, Any] = {
            "on_permission_request": PermissionHandler.approve_all,
            "model": self.model,
        }

        # Add system prompt if provided
        if system_prompt:
            session_config["system_message"] = {
                "mode": "append",
                "content": system_prompt,
            }

        # Convert tools to Copilot format if provided
        if tools:
            session_config["tools"] = self._convert_tools(tools)

        # Create and use client
        async with CopilotClient(
            github_token=self.github_token,
            working_directory=self.working_directory,
        ) as client:
            async with await client.create_session(**session_config) as session:
                return await self._run_session(session, messages)

    async def _run_session(self, session, messages: list[dict]) -> dict:
        """
        Run a Copilot session and collect response.

        Listens for events and returns the first assistant message and any
        tool calls. Sets done=True when session becomes idle.
        """
        result = {
            "content": "",
            "tool_calls": None,
            "done": False,
        }

        # Prepare events to track
        completion_event = asyncio.Event()
        tool_calls_data = []
        assistant_content = ""

        def on_event(event):
            nonlocal assistant_content, tool_calls_data

            # Check event type by class name (duck typing)
            event_type = type(event.data).__name__

            if event_type == "AssistantMessageData":
                # Capture assistant message
                assistant_content = getattr(event.data, "content", "") or ""

            elif event_type == "ToolCallData" or event_type == "ExternalToolRequestedData":
                # Capture tool call - store the event data for later processing
                tool_calls_data.append(event.data)

            elif event_type == "SessionIdleData":
                # Session finished
                completion_event.set()

        # Subscribe to events
        session.on(on_event)

        # Send the last user message (already in conversation history)
        last_message = messages[-1]
        if last_message.get("role") != "user":
            raise ValueError(
                "Last message must be from user role for complete()"
            )

        # Send to Copilot
        await session.send(last_message.get("content", ""))

        # Wait for completion
        await completion_event.wait()

        # Build result
        result["content"] = assistant_content
        result["done"] = True  # Copilot session completed

        # Convert tool calls if any
        if tool_calls_data:
            result["tool_calls"] = [
                self._convert_tool_call(tc) for tc in tool_calls_data
            ]

        return result

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        """
        Convert our message format to Copilot format.

        Our format: [{"role": "user"|"assistant"|"tool", "content": "..."}]
        Copilot format: similar, but "tool" role has extra fields.

        For this implementation, we pass through as-is since the formats
        are compatible. Copilot will handle the interpretation.
        """
        return messages

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """
        Convert our tool definitions to Copilot SDK format.

        Our format: list of dicts with tool_id, name, description, parameters
        Copilot format: list of Tool objects with name, description, parameters

        For now, returns tools as-is since schemas are compatible.
        Copilot SDK accepts raw dict definitions.
        """
        converted = []
        for tool in tools:
            # Extract fields we use
            copilot_tool = {
                "name": tool.get("name", tool.get("tool_id", "unknown")),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            }
            converted.append(copilot_tool)
        return converted

    @staticmethod
    def _convert_tool_call(tool_call_data) -> dict:
        """
        Convert Copilot tool call event to our format.

        Uses duck typing to extract tool_name and tool_arguments from the
        event data object regardless of its specific type.

        Returns: {"tool_id": str, "arguments": dict}
        """
        tool_name = getattr(tool_call_data, "tool_name", None)
        tool_arguments = getattr(tool_call_data, "tool_arguments", {}) or {}

        return {
            "tool_id": tool_name or "unknown",
            "arguments": tool_arguments,
        }
