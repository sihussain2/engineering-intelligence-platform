"""Tool dispatcher for routing and executing LLM tool calls."""

from dataclasses import dataclass
from typing import Any, Optional

from eip.repository.tool import RepositoryTool
from eip.repository.modification import RepositoryModificationTool
from eip.repository.execution import TestExecutionTool
from eip.llm.tools import ALL_TOOLS, ToolDefinition


@dataclass
class ToolCall:
    """Parsed tool call from LLM."""

    tool_id: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool."""

    tool_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_llm_message(self) -> dict:
        """Format as LLM tool result message."""
        if self.success:
            return {
                "role": "tool",
                "tool_use_id": self.tool_id,
                "content": str(self.result),
            }
        else:
            return {
                "role": "tool",
                "tool_use_id": self.tool_id,
                "content": f"Error: {self.error}",
            }


class ToolDispatcher:
    """Routes and executes tool calls for repository operations."""

    def __init__(self, repository_tool: RepositoryTool):
        """
        Initialize dispatcher with repository tools.

        Args:
            repository_tool: RepositoryTool instance for repository access.
        """
        if not isinstance(repository_tool, RepositoryTool):
            raise TypeError("repository_tool must be a RepositoryTool instance")
        self.repository_tool = repository_tool
        self.modification_tool = RepositoryModificationTool(repository_tool.root)
        self.execution_tool = TestExecutionTool(repository_tool.root)

    def get_tools(self) -> list[dict]:
        """Get all available tools in LLM-consumable format."""
        return [tool.to_dict() for tool in ALL_TOOLS]

    def execute_call(self, call: ToolCall) -> ToolResult:
        """
        Execute a validated tool call.

        Args:
            call: Parsed tool call with tool_id and arguments.

        Returns:
            ToolResult with success status and result or error.
        """
        try:
            if call.tool_id == "repo.list_files":
                path = call.arguments.get("path", ".")
                result = self.repository_tool.list_files(path)
                return ToolResult(
                    tool_id=call.tool_id, success=True, result=result
                )

            elif call.tool_id == "repo.read_file":
                path = call.arguments.get("path")
                if not path:
                    return ToolResult(
                        tool_id=call.tool_id,
                        success=False,
                        error="'path' argument is required",
                    )
                result = self.repository_tool.read_file(path)
                return ToolResult(
                    tool_id=call.tool_id, success=True, result=result
                )

            elif call.tool_id == "repo.search_code":
                query = call.arguments.get("query")
                if not query:
                    return ToolResult(
                        tool_id=call.tool_id,
                        success=False,
                        error="'query' argument is required",
                    )
                max_results = call.arguments.get("max_results", 100)
                result = self.repository_tool.search_code(query, max_results)
                return ToolResult(
                    tool_id=call.tool_id, success=True, result=result
                )

            elif call.tool_id == "repo.modify_file":
                path = call.arguments.get("path")
                old_content = call.arguments.get("old_content")
                new_content = call.arguments.get("new_content")
                if not path or old_content is None or new_content is None:
                    return ToolResult(
                        tool_id=call.tool_id,
                        success=False,
                        error="'path', 'old_content', and 'new_content' arguments are required",
                    )
                mod_result = self.modification_tool.modify_file(
                    path, old_content, new_content
                )
                return ToolResult(
                    tool_id=call.tool_id,
                    success=mod_result.success,
                    result=mod_result.to_dict() if mod_result.success else None,
                    error=mod_result.error,
                )

            elif call.tool_id == "repo.run_tests":
                test_path = call.arguments.get("test_path")
                test_result = self.execution_tool.run_tests(test_path)
                return ToolResult(
                    tool_id=call.tool_id,
                    success=test_result.success,
                    result=test_result.to_dict(),
                    error=None,
                )

            else:
                return ToolResult(
                    tool_id=call.tool_id,
                    success=False,
                    error=f"Unknown tool: {call.tool_id}",
                )

        except ValueError as e:
            return ToolResult(
                tool_id=call.tool_id,
                success=False,
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                tool_id=call.tool_id,
                success=False,
                error=f"Execution error: {str(e)}",
            )
