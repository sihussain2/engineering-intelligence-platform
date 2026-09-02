"""Provider-independent LLM client protocol."""

from typing import Any, Optional, Protocol


class LLMClient(Protocol):
    """
    Protocol for any LLM provider.

    Enables swapping between OpenAI, Anthropic, local models, etc.
    without changing core code.
    """

    def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Request a completion from the LLM with optional tool definitions.

        Args:
            messages: Conversation history. Each message is a dict with:
                {"role": "user"|"assistant"|"tool", "content": "..."}
            tools: Optional list of tool definitions (JSON schema format).
            system_prompt: Optional system prompt.

        Returns:
            Dict with keys:
            {
                "content": str,  # LLM's text response
                "tool_calls": Optional[list[dict]],  # If LLM wants to call tools
                    # Each tool call has: {"tool_id": str, "arguments": dict}
                "done": bool,  # Whether LLM is finished reasoning
            }
        """
        ...
