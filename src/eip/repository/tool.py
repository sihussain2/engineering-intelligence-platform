from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepositoryTool:
    """Read-only interface for inspecting a software repository."""

    root: Path

    def list_files(self, path: str = ".") -> list[str]:
        """List files and directories under the given repository path."""
        target = (self.root / path).resolve()

        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("Path is outside the repository")

        return [
            str(item.relative_to(self.root))
            for item in sorted(target.rglob("*"))
        ]

    def read_file(self, path: str) -> str:
        """Read a text file from the repository."""
        raise NotImplementedError

    def search_code(self, query: str) -> list[dict]:
        """Search repository source files for a text query."""
        raise NotImplementedError