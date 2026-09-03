"""GitHub Copilot SDK adapter implementing LLMClient protocol."""

import asyncio
import os
from typing import TYPE_CHECKING, Any, Optional

try:
    from copilot import CopilotClient
    from copilot.session import PermissionHandler, Tool
    from copilot.tools import ToolInvocation, ToolResult
except ImportError:
    raise ImportError(
        "github-copilot-sdk is required. Install with: pip install github-copilot-sdk"
    )

if TYPE_CHECKING:
    from eip.llm.dispatcher import ToolDispatcher


class CopilotLLMClient:
    """
    LLMClient implementation using GitHub Copilot SDK.

    Adapts the Copilot SDK's async event-based interface to our synchronous
    complete() interface. Preserves provider-independence by keeping all
    Copilot SDK specifics inside this adapter.

    Uses GitHub's stored OAuth credentials from `copilot` CLI login.
    Falls back to COPILOT_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN env vars.

    MILESTONE 2 (Current): Real Copilot tool calling
    - ✅ Text-based LLM responses
    - ✅ System prompt support
    - ✅ Message history (SimpleAgent maintains context)
    - ✅ Real Copilot provider tool calling bridged to EIP ToolDispatcher
    - ✅ EIP tool definitions exposed to LLM via SDK Tool handlers

    The integration uses Copilot SDK's Tool handler mechanism to:
    1. Define EIP repository tools (list_files, read_file, search_code)
    2. Pass them to the Copilot session
    3. When LLM requests a tool, the SDK calls our handler
    4. Handler converts to EIP ToolCall and executes via ToolDispatcher
    5. Handler returns result as SDK ToolResult
    6. SDK continues conversation with tool result
    7. Final response is returned after all tool calls complete
    """

    def __init__(
        self,
        model: str = "claude-haiku-4.5",
        github_token: Optional[str] = None,
        working_directory: Optional[str] = None,
        dispatcher: Optional["ToolDispatcher"] = None,
    ):
        """
        Initialize Copilot LLM client.

        Args:
            model: Model to use. Default "claude-haiku-4.5" (Claude Haiku 4.5).
            github_token: GitHub token. If None, uses copilot CLI auth or env vars.
            working_directory: Working directory for Copilot operations.
            dispatcher: Optional ToolDispatcher for tool execution. If provided,
                enables real Copilot tool calling to EIP-controlled tools.
        """
        self.model = model
        self.github_token = github_token or os.environ.get(
            "COPILOT_GITHUB_TOKEN"
        ) or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.working_directory = working_directory
        self.dispatcher = dispatcher

    def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Request a completion from Copilot LLM with optional tool support.

        Runs async event loop internally to adapt Copilot SDK's async API
        to our sync interface.

        MILESTONE 2 (Current):
        - ✅ Text-based completion
        - ✅ System prompt support
        - ✅ Message history (SimpleAgent maintains context)
        - ✅ Real Copilot tool calling (if dispatcher is provided)

        Args:
            messages: Conversation history. Each message is:
                {"role": "user"|"assistant", "content": "..."}
                Last message MUST be from user.
            tools: List of EIP tool definitions. If provided and dispatcher is
                configured, these tools are exposed to the LLM via Copilot SDK
                Tool handlers. The LLM can request them, and handlers route them
                through EIP's ToolDispatcher.
            system_prompt: Optional system prompt for instructions.

        Returns:
            Dict with keys:
            {
                "content": str,  # LLM's text response
                "tool_calls": None,  # Tool calls are handled internally by SDK
                "done": bool,  # Always True (session completes)
            }

        Raises:
            RuntimeError: If called from existing async event loop.
            ValueError: If last message is not from user or content is empty.
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

        Manages Copilot client lifecycle and handles tool invocation.

        If dispatcher is configured and tools are provided:
        1. Converts EIP tool definitions to SDK Tool objects
        2. Creates handlers that route tool calls to ToolDispatcher
        3. Passes tools to Copilot session with explicit available_tools allowlist
        4. SDK automatically invokes handlers when LLM requests tools
        5. Handlers execute through EIP's controlled ToolDispatcher
        6. SDK continues conversation with tool results
        7. Final response returned after all tool calls complete

        SECURITY: When tools are provided, available_tools is set to an explicit
        allowlist containing ONLY those custom tools. This prevents the Copilot
        runtime from exposing built-in tools (bash, git, etc.) to the LLM.
        """
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

        # Build SDK Tool objects if dispatcher and tools are provided
        sdk_tools = None
        if self.dispatcher and tools:
            sdk_tools = self._build_sdk_tools(tools)
            session_config["tools"] = sdk_tools

            # SECURITY: Restrict available tools to ONLY custom EIP tools.
            # This prevents the Copilot runtime from exposing built-in tools
            # (like bash, git, etc.) to the LLM.
            # Each tool is allowlisted by its name in "custom:name" format.
            available_tools = [f"custom:{tool.get('name', '')}" for tool in tools]
            session_config["available_tools"] = available_tools

        # Create and use client
        async with CopilotClient(
            github_token=self.github_token,
            working_directory=self.working_directory,
        ) as client:
            async with await client.create_session(**session_config) as session:
                return await self._run_session(session, messages)

    def _build_sdk_tools(self, eip_tools: list[dict]) -> list[Tool]:
        """
        Build Copilot SDK Tool objects from EIP tool definitions.

        Each Tool has a handler that:
        1. Receives ToolInvocation from SDK
        2. Converts to EIP ToolCall
        3. Executes via EIP's ToolDispatcher
        4. Converts result to SDK ToolResult

        Args:
            eip_tools: List of EIP tool definitions (dicts with tool_id, name,
                description, parameters)

        Returns:
            List of SDK Tool objects ready to pass to create_session()
        """
        if not self.dispatcher:
            # Should not happen (checked before calling), but be safe
            return []

        sdk_tools = []
        for eip_tool in eip_tools:
            # Extract EIP tool info
            tool_id = eip_tool.get("tool_id", "")
            name = eip_tool.get("name", tool_id)
            description = eip_tool.get("description", "")
            parameters = eip_tool.get("parameters", {})

            # Create a handler for this specific tool
            # Use a closure to capture tool_id
            def make_handler(tid):
                def tool_handler(invocation: ToolInvocation) -> ToolResult:
                    return self._handle_tool_invocation(tid, invocation)
                return tool_handler

            # Create SDK Tool with handler
            sdk_tool = Tool(
                name=name,
                description=description,
                handler=make_handler(tool_id),
                parameters=parameters,
            )
            sdk_tools.append(sdk_tool)

        return sdk_tools

    def _handle_tool_invocation(
        self, tool_id: str, invocation: ToolInvocation
    ) -> ToolResult:
        """
        Handle a tool invocation from Copilot SDK.

        Bridges Copilot's tool invocation to EIP's ToolDispatcher.

        Args:
            tool_id: EIP tool ID (from tool definition)
            invocation: Copilot SDK ToolInvocation with arguments

        Returns:
            Copilot SDK ToolResult with execution result
        """
        if not self.dispatcher:
            return ToolResult(
                text_result_for_llm="Error: No dispatcher configured",
                result_type="failure",
                error="ToolDispatcher not available",
            )

        try:
            # Import here to avoid circular dependencies
            from eip.llm.dispatcher import ToolCall

            # Convert SDK invocation to EIP ToolCall
            tool_call = ToolCall(
                tool_id=tool_id,
                arguments=invocation.arguments or {},
            )

            # Execute through EIP's ToolDispatcher
            tool_result = self.dispatcher.execute_call(tool_call)

            # Convert EIP ToolResult to SDK ToolResult
            if tool_result.success:
                return ToolResult(
                    text_result_for_llm=str(tool_result.result),
                    result_type="success",
                )
            else:
                return ToolResult(
                    text_result_for_llm=f"Error: {tool_result.error}",
                    result_type="failure",
                    error=tool_result.error or "Unknown error",
                )
        except Exception as e:
            # Catch any errors and return as failure to SDK
            return ToolResult(
                text_result_for_llm=f"Exception: {str(e)}",
                result_type="failure",
                error=str(e),
            )

    async def _run_session(self, session, messages: list[dict]) -> dict:
        """
        Run a Copilot session and collect final response.

        With real tool calling enabled (dispatcher configured + tools provided):
        1. Calls session.send_and_wait() with full conversation history
        2. SDK sends message + tools to LLM
        3. If LLM requests a tool, SDK calls the tool handler
        4. Handler executes tool via ToolDispatcher and returns result
        5. SDK continues conversation with tool result
        6. Repeat until LLM produces final response
        7. send_and_wait() returns the final response

        Without tool calling (no dispatcher or no tools):
        - Simple text-only completion, same as before

        The SDK handles all tool iteration internally via send_and_wait().
        We only need to wait for the final response.

        FIX FOR SESSION ISOLATION: This method now includes FULL message history
        in the prompt sent to send_and_wait(), not just the latest message.
        This ensures the LLM has context from previous tool calls and responses,
        even though each complete() call creates a new SDK session.

        Args:
            session: Copilot session object
            messages: Conversation history (full message history)

        Returns:
            Dict with content and done flag
        """
        # Validate input
        if not messages:
            raise ValueError("Messages list cannot be empty")

        last_message = messages[-1]
        if last_message.get("role") != "user":
            raise ValueError(
                "Last message must be from user role for complete()"
            )

        # Build full conversation prompt including message history
        # This ensures the LLM has context from all previous exchanges
        full_prompt = self._build_full_prompt(messages)

        # send_and_wait() handles tool invocation internally:
        # - If tools are configured and LLM requests them, SDK calls handlers
        # - Handlers execute via ToolDispatcher
        # - Results are fed back to LLM
        # - SDK continues until final response is ready
        response_event = await session.send_and_wait(full_prompt, timeout=30.0)

        # Extract content from response
        if response_event is None:
            raise RuntimeError(
                "Copilot did not return a response. Session may have failed."
            )

        # Get the assistant message content
        # The SDK returns AssistantMessageData as the final message event
        content = getattr(response_event.data, "content", None)

        if not content:
            raise RuntimeError(
                "Copilot returned an empty response. "
                "Check authentication and service status."
            )

        result = {
            "content": content,
            "tool_calls": None,  # SDK handles tool calls internally
            "done": True,
        }

        return result

    @staticmethod
    def _build_full_prompt(messages: list[dict]) -> str:
        """
        Build a full conversation prompt from message history.

        Converts the message history into a single prompt string that includes
        all previous exchanges. This ensures the LLM has full context even though
        each complete() call creates a new SDK session.

        Args:
            messages: List of message dicts with "role" and "content"

        Returns:
            Single prompt string with full conversation history
        """
        if not messages:
            return ""

        # If only one message, it's just the user's message
        if len(messages) == 1:
            return messages[0].get("content", "")

        # Format previous messages as conversation history
        prompt_parts = []

        # Include all but the last message as context
        for msg in messages[:-1]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            else:
                prompt_parts.append(f"{role}: {content}")

        # Add the final user message
        final_msg = messages[-1]
        final_content = final_msg.get("content", "")

        # If there's history, prefix the current message
        if len(messages) > 1:
            prompt_parts.append(f"\nCurrent request from user: {final_content}")
            return "\n".join(prompt_parts)
        else:
            return final_content

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
