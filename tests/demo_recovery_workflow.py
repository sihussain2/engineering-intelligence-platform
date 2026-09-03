"""
Focused live demo of Milestone 5 recovery workflow.

This script uses mock LLM responses to demonstrate the failure recovery
workflow without relying on Copilot API behavior.
"""

import tempfile
from pathlib import Path
from eip.repository.tool import RepositoryTool
from eip.llm.agent import SimpleAgent


class ControlledLLMClient:
    """LLM client with predefined response sequence for testing."""

    def __init__(self, recovery_scenario=True):
        self.call_count = 0
        self.recovery_scenario = recovery_scenario
        self.dispatcher = None

    def complete(self, messages, tools, system_prompt):
        """Return predefined responses to demonstrate recovery."""
        self.call_count += 1

        if self.recovery_scenario:
            # Scenario: First change is wrong, then correct it
            if self.call_count == 1:
                # Investigate
                return {
                    "content": "Let me investigate the repository structure.",
                    "tool_calls": [
                        {"tool_id": "repo.list_files", "arguments": {"path": "."}}
                    ],
                    "done": False,
                }
            elif self.call_count == 2:
                # Read the configuration file
                return {
                    "content": "I'll examine the settings file.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "src/settings.py"},
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 3:
                # First modification attempt - DELIBERATELY WRONG
                return {
                    "content": "I'll change MAX_RETRIES to 5.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "src/settings.py",
                                "old_content": "MAX_RETRIES = 3",
                                "new_content": "MAX_RETRIES = 10",  # WRONG!
                            },
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 4:
                # Run tests - will show failure
                return {
                    "content": "Now I'll run the tests to verify.",
                    "tool_calls": [
                        {"tool_id": "repo.run_tests", "arguments": {}}
                    ],
                    "done": False,
                }
            elif self.call_count == 5:
                # Analyze the failure
                return {
                    "content": "I see tests failed. The test expects MAX_RETRIES=5 but I set it to 10. Let me fix this.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.read_file",
                            "arguments": {"path": "tests/test_settings.py"},
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 6:
                # Corrective modification - RIGHT
                return {
                    "content": "Now I'll fix the value to 5 as required.",
                    "tool_calls": [
                        {
                            "tool_id": "repo.modify_file",
                            "arguments": {
                                "path": "src/settings.py",
                                "old_content": "MAX_RETRIES = 10",
                                "new_content": "MAX_RETRIES = 5",
                            },
                        }
                    ],
                    "done": False,
                }
            elif self.call_count == 7:
                # Retest - should pass
                return {
                    "content": "Re-running tests with the corrected value.",
                    "tool_calls": [
                        {"tool_id": "repo.run_tests", "arguments": {}}
                    ],
                    "done": False,
                }
            elif self.call_count == 8:
                # Final assessment
                return {
                    "content": """✅ **Task Complete - Recovery Successful**

**Problem Identification:**
- Initially changed MAX_RETRIES to 10 (incorrect)
- Tests failed because they expected 5

**Solution:**
- Diagnosed the issue by reading the test file
- Corrected MAX_RETRIES to exactly 5
- Verified the fix with tests

**Final Status:**
- ✓ Requirement satisfied: MAX_RETRIES changed from 3 to 5
- ✓ Tests passing: Both test_max_retries_is_five and test_get_retry_count pass
- ✓ No regressions: All tests in the suite pass

The recovery workflow succeeded: Failed → Diagnosed → Fixed → Verified""",
                    "tool_calls": [],
                    "done": True,
                }
        else:
            # Simple success scenario
            return {
                "content": "Task complete.",
                "tool_calls": [],
                "done": True,
            }


def create_test_repo(path: Path):
    """Create test repository."""
    (path / "src").mkdir()
    (path / "tests").mkdir()
    (path / "src" / "__init__.py").write_text("")
    (path / "src" / "settings.py").write_text("MAX_RETRIES = 3")
    (path / "tests" / "test_settings.py").write_text("""
def test_max_retries_is_five():
    from src.settings import MAX_RETRIES
    assert MAX_RETRIES == 5

def test_get_retry_count():
    from src.settings import MAX_RETRIES
    assert MAX_RETRIES == 5
""")


def run_demo():
    """Run recovery workflow demonstration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        create_test_repo(repo_path)

        print("\n" + "=" * 80)
        print("MILESTONE 5: FAILURE RECOVERY WORKFLOW")
        print("Controlled LLM Demonstration")
        print("=" * 80)
        print("\nScenario: Agent makes WRONG change, tests FAIL, agent FIXES it")
        print(f"\nRepository: {repo_path}")
        print("\nInitial state:")
        print(f"  src/settings.py: MAX_RETRIES = 3")
        print(f"  Target: MAX_RETRIES = 5")
        print(f"  Tests: Expect MAX_RETRIES == 5")

        # Create agent with controlled LLM
        repo_tool = RepositoryTool(repo_path)
        llm_client = ControlledLLMClient(recovery_scenario=True)
        agent = SimpleAgent(llm_client, repo_tool, max_iterations=15)

        requirement = "Change MAX_RETRIES from 3 to 5 and ensure all tests pass."
        print(f"\nRequirement: {requirement}")
        print("\nRunning agent...")
        print("-" * 80)

        session = agent.run(requirement)

        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\nIterations: {session.iterations}")
        print(f"Recovery attempts: {session.recovery_attempts}")
        print(f"Files modified: {session.modifications_made}")
        print(f"Tests passed: {session.tests_passed}")
        print(f"Final response:\n{session.final_response[:300]}")

        # Verify
        modified_content = (repo_path / "src" / "settings.py").read_text()
        has_correct_value = "MAX_RETRIES = 5" in modified_content
        print(f"\nFile correctly modified to MAX_RETRIES = 5: {has_correct_value}")
        print(f"Tests passed: {session.tests_passed}")

        # Show interaction sequence
        print("\n" + "=" * 80)
        print("INTERACTION SEQUENCE")
        print("=" * 80)
        messages_to_show = []
        for msg in session.messages:
            if msg.get("role") in ["user", "assistant"]:
                messages_to_show.append(msg)
            elif msg.get("name") == "tool":
                messages_to_show.append(msg)

        for i, msg in enumerate(messages_to_show[:15]):
            role = msg.get("role", "").upper() or msg.get("name", "").upper()
            content = msg.get("content", "")

            if isinstance(content, str):
                preview = content[:100] if len(content) > 100 else content
                print(f"\n{i+1}. {role}")
                print(f"   {preview}")
            elif isinstance(content, dict):
                success = content.get("success", "unknown")
                if content.get("tool_id") == "repo.run_tests":
                    print(f"\n{i+1}. {role} [TEST RESULT]")
                    print(f"   Success: {success}")
                    print(f"   Summary: {content.get('summary', '')}")
                else:
                    print(f"\n{i+1}. {role}")
                    print(f"   {str(content)[:100]}")

        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        success = has_correct_value and session.tests_passed
        if success:
            print("\n✅ RECOVERY SUCCESSFUL:")
            print("   - Agent made wrong change (MAX_RETRIES = 10)")
            print("   - Tests failed")
            print("   - Agent diagnosed: test expects 5, not 10")
            print("   - Agent corrected: MAX_RETRIES = 5")
            print("   - Tests passed")
        else:
            print("\n⚠ PARTIAL SUCCESS:")
            if has_correct_value:
                print("   - File correctly modified")
                if not session.tests_passed:
                    print("   - But tests show as failed (might be timing issue)")
            else:
                print("   - File was not correctly modified")

        return success


if __name__ == "__main__":
    success = run_demo()
    print("\n" + "=" * 80)
    if success:
        print("✅ Milestone 5 recovery workflow DEMONSTRATED SUCCESSFULLY")
    else:
        print("⚠ Demonstration completed (some issues to investigate)")
    print("=" * 80 + "\n")
