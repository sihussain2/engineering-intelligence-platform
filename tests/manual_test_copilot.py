#!/usr/bin/env python3
"""
Manual integration test for CopilotLLMClient.

This test makes a REAL request to GitHub Copilot and requires:
1. An active GitHub Copilot subscription
2. Local Copilot CLI authentication (or COPILOT_GITHUB_TOKEN env var)
3. Network connectivity to Copilot service

This is NOT part of the normal pytest suite and must be run manually:

    python tests/manual_test_copilot.py

OR from the command line:

    python -c "from tests.manual_test_copilot import main; main()"

The test is intentionally NOT included in pytest's automatic test discovery
to avoid failing on CI/CD systems that don't have Copilot access.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from eip.llm.copilot import CopilotLLMClient


def main():
    """Run manual integration test."""
    print("\n" + "=" * 80)
    print("Manual Copilot LLMClient Integration Test")
    print("=" * 80)
    print()

    # Initialize client
    print("1. Initializing CopilotLLMClient...")
    client = CopilotLLMClient(model="claude-haiku-4.5")
    print("   ✓ Client initialized")
    print()

    # Prepare message
    user_message = "Explain in one paragraph what the Engineering Intelligence Platform is."
    print("2. Sending request to Copilot:")
    print(f"   User: {user_message}")
    print()

    # Make request
    print("3. Waiting for Copilot response...")
    print("   (This may take 5-10 seconds...)")
    print()

    try:
        result = client.complete(
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        )

        # Display result
        print("4. Response received:")
        print("-" * 80)
        print(result["content"])
        print("-" * 80)
        print()

        # Verify response format
        print("5. Response structure validation:")
        print(f"   content (str): {len(result['content'])} characters")
        print(f"   tool_calls: {result['tool_calls']}")
        print(f"   done: {result['done']}")
        print()

        # Validate that we got actual content (not empty/whitespace)
        if not result["content"] or not result["content"].strip():
            print("❌ Manual integration test FAILED")
            print("Reason: Empty or whitespace-only response from Copilot")
            print("=" * 80)
            return 1

        # Success
        print("✅ Manual integration test PASSED")
        print("=" * 80)
        return 0

    except Exception as e:
        print()
        print("❌ Manual integration test FAILED")
        print(f"Error: {type(e).__name__}: {e}")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
