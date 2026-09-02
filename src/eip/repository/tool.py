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
        target = (self.root / path).resolve()

        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("Path is outside the repository")

        if not target.is_file():
            raise ValueError("Path is not a file")

        return target.read_text(encoding="utf-8")

    def search_code(self, query: str, max_results: int = 100) -> list[dict]:
        """
        Search repository source files for a text query.

        Args:
            query: Text string to search for (case-sensitive substring match).
            max_results: Maximum number of result lines to return (default 100).

        Returns:
            List of dicts with keys: 'file', 'line_number', 'line_text'
            where 'file' is repository-relative path.

        Raises:
            ValueError: If query is empty or max_results <= 0.
        """
        if not query:
            raise ValueError("Query cannot be empty")
        if max_results <= 0:
            raise ValueError("max_results must be greater than 0")

        excluded_dirs = {
            ".git", ".hg",
            ".venv", "venv", "env",
            "__pycache__",
            ".pytest_cache", ".tox",
            "node_modules",
            ".egg-info", ".dist-info",
            ".mypy_cache", ".ruff_cache",
            "dist", "build",
            ".vs", ".idea",
        }

        results = []

        for file_path in sorted(self.root.rglob("*")):
            # Skip excluded directories
            if any(part in excluded_dirs for part in file_path.parts):
                continue

            # Process only regular files
            if not file_path.is_file():
                continue

            # Verify path is within repository
            if not file_path.is_relative_to(self.root.resolve()):
                continue

            # Try to read as UTF-8 text
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError):
                continue

            # Search line by line
            for line_num, line_text in enumerate(content.splitlines(), start=1):
                if query in line_text:
                    results.append({
                        "file": str(file_path.relative_to(self.root)),
                        "line_number": line_num,
                        "line_text": line_text.strip(),
                    })
                    if len(results) >= max_results:
                        return results

        return results
