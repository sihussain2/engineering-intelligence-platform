"""Milestone 5: Iterative Verification & Failure Recovery

This document describes the architecture and implementation of Milestone 5.

OVERVIEW
========

Milestone 5 transforms EIP from a simple "modify code, run tests, report result" system
into a sophisticated engineering agent that can recover from test failures through
diagnosis and corrective action.

Core workflow:
1. Investigate repository
2. Implement changes
3. Run tests
4. IF PASS: Review and evaluate
   ELSE: Diagnose failure, propose fix, retry
5. Produce structured result

CONTROL PRINCIPLE
=================

"Verification is iterative. The agent cannot succeed merely by making a change;
success requires that tests pass AND that the requirement is satisfied."

The agent's responsibility: Reason about code and propose solutions
EIP's responsibility: Control execution, validate changes, limit iterations

ARCHITECTURE
============

Test Result Enhancement
-----------------------

TestResult now includes:
  - failure_type: "test_failure" | "execution_error" | "timeout" | None
  - passed_count: Number of passing tests
  - failed_count: Number of failing tests
  - failed_tests: List of names of failed tests (e.g., "tests/test_app.py::test_feature")

This enables the LLM to understand not just "tests failed" but also:
  - Which specific tests failed
  - How many tests passed vs failed
  - What type of failure occurred

_parse_test_output() method extracts test counts and names from pytest output using regex.

Agent State Tracking
--------------------

AgentSession now tracks:
  - tests_passed: bool | None (unknown until first test run)
  - recovery_attempts: int (count of failures requiring fixes)
  - last_test_result: dict (complete result from last test execution)
  - modifications_made: list[str] (files that were modified)
  - engineering_result: EngineringResult | None (final structured result)

The agent can use this state to:
  - Determine if verification is complete (tests_passed == True)
  - Decide whether to continue after a failure (recovery_attempts < limit)
  - Understand which files were changed
  - Provide evidence in final result

Verification-Aware Prompts
--------------------------

SimpleAgent now generates two different system prompts:

1. First iteration (_get_verification_prompt(..., is_first_iteration=True)):
   - Explains full workflow: INVESTIGATE → PLAN → IMPLEMENT → VERIFY → REVIEW → EVALUATE
   - Warns about constraints (exact match, single occurrence)
   - Explains recovery loop: what to do if tests fail

2. Continuation iterations (_get_verification_prompt(..., is_first_iteration=False)):
   - Shorter, focused on recovery and iteration
   - Emphasizes: diagnose, understand, fix, retest
   - Maintains context about original requirement

This keeps tokens efficient while guiding the LLM appropriately.

Failure Recovery Loop
---------------------

When agent's test run returns failure:
  1. TestResult includes: failed_count, failed_tests, stdout, stderr
  2. LLM receives complete result as tool_result message
  3. LLM can:
     - Read failure output
     - Use read_file/search_code to inspect source
     - Use read_file/search_code to inspect tests
     - Propose diagnosis
  4. LLM requests modify_file with corrective change
  5. Loop continues until:
     - Tests pass (success) OR
     - Max iterations reached (verification_incomplete)

The loop is controlled by:
  - max_iterations in SimpleAgent (default 10)
  - Each iteration consumes 1 counter
  - recovery_attempts tracks how many failures encountered

Structured Result
-----------------

EngineringResult dataclass captures:
  
  status: RequirementStatus
    - SATISFIED: Tests pass, requirement addressed
    - PARTIALLY_SATISFIED: Progress made but incomplete
    - NOT_SATISFIED: No progress or wrong direction
    - VERIFICATION_INCOMPLETE: Max iterations reached without conclusion

  implementation: ImplementationSummary
    - files_changed: list of modified files
    - changes_description: summary of what was changed
    - modifications_attempted: count of modify_file calls
    - iterations_required: count of agent iterations

  verification: VerificationSummary
    - tests_passed: bool
    - test_summary: human-readable summary
    - total_tests_run: count
    - passed_count: count
    - failed_count: count
    - failures_diagnosed: list of failures encountered
    - recovery_attempts: count of recovery cycles

  review: ReviewFindings
    - requirement_addressed: bool
    - implementation_correct: bool
    - test_coverage_adequate: bool
    - risks: list of identified risks
    - limitations: list of limitations
    - recommendations: list of recommendations

  evidence: str (free-form evidence supporting conclusion)
  agent_reasoning: str (agent's final reasoning)

This structured result enables:
  - Clear pass/fail/incomplete determination
  - Full audit trail of what was attempted
  - Risk/limitation identification
  - Post-mortem analysis

IMPLEMENTATION DETAILS
======================

Files Modified:
  src/eip/repository/execution.py:
    - Enhanced TestResult dataclass
    - Added _parse_test_output() method
    - Updated run_tests() to populate new fields

  src/eip/llm/agent.py:
    - Enhanced AgentSession with verification tracking
    - Updated SimpleAgent with _get_verification_prompt()
    - Modified run() to use verification prompts
    - Added recovery_attempts increment on test failure

Files Created:
  src/eip/llm/verification.py:
    - RequirementStatus enum
    - ImplementationSummary dataclass
    - VerificationSummary dataclass
    - ReviewFindings dataclass
    - EngineringResult dataclass

  tests/test_execution_tool_enhanced.py (9 tests):
    - Verify failure_type classification
    - Verify test count extraction
    - Verify failed test identification
    - Verify timeout detection

  tests/test_agent_recovery.py (10 tests):
    - Test session state tracking
    - Test agent continuation after failure
    - Test max_iterations enforcement
    - Test verification prompts
    - Test EngineringResult model

  tests/run_recovery_workflow_test.py:
    - Live integration test with real Copilot LLM
    - Demonstrates full failure/recovery cycle

EXAMPLE WORKFLOW
================

Scenario: "Change MAX_RETRIES from 3 to 5 and ensure tests pass"

Repository:
  src/settings.py: MAX_RETRIES = 3
  tests/test_settings.py: assert MAX_RETRIES == 5

Execution:

  ITERATION 1:
    Agent: "I'll investigate the repository and make the required change."
    Tool: read_file("src/settings.py") → "MAX_RETRIES = 3"
    Tool: read_file("tests/test_settings.py") → "assert MAX_RETRIES == 5"
    Tool: modify_file(..., "MAX_RETRIES = 3", "MAX_RETRIES = 5")
    Tool: run_tests() 
    → TestResult(success=True, ...) or (success=False, ...)

  IF PASS:
    Agent: "Tests pass. The requirement is satisfied."
    Result: SATISFIED

  IF FAIL (e.g., syntax error introduced):
    Result: TestResult(
      success=False,
      failed_count=1,
      failed_tests=["tests/test_settings.py::test_max_retries"],
      stdout="...AssertionError: Expected...",
      failure_type="test_failure"
    )
    
    ITERATION 2:
      Agent: "Tests failed. Let me diagnose the issue."
      Tool: read_file("src/settings.py") → (sees what was actually written)
      Tool: search_code("MAX_RETRIES")
      Agent: "I see the problem. The value is actually 5 but the test still fails.
              Let me check the test more carefully."
      Tool: read_file("tests/test_settings.py")
      Agent: "Now I understand. I need to fix [specific issue]"
      Tool: modify_file(..., <old>, <new>)
      Tool: run_tests()
      → TestResult(success=True)

    ITERATION 3:
      Agent: "Tests now pass. Requirement satisfied."
      Result: SATISFIED with evidence and reasoning

SAFETY MECHANISMS
=================

1. Max Iterations:
   - Default: 10 iterations per requirement
   - Prevents infinite loops
   - If max reached: status = VERIFICATION_INCOMPLETE
   - Clear indication that verification is inconclusive

2. Single Occurrence Requirement:
   - Prevents ambiguous modifications
   - Agent must understand exact content to change
   - Forces precision (good for correctness, limits flexibility)

3. Exact Match Requirement:
   - No regex, no fuzzy matching
   - No partial replacements
   - Forces agent to understand full context

4. Path Validation:
   - All modifications must be inside repo root
   - Prevents /etc/passwd style attacks
   - Tests must be under repository

5. Subprocess Isolation:
   - Tests run in subprocess with timeout
   - 120-second limit prevents hanging
   - Cannot access arbitrary commands

6. Proof-of-execution:
   - Every modification returns evidence
   - Every test run returns complete output
   - Agent can verify results
   - No silent failures

TESTING STRATEGY
================

Unit Tests (test_execution_tool_enhanced.py):
  - TestResult captures failure types
  - TestResult distinguishes timeout
  - TestResult extracts test counts
  - TestResult tracks failed tests
  - Tool parsing works correctly

Agent Recovery Tests (test_agent_recovery.py):
  - Session tracks test status
  - Session counts recovery attempts
  - Session records modifications
  - Agent continues after failure
  - Agent respects max_iterations
  - Prompts guide verification workflow
  - EngineringResult serializes correctly

Live Integration Test (run_recovery_workflow_test.py):
  - Creates test repository with deliberate failure scenario
  - Runs agent with real Copilot LLM
  - Agent diagnoses and recovers from failure
  - Tests pass on retry
  - Full workflow evidence captured

KNOWN LIMITATIONS
=================

1. Recovery Limited by Iterations:
   - Max 10 iterations per task
   - Complex issues might need more
   - Future: Could increase for specific task types

2. Cannot Create/Delete Files:
   - Agent can only modify existing files
   - Cannot add new modules
   - Cannot remove unused code
   - Deferred to Milestone 6

3. Cannot Use Git:
   - Cannot create branches
   - Cannot make commits
   - Cannot file PRs
   - Deferred to Milestone 6

4. Test Failure Diagnosis Dependent on Output:
   - Agent must read test failure output carefully
   - Pytest output parsing is heuristic-based
   - Could miss subtle failures
   - Future: Could add structured test result parsing

5. Cannot Fix All Classes of Issues:
   - Logic errors that require architecture change
   - Performance issues
   - Security issues requiring multi-file coordination
   - Deferred to future milestones

ARCHITECTURAL DECISIONS
=======================

1. Reused max_iterations for Recovery:
   - Already had iteration limiting mechanism
   - Avoids introducing new safety concepts
   - Simple and well-understood

2. In-Memory Verification State:
   - No persistent storage
   - Session exists for lifetime of run() call
   - Reconstructed for each user request (like Copilot)
   - Simpler than state database

3. LLM Performs Diagnosis:
   - Not a separate diagnosis engine
   - LLM uses existing tools to understand
   - Leverages LLM's reasoning capabilities
   - Keeps system focused

4. Verification-Aware Prompts:
   - Guides LLM behavior without constraints
   - Different prompts for different stages
   - Efficient (shorter continuation prompts)
   - Easy to update/improve

5. Structured Result Without Repository Persistence:
   - Result is in-memory object
   - Can be serialized to JSON
   - Future: Could add persistence layer
   - Current: Sufficient for end-to-end demonstration

FUTURE ENHANCEMENTS
===================

Milestone 6 Could Add:
  1. File creation (create_file with smart defaults)
  2. File deletion (delete_file with safety checks)
  3. Git operations (commit, branch, PR)
  4. Approval workflow (human review before modification)
  5. Transactional rollback (modify_file with rollback)
  6. Test selection (run_tests with specific test filter)
  7. Structured approval results (not just success/fail)
  8. Audit logging (persistent record of all changes)

Milestone 7+ Could Add:
  1. Multi-file coordination (modify multiple files atomically)
  2. Sophisticated planning (AST analysis for code understanding)
  3. Specialized agents (test-generation agent, refactoring agent)
  4. Performance optimization (detect perf regressions)
  5. Security analysis (identify security issues)
  6. Comparison mode (compare two implementations)
"""
