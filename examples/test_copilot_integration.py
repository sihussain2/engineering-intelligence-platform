"""
Integration test example for GitHub Copilot SDK adapter.

This module is NOT included in the standard pytest suite because it requires
real GitHub authentication and makes actual Copilot API calls.

To run this test manually:
    1. Ensure you have GitHub Copilot CLI authenticated:
       $ copilot login
    2. Export the adapter if not already installed:
       $ export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    3. Run this specific test:
       $ python -m pytest examples/test_copilot_integration.py -v -s

Requirements:
    - Active GitHub Copilot subscription
    - GitHub Copilot CLI installed and authenticated
    - Internet connection to reach Copilot service
"""

import os

import pytest

from eip.llm.copilot import CopilotLLMClient
from eip.llm.dispatcher import ToolDispatcher
from eip.repository.tool import RepositoryTool


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("RUN_COPILOT_INTEGRATION"),
    reason="Set RUN_COPILOT_INTEGRATION=1 to run integration tests",
)
class TestCopilotIntegration:
    """Integration tests against real Copilot service."""

    def test_copilot_simple_completion(self, tmp_path):
        """Test basic completion with real Copilot."""
        # Skip if no auth available
        if not self._has_copilot_auth():
            pytest.skip("No Copilot authentication available")

        client = CopilotLLMClient(model="gpt-5")
        messages = [
            {"role": "user", "content": "What is the capital of France?"}
        ]

        result = client.complete(messages)

        # Verify result structure
        assert "content" in result
        assert "tool_calls" in result
        assert "done" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        assert result["done"] is True

        # Verify content is reasonable
        assert "Paris" in result["content"] or "france" in result["content"].lower()

    def test_copilot_with_repository_tools(self, tmp_path):
        """Test Copilot with repository access tools."""
        if not self._has_copilot_auth():
            pytest.skip("No Copilot authentication available")

        # Create a simple test repository
        (tmp_path / "test.py").write_text("def hello():\n    print('Hello')\n")
        (tmp_path / "README.md").write_text("# Test Project\n")

        # Set up tools
        repo_tool = RepositoryTool(tmp_path)
        dispatcher = ToolDispatcher(repo_tool)

        # Create client
        client = CopilotLLMClient(model="gpt-5")

        # Request with tools
        messages = [
            {
                "role": "user",
                "content": "What files are in this repository?",
            }
        ]

        # Get tool definitions
        tools = dispatcher.get_tools()

        result = client.complete(messages, tools=tools)

        # Verify result
        assert result["done"] is True
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0

    def test_copilot_multi_turn_conversation(self, tmp_path):
        """Test multi-turn conversation with Copilot."""
        if not self._has_copilot_auth():
            pytest.skip("No Copilot authentication available")

        client = CopilotLLMClient(model="gpt-5")

        # First turn
        messages = [
            {"role": "user", "content": "What is Python?"}
        ]
        result1 = client.complete(messages)
        assert result1["done"] is True

        # Second turn - add assistant response and new user message
        messages.append({"role": "assistant", "content": result1["content"]})
        messages.append(
            {"role": "user", "content": "What are its main features?"}
        )

        result2 = client.complete(messages)
        assert result2["done"] is True
        assert isinstance(result2["content"], str)

    def test_copilot_with_system_prompt(self, tmp_path):
        """Test Copilot with custom system prompt."""
        if not self._has_copilot_auth():
            pytest.skip("No Copilot authentication available")

        client = CopilotLLMClient(model="gpt-5")
        messages = [
            {"role": "user", "content": "Say hello in French"}
        ]
        system_prompt = (
            "You are a helpful assistant that only responds in one sentence."
        )

        result = client.complete(
            messages, system_prompt=system_prompt
        )

        assert result["done"] is True
        # Count sentences (approximate)
        sentences = result["content"].count(".") + result["content"].count("!")
        assert sentences <= 2  # Allow for some tolerance

    @staticmethod
    def _has_copilot_auth() -> bool:
        """Check if Copilot authentication is available."""
        # Check for environment variables
        auth_env_vars = [
            "COPILOT_GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ]
        return any(os.environ.get(var) for var in auth_env_vars)


# Standalone integration test functions that can be run directly
def manual_test_copilot_simple():
    """
    Manual integration test - run with:
        python examples/test_copilot_integration.py
    """
    print("\n=== Manual Copilot Integration Test ===")
    print("Testing basic completion...")

    try:
        client = CopilotLLMClient(model="gpt-5")
        messages = [
            {"role": "user", "content": "Hello! What can you help me with?"}
        ]

        result = client.complete(messages)

        print(f"✓ Completion succeeded")
        print(f"  Content: {result['content'][:100]}...")
        print(f"  Done: {result['done']}")
        print(f"  Tool calls: {result['tool_calls']}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Allow running as a manual test script
    import sys

    if "manual" in sys.argv:
        manual_test_copilot_simple()
    else:
        print(
            "Run with pytest: python -m pytest examples/test_copilot_integration.py -v"
        )
        print(
            "Or set RUN_COPILOT_INTEGRATION=1 to enable integration tests in CI"
        )
