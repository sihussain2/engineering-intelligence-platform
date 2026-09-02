"""Tool dispatcher for routing and executing LLM tool calls."""

from dataclasses import dataclass
from typing import Any, Optional

from eip.repository.tool import RepositoryTool
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
    """Routes and executes tool calls against RepositoryTool."""

    def __init__(self, repository_tool: RepositoryTool):
        """
        Initialize dispatcher with a repository tool.

        Args:
            repository_tool: RepositoryTool instance for repository access.
        """
        if not isinstance(repository_tool, RepositoryTool):
            raise TypeError("repository_tool must be a RepositoryTool instance")
        self.repository_tool = repository_tool

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
