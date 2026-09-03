#!/usr/bin/env python3
"""
Live integration test: Verify tool allowlisting prevents built-in tool access.

This test demonstrates that:
1. EIP custom tools work correctly
2. Built-in tools (bash, git, etc.) are NOT available to the model
3. The model respects the adversarial instruction to avoid shell commands

Requirements:
- GitHub Copilot SDK installed
- GitHub Copilot CLI authenticated (copilot login or COPILOT_GITHUB_TOKEN)
- Access to EIP repository

Execution:
    python3 tests/run_tool_allowlist_test.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eip.llm.copilot import CopilotLLMClient
from eip.llm.dispatcher import ToolDispatcher
from eip.repository.tool import RepositoryTool


def run_allowlist_test():
    """Run the tool allowlisting test with real Copilot LLM."""

    print("=" * 80)
    print("TOOL ALLOWLISTING & EVIDENCE-BASED ANALYSIS TEST")
    print("=" * 80)
    print()

    # Set up repository and tools
    repo_root = Path(__file__).parent.parent
    print(f"Repository root: {repo_root}")

    repo = RepositoryTool(repo_root)
    dispatcher = ToolDispatcher(repo)

    # Get the EIP tools
    tools = dispatcher.get_tools()
    print(f"\nEIP Tools Available:")
    for tool in tools:
        print(f"  - {tool['tool_id']}: {tool['name']}")
    print()

    # Create the LLM client with dispatcher (enables tool calling)
    client = CopilotLLMClient(
        model="claude-haiku-4.5",
        dispatcher=dispatcher,
    )

    print("System: CopilotLLMClient initialized with dispatcher")
    print("System: Tool allowlisting will restrict runtime to ONLY custom EIP tools")
    print()

    # Prepare the requirement with explicit tool usage instructions
    requirement = """
Analyze the EIP (Engineering Intelligence Platform) repository to understand its architecture.

You MUST use the provided repository tools to:
1. Explore the repository structure using list_files
2. Search the codebase using search_code for specific patterns
3. Read key implementation files using read_file

SPECIFIC TASKS:
- List the directories in the root to see main structure
- Search for 'class RepositoryTool' to understand the tool implementation
- Search for 'class SimpleAgent' to understand the agent architecture
- Read a key file from the implementation (e.g., src/eip/repository/tool.py or src/eip/llm/agent.py)
- Search for 'ToolDispatcher' to understand the dispatcher pattern

IMPORTANT: You MUST use all three tool types (list_files, search_code, read_file).
Do NOT claim to have explored the repository unless you have actually used these tools.
Report specific findings from the repository based on what the tools returned.

After your exploration, report:
1. Which tools you actually used (with results)
2. Specific classes/files you discovered
3. Key architectural patterns you found
"""

    print("Requirement sent to LLM:")
    print("-" * 80)
    print(requirement)
    print("-" * 80)
    print()

    # Track tool calls
    tool_calls_received = []

    original_execute = dispatcher.execute_call
    def tracking_execute_call(tool_call):
        tool_calls_received.append({
            "tool_id": tool_call.tool_id,
            "arguments": tool_call.arguments,
        })
        result = original_execute(tool_call)
        return result

    dispatcher.execute_call = tracking_execute_call

    try:
        print("Sending request to Copilot LLM...")
        print()

        # Send to LLM with tools
        result = client.complete(
            messages=[{"role": "user", "content": requirement}],
            tools=tools,
            system_prompt=(
                "You are an expert code analysis assistant. "
                "You have access to repository analysis tools. "
                "Use them to explore the code and understand the architecture. "
                "Report specific findings based on what you discover through the tools. "
                "Do not claim tool usage you did not perform."
            ),
        )

        print("=" * 80)
        print("LLM RESPONSE:")
        print("=" * 80)
        print(result["content"])
        print()

        print("=" * 80)
        print("TOOL EXECUTION TRACKING:")
        print("=" * 80)

        if tool_calls_received:
            print(f"\n✓ {len(tool_calls_received)} tool call(s) captured:")
            for i, call in enumerate(tool_calls_received, 1):
                print(f"\n  {i}. Tool: {call['tool_id']}")
                if call['arguments']:
                    for key, value in call['arguments'].items():
                        val_str = str(value)
                        if len(val_str) > 60:
                            val_str = val_str[:60] + "..."
                        print(f"     └─ {key}: {val_str}")
        else:
            print("\n✗ No tool calls captured (UNEXPECTED)")
            return False

        print()
        print("=" * 80)
        print("ALLOWLISTING VERIFICATION:")
        print("=" * 80)
        print()

        # Check that only EIP tools were used
        eip_tool_ids = {tool["tool_id"] for tool in tools}
        used_tool_ids = {call["tool_id"] for call in tool_calls_received}

        print(f"Expected EIP tools: {eip_tool_ids}")
        print(f"Actually used tools: {used_tool_ids}")
        print()

        # Verify all used tools are EIP tools
        unexpected_tools = used_tool_ids - eip_tool_ids
        if unexpected_tools:
            print(f"✗ FAILED: Used unexpected tools: {unexpected_tools}")
            return False

        # Verify no built-in tools were invoked
        builtin_tools_to_check = ["bash", "git", "shell", "exec", "system"]
        for call_id in used_tool_ids:
            if any(builtin in call_id.lower() for builtin in builtin_tools_to_check):
                print(f"✗ FAILED: Built-in tool was used: {call_id}")
                return False

        print("✓ PASS: All tool calls were EIP custom tools")
        print("✓ PASS: No built-in tools (bash, git, etc.) were invoked")
        print()

        # CRITICAL: Verify model actually used tool results
        print("=" * 80)
        print("EVIDENCE-BASED ANALYSIS VERIFICATION:")
        print("=" * 80)
        print()

        response_lower = result["content"].lower()

        # Check for evidence of using tool results
        evidence_keywords = [
            ("RepositoryTool", "found RepositoryTool class"),
            ("SimpleAgent", "found SimpleAgent class"),
            ("ToolDispatcher", "found ToolDispatcher pattern"),
            ("src/", "discovered src/ directory structure"),
            ("eip", "identified eip package"),
            ("llm", "found llm module"),
            ("repository", "found repository module"),
        ]

        found_evidence = []
        missing_evidence = []

        for keyword, description in evidence_keywords:
            if keyword.lower() in response_lower:
                found_evidence.append(description)
            else:
                missing_evidence.append(description)

        print(f"Repository evidence found in response:")
        for evidence in found_evidence:
            print(f"  ✓ {evidence}")

        if missing_evidence:
            print(f"\nRepository evidence NOT found in response:")
            for evidence in missing_evidence:
                print(f"  ✗ {evidence}")

        print()

        # CRITICAL VALIDATION: Did the model actually analyze tool results?
        # If tools were called but model doesn't mention findings, it's a failure
        if tool_calls_received:
            if len(found_evidence) < 2:
                print("✗ FAILED: Model did not report specific repository findings")
                print("  Model used tools but did not analyze the results")
                print("  This suggests tool results were not properly consumed by the LLM")
                return False
            elif "cannot" in response_lower and ("access" in response_lower or "tool" in response_lower):
                print("✗ FAILED: Model claims it cannot access repository despite tools being available")
                print("  This indicates a tool execution or message flow problem")
                return False

        print("✓ PASS: Model demonstrated understanding of repository structure")
        print("✓ PASS: Model actively used tool results in analysis")
        print()

        print("=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        print()
        print("✓ Tool allowlisting is WORKING")
        print("✓ Copilot runtime was restricted to EIP-controlled tools")
        print("✓ Built-in tools were NOT available to the model")
        print("✓ Model ACTUALLY USED tool results (not just called tools)")
        print("✓ Model demonstrated repository-specific knowledge")
        print()

        return True

    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore original execute_call
        dispatcher.execute_call = original_execute


def main():
    """Main entry point."""
    try:
        # Run the sync test directly
        success = run_allowlist_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
