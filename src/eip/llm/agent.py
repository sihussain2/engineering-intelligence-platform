"""Simple agent loop for LLM-based repository analysis."""

from dataclasses import dataclass, field
from typing import Any, Optional

from eip.repository.tool import RepositoryTool
from eip.llm.protocol import LLMClient
from eip.llm.dispatcher import ToolCall, ToolDispatcher, ToolResult
from eip.llm.verification import (
    EngineringResult,
    ImplementationSummary,
    VerificationSummary,
    ReviewFindings,
    RequirementStatus,
)


@dataclass
class AgentSession:
    """Manages state for a single agent interaction."""

    requirement: str
    messages: list[dict] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    final_response: Optional[str] = None
    iterations: int = 0

    # Verification state (Milestone 5)
    tests_passed: Optional[bool] = None  # None = not run, True = passed, False = failed
    recovery_attempts: int = 0
    last_test_result: Optional[dict] = None  # Last test result from tool
    modifications_made: list[str] = field(default_factory=list)  # Files modified
    engineering_result: Optional[EngineringResult] = None

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

        # Track test results for verification (Milestone 5)
        if result.tool_id == "repo.run_tests" and result.result:
            self.last_test_result = result.result
            self.tests_passed = result.result.get("success", False)

    def record_modification(self, file_path: str):
        """Record that a file was modified."""
        if file_path not in self.modifications_made:
            self.modifications_made.append(file_path)


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

        # Configure the LLM client with dispatcher if it supports tool execution.
        # For CopilotLLMClient, this enables real provider tool calling.
        # For other clients, this is a no-op (they don't have a dispatcher attribute).
        if hasattr(llm_client, "dispatcher") and not llm_client.dispatcher:
            llm_client.dispatcher = self.dispatcher

    @staticmethod
    def _get_verification_prompt(requirement: str, is_first_iteration: bool = True) -> str:
        """
        Generate a system prompt for verification-aware engineering.

        Args:
            requirement: The engineering requirement.
            is_first_iteration: Whether this is the first iteration.

        Returns:
            System prompt guiding the agent through the engineering workflow.
        """
        if is_first_iteration:
            return f"""You are an AI assistant performing controlled software engineering.

TASK: {requirement}

WORKFLOW:
1. INVESTIGATE: Use repository tools to understand the codebase and identify what needs to change.
2. PLAN: Determine the specific modifications needed to satisfy the requirement.
3. IMPLEMENT: Use modify_file to make controlled changes to the code.
4. VERIFY: Use run_tests to execute tests and verify the implementation.
5. If tests PASS: Review the implementation and evaluate against the requirement.
6. If tests FAIL: Diagnose the failure using repository tools, then make corrective modifications.
7. ITERATE: Continue until tests pass or you reach the limit of corrections.

IMPORTANT CONSTRAINTS:
- You can ONLY modify files using modify_file (with exact old_content and new_content).
- You can ONLY run tests using run_tests.
- You can ONLY inspect code using list_files, read_file, and search_code.
- You CANNOT use bash, git, or arbitrary shell commands.
- After each modification, you MUST run tests to verify the change.
- If a test fails, INSPECT the failure and DIAGNOSE the cause before trying again.

REPORTING:
- Document what you investigate.
- Document modifications you make and why.
- Document test results.
- If you encounter failures, explain your diagnosis and the fix attempted.
- Provide a final summary of whether the requirement is satisfied."""
        else:
            return f"""Continue the engineering task: {requirement}

CURRENT STATUS:
- Use the same tools to continue investigating, fixing, and verifying.
- If tests are failing, inspect the failure output and diagnose the cause.
- If the implementation needs correction, modify it and re-run tests.
- Continue iterating until tests pass.

After tests pass:
- Review the implementation against the original requirement.
- Evaluate whether the requirement is truly satisfied.
- Provide a clear final assessment."""

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
            system_prompt = self._get_verification_prompt(requirement, is_first_iteration=True)

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
                    # Check if tool was already executed by provider (e.g., Copilot SDK)
                    already_executed = tool_call_data.get("already_executed", False)

                    if already_executed:
                        # Tool was already executed by provider (Copilot SDK)
                        # Create ToolResult from the execution data
                        from eip.llm.dispatcher import ToolResult
                        result = ToolResult(
                            tool_id=tool_call_data.get("tool_id", ""),
                            success=tool_call_data.get("success", False),
                            result=tool_call_data.get("result", None),
                            error=tool_call_data.get("error", None),
                        )
                    else:
                        # Tool needs to be executed by SimpleAgent
                        # Parse tool call
                        call = ToolCall(
                            tool_id=tool_call_data["tool_id"],
                            arguments=tool_call_data.get("arguments", {}),
                        )
                        # Execute
                        result = self.dispatcher.execute_call(call)

                    # Add to session
                    session.add_tool_result(result)

                    # Track modifications (Milestone 5)
                    if result.tool_id == "repo.modify_file" and result.result:
                        if result.result.get("success"):
                            session.record_modification(result.result.get("path", ""))

            # Check if LLM signals completion
            if llm_response.get("done"):
                session.final_response = llm_response.get("content", "")
                break

            # After test failures, continue iterating to allow diagnosis and recovery (Milestone 5)
            # Update system prompt to reflect ongoing iteration
            if session.tests_passed is False:
                session.recovery_attempts += 1
                system_prompt = self._get_verification_prompt(requirement, is_first_iteration=False)

        # If max iterations reached without done signal, use last response
        if session.final_response is None and session.messages:
            last_assistant_msg = None
            for msg in reversed(session.messages):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg.get("content", "")
                    break
            session.final_response = last_assistant_msg

        return session
