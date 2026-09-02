"""JSON schema definitions for repository tools."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool that an LLM can invoke."""

    tool_id: str
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters

    def to_dict(self) -> dict:
        """Convert to dict for LLM consumption."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


# Tool definitions for RepositoryTool methods

LIST_FILES_TOOL = ToolDefinition(
    tool_id="repo.list_files",
    name="list_files",
    description="List all files and directories in the repository under a given path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Repository-relative path to list. Defaults to '.' (repository root).",
                "default": ".",
            }
        },
        "required": [],
    },
)

READ_FILE_TOOL = ToolDefinition(
    tool_id="repo.read_file",
    name="read_file",
    description="Read the complete text contents of a single file from the repository.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Repository-relative path to the file to read.",
            }
        },
        "required": ["path"],
    },
)

SEARCH_CODE_TOOL = ToolDefinition(
    tool_id="repo.search_code",
    name="search_code",
    description="Search repository source files for lines containing a text query. Returns matching file paths, line numbers, and matching lines.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text to search for (case-sensitive substring match).",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matching lines to return. Defaults to 100.",
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
            },
        },
        "required": ["query"],
    },
)

ALL_TOOLS = [LIST_FILES_TOOL, READ_FILE_TOOL, SEARCH_CODE_TOOL]
