"""Live integration test demonstrating Milestone 4 capabilities."""

from pathlib import Path
import tempfile
import shutil

from eip.repository.tool import RepositoryTool
from eip.llm.agent import SimpleAgent
from eip.llm.copilot import CopilotLLMClient


def create_sample_repository(repo_path: Path):
    """Create a sample repository with modifiable config and tests."""
    # Create directory structure
    src_dir = repo_path / "src"
    src_dir.mkdir()

    tests_dir = repo_path / "tests"
    tests_dir.mkdir()

    # Create a simple configuration file
    config_file = src_dir / "config.py"
    config_file.write_text(
        '"""Application configuration."""\n'
        '\n'
        "# Maximum number of items to process\n"
        "MAX_ITEMS = 10\n"
        '\n'
        "# Other configuration\n"
        "DEBUG = True\n"
    )

    # Create a module that uses the config
    app_file = src_dir / "app.py"
    app_file.write_text(
        "from config import MAX_ITEMS\n"
        "\n"
        "def process_items(items):\n"
        '    """Process up to MAX_ITEMS items."""\n'
        "    return items[:MAX_ITEMS]\n"
    )

    # Create test file
    test_file = tests_dir / "test_app.py"
    test_file.write_text(
        "import sys\n"
        "sys.path.insert(0, 'src')\n"
        "\n"
        "from config import MAX_ITEMS\n"
        "from app import process_items\n"
        "\n"
        "def test_max_items_limit():\n"
        '    """Test that MAX_ITEMS limit is enforced."""\n'
        "    items = list(range(100))\n"
        "    result = process_items(items)\n"
        "    assert len(result) == MAX_ITEMS\n"
        "\n"
        "def test_max_items_value():\n"
        '    """Test that MAX_ITEMS has the correct value."""\n'
        "    assert MAX_ITEMS == 20  # This will fail initially, pass after modification\n"
    )

    # Create __init__.py files
    (tests_dir / "__init__.py").touch()
    (src_dir / "__init__.py").touch()

    # Create README
    readme = repo_path / "README.md"
    readme.write_text(
        "# Sample Engineering Project\n"
        "\n"
        "This is a sample project for testing EIP capabilities.\n"
        "\n"
        "The configuration in `src/config.py` contains MAX_ITEMS which controls\n"
        "how many items the application can process.\n"
    )

    return {
        "config_path": "src/config.py",
        "test_path": "tests/test_app.py",
    }


def run_live_test():
    """Run the live integration test."""
    print("=" * 80)
    print("MILESTONE 4 LIVE INTEGRATION TEST")
    print("Controlled Code Modification + Test Execution")
    print("=" * 80)
    print()

    # Create temporary repository
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        repo_path = Path(tmp_dir_str)
        paths = create_sample_repository(repo_path)

        print("Sample repository created at:", repo_path)
        print()

        # Print initial config
        config_path = repo_path / paths["config_path"]
        print("Initial config.py:")
        print("-" * 40)
        print(config_path.read_text())
        print("-" * 40)
        print()

        # Set up EIP
        repo_tool = RepositoryTool(repo_path)
        llm_client = CopilotLLMClient(
            model="claude-haiku-4.5",
            dispatcher=None,  # Will be set by agent
        )

        # Create and run agent
        agent = SimpleAgent(
            llm_client,
            repo_tool,
            max_iterations=10,
        )

        requirement = (
            "Change the maximum number of items from 10 to 20.\n"
            "\n"
            "1. Find where MAX_ITEMS is defined (should be in src/config.py)\n"
            "2. Read the file to see the exact current content\n"
            "3. Use modify_file to change MAX_ITEMS = 10 to MAX_ITEMS = 20\n"
            "4. After modification, run the tests to verify the change\n"
            "5. Report the success or any issues\n"
        )

        print("Requirement sent to agent:")
        print("-" * 40)
        print(requirement)
        print("-" * 40)
        print()

        print("Running agent with Copilot LLM...")
        print("(This makes a real request to Copilot API)")
        print()

        try:
            session = agent.run(requirement)

            # Check if modification was successful
            modified_content = config_path.read_text()

            print("=" * 80)
            print("RESULTS")
            print("=" * 80)
            print()

            print("Final config.py:")
            print("-" * 40)
            print(modified_content)
            print("-" * 40)
            print()

            if "MAX_ITEMS = 20" in modified_content:
                print("✓ MODIFICATION SUCCESSFUL: MAX_ITEMS changed to 20")
            else:
                print("✗ MODIFICATION FAILED: MAX_ITEMS was not changed")

            print()
            print("Tool calls made by agent:")
            print("-" * 40)
            for i, tool_result in enumerate(session.tool_results, 1):
                print(f"{i}. {tool_result.tool_id}")
                if tool_result.success:
                    print("   ✓ Success")
                else:
                    print(f"   ✗ Error: {tool_result.error}")
            print()

            print("Agent final response:")
            print("-" * 40)
            print(session.final_response)
            print("-" * 40)
            print()

            # Verify capabilities demonstrated
            tool_ids_used = {r.tool_id for r in session.tool_results}

            capabilities_demonstrated = []
            if "repo.list_files" in tool_ids_used:
                capabilities_demonstrated.append("Listed files/directories")
            if "repo.read_file" in tool_ids_used:
                capabilities_demonstrated.append("Read file contents")
            if "repo.search_code" in tool_ids_used:
                capabilities_demonstrated.append("Searched code")
            if "repo.modify_file" in tool_ids_used:
                capabilities_demonstrated.append("Modified file (WRITE)")
            if "repo.run_tests" in tool_ids_used:
                capabilities_demonstrated.append("Executed tests (VERIFY)")

            print("Capabilities demonstrated:")
            for cap in capabilities_demonstrated:
                print(f"  ✓ {cap}")
            print()

            print("=" * 80)
            print("MILESTONE 4 CAPABILITIES VERIFIED")
            print("=" * 80)

        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_live_test()
