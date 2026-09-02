"""Simple agent loop for LLM-based repository analysis."""

from dataclasses import dataclass, field
from typing import Any, Optional

from eip.repository.tool import RepositoryTool
from eip.llm.protocol import LLMClient
from eip.llm.dispatcher import ToolCall, ToolDispatcher, ToolResult


@dataclass
class AgentSession:
    """Manages state for a single agent interaction."""

    requirement: str
    messages: list[dict] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    final_response: Optional[str] = None
    iterations: int = 0

    def add_user_message(self, content: str):
        """Add a user message to conversation."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """Add an assistant message to conversation."""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, result: ToolResult):
        """Add a tool result to conversation and tracking."""
        self.messages.append(result.to_llm_message())
        self.tool_results.append(result)


class SimpleAgent:
    """Minimal agent loop for tool-calling LLM interactions."""

    def __init__(
        self,
        llm_client: LLMClient,
        repository_tool: RepositoryTool,
        max_iterations: int = 10,
    ):
        """
        Initialize agent.

        Args:
            llm_client: LLMClient implementation.
            repository_tool: RepositoryTool for repository access.
            max_iterations: Maximum number of LLM turns before stopping.
        """
        self.llm_client = llm_client
        self.dispatcher = ToolDispatcher(repository_tool)
        self.max_iterations = max_iterations

    def run(self, requirement: str, system_prompt: Optional[str] = None) -> AgentSession:
        """
        Run agent loop for a given requirement.

        Args:
            requirement: The software requirement to analyze.
            system_prompt: Optional system prompt for the LLM.

        Returns:
            AgentSession with conversation history and results.
        """
        if not system_prompt:
            system_prompt = (
                "You are an AI assistant analyzing a software repository. "
                "Use the provided tools to explore the repository and understand its structure, "
                "then provide a detailed analysis of the requirement."
            )

        session = AgentSession(requirement=requirement)
        session.add_user_message(requirement)

        for iteration in range(self.max_iterations):
            session.iterations += 1

            # Get LLM response
            llm_response = self.llm_client.complete(
                messages=session.messages,
                tools=self.dispatcher.get_tools(),
                system_prompt=system_prompt,
            )

            # Add assistant message to history
            session.add_assistant_message(llm_response.get("content", ""))

            # Process tool calls if any
            tool_calls = llm_response.get("tool_calls", [])
            if tool_calls:
                for tool_call_data in tool_calls:
                    # Parse tool call
                    call = ToolCall(
                        tool_id=tool_call_data["tool_id"],
                        arguments=tool_call_data.get("arguments", {}),
                    )
                    # Execute
                    result = self.dispatcher.execute_call(call)
                    # Add to session
                    session.add_tool_result(result)

            # Check if LLM signals completion
            if llm_response.get("done"):
                session.final_response = llm_response.get("content", "")
                break

        # If max iterations reached without done signal, use last response
        if session.final_response is None and session.messages:
            last_assistant_msg = None
            for msg in reversed(session.messages):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg.get("content", "")
                    break
            session.final_response = last_assistant_msg

        return session
