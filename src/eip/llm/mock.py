"""Mock/fake LLM implementation for testing."""

from typing import Any, Optional

from eip.llm.protocol import LLMClient


class MockLLMClient:
    """
    Mock LLM that follows a predefined script for testing.

    Useful for:
    - Unit testing agent loops
    - Verifying tool calling logic
    - Testing error handling
    """

    def __init__(self, responses: Optional[list[dict]] = None):
        """
        Initialize with a list of responses to return.

        Args:
            responses: List of dicts, each with:
                {
                    "content": str,
                    "tool_calls": Optional[list[dict]],
                    "done": bool,
                }
        """
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = None

    def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Return the next canned response.

        Args:
            messages: Conversation history (stored for inspection).
            tools: Tool definitions.
            system_prompt: System prompt.

        Returns:
            Next response from self.responses.

        Raises:
            IndexError: If responses exhausted.
        """
        self.last_messages = messages

        if self.call_count >= len(self.responses):
            raise IndexError(
                f"MockLLMClient: No more responses. "
                f"Call count: {self.call_count}, responses: {len(self.responses)}"
            )

        response = self.responses[self.call_count]
        self.call_count += 1

        return response

    def reset(self):
        """Reset call count for reuse."""
        self.call_count = 0
        self.last_messages = None


class ConversationalMockLLM:
    """
    Mock LLM that simulates a multi-turn conversation.

    Useful for testing realistic agent loops.
    """

    def __init__(self):
        """Initialize empty conversation."""
        self.call_count = 0

    def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Simple script: search → read → final response.

        Turn 1: LLM searches for relevant files
        Turn 2: LLM reads a file
        Turn 3: LLM provides final analysis
        """
        self.call_count += 1

        if self.call_count == 1:
            # First turn: search for relevant code
            return {
                "content": "Let me search the repository for relevant code.",
                "tool_calls": [
                    {
                        "tool_id": "repo.search_code",
                        "arguments": {"query": "class", "max_results": 50},
                    }
                ],
                "done": False,
            }

        elif self.call_count == 2:
            # Second turn: read a file
            return {
                "content": "Now let me examine the structure in more detail.",
                "tool_calls": [
                    {
                        "tool_id": "repo.list_files",
                        "arguments": {"path": "src"},
                    }
                ],
                "done": False,
            }

        else:
            # Third turn and beyond: provide final response
            return {
                "content": "Based on my analysis of the repository, here are my findings...",
                "tool_calls": [],
                "done": True,
            }
