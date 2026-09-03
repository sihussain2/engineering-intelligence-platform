"""Live integration test for Milestone 5 recovery workflow with real Copilot LLM."""

import tempfile
from pathlib import Path
from eip.repository.tool import RepositoryTool
from eip.llm.agent import SimpleAgent
from eip.llm.copilot import CopilotLLMClient


def create_recovery_test_repository(repo_path: Path) -> dict:
    """
    Create a small test repository for recovery workflow.
    
    Scenario: Agent needs to change a constant from one value to another.
    Test initially configured to validate the NEW value.
    This ensures tests fail on initial (wrong) implementation attempt.
    
    Returns:
        Dict with scenario details
    """
    # Create directory structure
    (repo_path / "src").mkdir()
    (repo_path / "tests").mkdir()
    
    # Create application code
    (repo_path / "src" / "__init__.py").write_text("")
    (repo_path / "src" / "settings.py").write_text('''"""Application settings."""

# The number of retries for failed operations
MAX_RETRIES = 3

def get_retry_count():
    """Get the configured number of retries."""
    return MAX_RETRIES
''')
    
    # Create test that validates the CORRECT (target) value
    (repo_path / "tests" / "test_settings.py").write_text('''"""Tests for settings."""

def test_max_retries_is_five():
    """Verify MAX_RETRIES is set to 5 (the target value)."""
    from src.settings import MAX_RETRIES
    assert MAX_RETRIES == 5, f"Expected MAX_RETRIES=5 but got {MAX_RETRIES}"

def test_get_retry_count():
    """Verify get_retry_count returns the correct value."""
    from src.settings import get_retry_count
    count = get_retry_count()
    assert count == 5, f"Expected 5 retries but got {count}"
''')
    
    # Create pytest config to run from repo root
    (repo_path / "pytest.ini").write_text('''[pytest]
testpaths = tests
python_files = test_*.py
''')
    
    return {
        "scenario": "Change MAX_RETRIES from 3 to 5",
        "implementation_file": "src/settings.py",
        "test_file": "tests/test_settings.py",
        "initial_value": "MAX_RETRIES = 3",
        "target_value": "MAX_RETRIES = 5",
        "description": "Update retry configuration and ensure tests pass",
    }


def run_live_recovery_test():
    """
    Run live integration test with real Copilot LLM.
    
    Demonstrates:
    1. Agent receives requirement
    2. Agent investigates repository
    3. Agent makes initial modification
    4. Agent runs tests
    5. Tests FAIL because agent incorrectly modified the value
    6. Agent diagnoses the failure
    7. Agent makes corrective modification
    8. Agent runs tests again
    9. Tests PASS
    10. Agent produces final result with evidence
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        scenario = create_recovery_test_repository(repo_path)
        
        print("\n" + "=" * 80)
        print("MILESTONE 5: FAILURE RECOVERY WORKFLOW")
        print("Real Copilot LLM Integration Test")
        print("=" * 80)
        print(f"\nTest Repository: {repo_path}")
        print(f"Scenario: {scenario['scenario']}")
        print(f"\nRepository structure:")
        print(f"  {scenario['implementation_file']}")
        print(f"    Initial: {scenario['initial_value']}")
        print(f"    Target:  {scenario['target_value']}")
        print(f"  {scenario['test_file']}")
        
        # Create agent with Copilot LLM
        repo_tool = RepositoryTool(repo_path)
        llm_client = CopilotLLMClient()
        agent = SimpleAgent(llm_client, repo_tool, max_iterations=15)
        
        # Run agent
        print(f"\nLaunching agent with requirement:")
        requirement = f"""{scenario['scenario']}.

Details:
- The file {scenario['implementation_file']} currently has {scenario['initial_value']}.
- It should be changed to {scenario['target_value']}.
- Tests in {scenario['test_file']} validate that the change is correct.

Instructions:
1. Investigate the repository and understand the current state.
2. Identify the exact line that needs to change.
3. Make the modification using modify_file.
4. Run the tests to verify.
5. If tests fail, inspect the failure, diagnose the issue, and make a corrective modification.
6. Keep iterating until tests pass.
7. Once tests pass, review the implementation and provide a final assessment."""
        print(f"\n{requirement}")
        
        print("\n" + "-" * 80)
        print("Running agent (connecting to Copilot LLM)...")
        print("-" * 80)
        
        session = agent.run(requirement)
        
        # Report results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\nIterations: {session.iterations}/{agent.max_iterations}")
        print(f"Recovery attempts: {session.recovery_attempts}")
        print(f"Modifications made: {len(session.modifications_made)}")
        if session.modifications_made:
            for file in session.modifications_made:
                print(f"  - {file}")
        
        print(f"\nFinal test status: {session.tests_passed}")
        print(f"Last test result: {session.last_test_result}")
        
        print("\nAgent's final response:")
        print("-" * 80)
        if session.final_response:
            print(session.final_response[:500])
            if len(session.final_response) > 500:
                print("...")
        else:
            print("(No final response)")
        
        # Show execution evidence (Milestone 5: tool visibility)
        print("\n" + "=" * 80)
        print("EXECUTION EVIDENCE (Milestone 5 - Tool Visibility)")
        print("=" * 80)
        print(f"\nTotal tool results recorded: {len(session.tool_results)}")
        
        modify_file_calls = [
            r for r in session.tool_results
            if r.tool_id == "repo.modify_file"
        ]
        run_tests_calls = [
            r for r in session.tool_results
            if r.tool_id == "repo.run_tests"
        ]
        
        print(f"  repo.modify_file calls: {len(modify_file_calls)}")
        print(f"  repo.run_tests calls: {len(run_tests_calls)}")
        
        if session.tool_results:
            print("\nTool execution timeline:")
            for i, result in enumerate(session.tool_results, 1):
                status = "✓" if result.success else "✗"
                print(f"  {i}. [{status}] {result.tool_id}")
                if result.tool_id == "repo.run_tests" and result.result:
                    test_result = result.result
                    if isinstance(test_result, dict):
                        passed = test_result.get("passed", "?")
                        failed = test_result.get("failed", "?")
                        print(f"       Passed: {passed}, Failed: {failed}")
                if result.error:
                    print(f"       Error: {result.error}")
        
        # Verify the implementation
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        modified_content = (repo_path / "src" / "settings.py").read_text()
        has_target_value = "MAX_RETRIES = 5" in modified_content
        
        print(f"\nTarget value in file: {'✓ YES' if has_target_value else '✗ NO'}")
        print(f"Tests passed: {'✓ YES' if session.tests_passed else '✗ NO'}")
        print(f"Tool execution visible: {'✓ YES' if len(session.tool_results) > 0 else '✗ NO'}")
        print(f"Modifications tracked: {'✓ YES' if len(session.modifications_made) > 0 else '✗ NO'}")
        
        # Enhanced verdict with full evidence checklist
        evidence_items = [
            ("File modified to target value", has_target_value),
            ("Tests eventually passed", session.tests_passed),
            ("Tool calls recorded", len(session.tool_results) > 0),
            ("Modifications tracked in session", len(session.modifications_made) > 0),
            ("Multiple iterations for recovery", session.iterations > 1),
            ("Recovery attempts recorded", session.recovery_attempts > 0),
        ]
        
        print("\nEvidence checklist:")
        for item, status in evidence_items:
            print(f"  {'✓' if status else '✗'} {item}")
        
        all_passed = all(status for _, status in evidence_items)
        
        if all_passed:
            print("\n✓ SUCCESS: Agent recovered from failure with full execution visibility!")
        elif has_target_value and session.tests_passed:
            print("\n⚠ PARTIAL: Requirement satisfied but not all execution evidence captured.")
        elif has_target_value:
            print("\n⚠ PARTIAL: File modified correctly but tests show as failed.")
        else:
            print("\n✗ FAILED: Modification not successful or not the target value.")
        
        # Show message sequence
        print("\n" + "=" * 80)
        print("INTERACTION TRANSCRIPT")
        print("=" * 80)
        print("\nConversation history:")
        for i, msg in enumerate(session.messages[:10]):  # First 10 messages
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            tool_info = ""
            if msg.get("name") == "tool":
                tool_result = msg.get("content", "")
                if isinstance(tool_result, dict):
                    if tool_result.get("success") is False:
                        tool_info = " [TOOL ERROR/FAILURE]"
                    else:
                        tool_info = " [TOOL SUCCESS]"
            print(f"\n{i+1}. {role}{tool_info}")
            if len(content) > 150:
                print(f"   {content[:150]}...")
            else:
                print(f"   {content}")
        
        if len(session.messages) > 10:
            print(f"\n... ({len(session.messages) - 10} more messages)")
        
        return {
            "success": has_target_value and session.tests_passed,
            "tests_passed": session.tests_passed,
            "file_modified": has_target_value,
            "iterations": session.iterations,
            "recovery_attempts": session.recovery_attempts,
            "modifications": session.modifications_made,
            "scenario": scenario,
        }


if __name__ == "__main__":
    result = run_live_recovery_test()
    
    # Exit with appropriate code
    exit(0 if result["success"] else 1)
