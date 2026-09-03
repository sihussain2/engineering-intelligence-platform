"""Controlled file modification tool for the Engineering Intelligence Platform."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ModificationResult:
    """Result of a file modification attempt."""

    success: bool
    path: str
    operation: str  # "replace" or other operation type
    changes: int  # Number of replacements made
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for LLM consumption."""
        result = {
            "success": self.success,
            "path": self.path,
            "operation": self.operation,
            "changes": self.changes,
        }
        if self.old_content is not None:
            result["old_content"] = self.old_content
        if self.new_content is not None:
            result["new_content"] = self.new_content
        if self.error is not None:
            result["error"] = self.error
        return result


class RepositoryModificationTool:
    """Controlled file modification interface for a software repository."""

    def __init__(self, root: Path):
        """
        Initialize modification tool.

        Args:
            root: Path to the repository root directory.
        """
        self.root = Path(root).resolve()

    def modify_file(
        self, path: str, old_content: str, new_content: str
    ) -> ModificationResult:
        """
        Modify a file by replacing exact content.

        Validation requirements:
        1. Resolve path relative to repository root
        2. Reject any path outside repository root
        3. Reject nonexistent files
        4. Read current file contents
        5. Require exact matching of old_content
        6. Require exactly ONE occurrence of old_content
        7. Reject if zero occurrences exist
        8. Reject if more than one occurrence exists
        9. Only after all validation succeeds, perform replacement
        10. Preserve the rest of the file exactly
        11. Return structured evidence

        Args:
            path: Repository-relative path to file to modify
            old_content: Exact current content to replace (must match exactly once)
            new_content: New content to replace old_content with

        Returns:
            ModificationResult with success status and details
        """
        # Step 1: Resolve path relative to repository root
        try:
            target = (self.root / path).resolve()
        except (ValueError, OSError) as e:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error=f"Invalid path: {str(e)}",
            )

        # Step 2: Reject path outside repository root
        try:
            target.relative_to(self.root)
        except ValueError:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error="Path is outside the repository",
            )

        # Step 3: Reject nonexistent files
        if not target.exists():
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error="File does not exist",
            )

        if not target.is_file():
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error="Path is not a file",
            )

        # Step 4: Read current file contents
        try:
            current_content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error=f"Cannot read file: {str(e)}",
            )

        # Step 5 & 6: Require exact matching and exactly ONE occurrence
        occurrence_count = current_content.count(old_content)

        # Step 7: Reject if zero occurrences
        if occurrence_count == 0:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error="old_content not found in file",
            )

        # Step 8: Reject if more than one occurrence
        if occurrence_count > 1:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error=f"old_content appears {occurrence_count} times (must appear exactly once)",
            )

        # Step 9 & 10: Perform replacement
        modified_content = current_content.replace(old_content, new_content, count=1)

        # Step 11: Write modified content
        try:
            target.write_text(modified_content, encoding="utf-8")
        except OSError as e:
            return ModificationResult(
                success=False,
                path=path,
                operation="replace",
                changes=0,
                error=f"Cannot write file: {str(e)}",
            )

        # Return success with evidence
        return ModificationResult(
            success=True,
            path=path,
            operation="replace",
            changes=1,
            old_content=old_content,
            new_content=new_content,
        )
