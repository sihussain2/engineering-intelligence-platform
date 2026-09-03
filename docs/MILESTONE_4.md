"""
MILESTONE 4: CONTROLLED ENGINEERING EXECUTION

Architecture extension for controlled code modification and test execution.

========================================================
OVERVIEW
========================================================

Milestone 4 extends EIP from read-only repository analysis into controlled
engineering execution. The platform now supports:

1. READ operations (Milestone 1-3):
   - list_files: List repository structure
   - read_file: Read file contents
   - search_code: Search for patterns in code

2. WRITE operations (NEW - Milestone 4):
   - modify_file: Make controlled file modifications

3. VERIFY operations (NEW - Milestone 4):
   - run_tests: Execute the project's test suite

All operations are strictly controlled by EIP and follow the principle:
"The agent proposes; EIP validates and executes."

========================================================
CONTROL PRINCIPLE
========================================================

The engineering agent does NOT have direct access to:
- Arbitrary shell commands
- Arbitrary file writes
- Arbitrary file deletes
- git operations (deferred to later milestone)
- Network operations

Instead, the agent:
1. Inspects the repository (READ tools)
2. Identifies the necessary changes (analysis)
3. REQUESTS modifications through controlled tools (WRITE tools)
4. EIP validates and executes the modification
5. Agent receives structured evidence of what changed
6. Agent may request test execution (VERIFY tools)
7. Agent receives test results
8. Agent produces final response

========================================================
ARCHITECTURE DIAGRAM
========================================================

Milestone 1-3 (Read-only):
  Requirement
    ↓
  RepositoryAnalyst
    ↓
  SimpleAgent
    ↓
  LLMClient
    ↕ (tool calls)
  ToolDispatcher
    ↓
  RepositoryTool
    ├── list_files
    ├── read_file
    └── search_code

Milestone 4 (Read + Write + Verify):
  Requirement
    ↓
  Agent inspects (READ)
    ↓
  Agent identifies location
    ↓
  Agent requests modification (WRITE)
    ↓
  EIP validates & executes
    ↓
  Agent receives evidence
    ↓
  Agent may request tests (VERIFY)
    ↓
  Agent receives test results
    ↓
  Agent generates final response

  LLMClient
    ↕ (tool calls)
  ToolDispatcher
    ├── RepositoryTool (READ)
    │   ├── list_files
    │   ├── read_file
    │   └── search_code
    │
    ├── RepositoryModificationTool (WRITE)
    │   └── modify_file
    │
    └── TestExecutionTool (VERIFY)
        └── run_tests

========================================================
TOOL SPECIFICATIONS
========================================================

READ TOOLS (Unchanged from Milestone 3)
--------------------------------------

1. repo.list_files(path: str = ".") -> list[str]
   Lists files and directories under a repository path.
   Always returns relative paths from repository root.

2. repo.read_file(path: str) -> str
   Reads complete text contents of a file.
   Returns UTF-8 text.
   Rejects directories.

3. repo.search_code(query: str, max_results: int = 100) -> list[dict]
   Searches source files for text patterns (case-sensitive).
   Returns: file, line_number, line_text
   Automatically excludes build artifacts, caches, venv, etc.

WRITE TOOLS (New in Milestone 4)
--------------------------------

1. repo.modify_file(path: str, old_content: str, new_content: str)
   -> ModificationResult

   Modifies a file by replacing exact content.
   
   Validation (strictly enforced):
   - Path must be inside repository root
   - File must exist
   - old_content must match exactly (case-sensitive)
   - old_content must occur exactly once (no ambiguity)
   - Rejected if 0 occurrences (content not found)
   - Rejected if >1 occurrence (too ambiguous)
   - Only after ALL validation succeeds, file is modified
   
   Result includes:
   - success: boolean
   - path: modified file path
   - operation: "replace"
   - changes: 1 (always, for successful calls)
   - old_content: what was replaced
   - new_content: what replaced it
   - error: error message if failed
   
   Agent receives full evidence of the change, allowing
   accurate reporting and subsequent verification.

VERIFY TOOLS (New in Milestone 4)
---------------------------------

1. repo.run_tests(test_path: str = None) -> TestResult

   Executes the repository's pytest test suite.
   
   Arguments:
   - test_path: optional relative path to specific test file/directory
                If None, runs entire test suite
   - Must be inside repository root
   
   Result includes:
   - success: test suite passed (exit code 0)
   - exit_code: pytest exit code
   - stdout: complete test output
   - stderr: error output if any
   - summary: human-readable summary
               e.g., "✓ Tests passed: X passed in Y.XXs"
                     "✗ Tests failed: 1 failed in Y.XXs"
   
   Agent can:
   - Request full test suite run
   - Request specific test file/directory run
   - Receive complete results including failures
   - Continue reasoning based on test results

========================================================
IMPLEMENTATION DETAILS
========================================================

File Structure:
  src/eip/repository/
    tool.py                    (READ - unchanged)
    modification.py            (WRITE - new)
    execution.py               (VERIFY - new)
  
  src/eip/llm/
    tools.py                   (Tool definitions - updated)
    dispatcher.py              (Routing logic - updated)
    agent.py                   (Agent loop - no changes needed)

Modification Tool (src/eip/repository/modification.py):
  class RepositoryModificationTool:
    def __init__(root: Path)
    def modify_file(path: str, old_content: str, new_content: str)
      -> ModificationResult
  
  Validation steps:
  1. Resolve path relative to repository root
  2. Check path is inside repository
  3. Check file exists and is a file (not directory)
  4. Read current file contents
  5. Count occurrences of old_content
  6. Reject if count != 1
  7. Only if count == 1: perform replacement
  8. Write modified file
  9. Return structured evidence

Test Execution Tool (src/eip/repository/execution.py):
  class TestExecutionTool:
    def __init__(root: Path)
    def run_tests(test_path: str = None) -> TestResult
  
  Implementation:
  - Runs pytest via subprocess
  - Captures stdout/stderr
  - Returns exit code and output
  - Generates human-readable summary

Tool Dispatcher (src/eip/llm/dispatcher.py):
  - Imports and initializes all three tool classes
  - Routes tool_id to appropriate implementation
  - For repo.modify_file: calls modification_tool.modify_file()
  - For repo.run_tests: calls execution_tool.run_tests()
  - Returns structured ToolResult to SDK/LLM

========================================================
SECURITY & CONTROL MEASURES
========================================================

1. Path Validation:
   All file operations validate that paths are inside the repository root.
   Prevents access to ../../../etc/passwd style attacks.

2. Exact Match Requirement:
   modify_file requires EXACT match of old_content.
   - No partial matches
   - No regex patterns
   - Case-sensitive matching
   - Prevents accidental modifications

3. Single Occurrence Requirement:
   modify_file rejects ambiguous modifications.
   - 0 occurrences: rejected (content not found)
   - >1 occurrence: rejected (which one to modify?)
   - Only exactly 1: allowed
   
   This prevents silent failures or unexpected side effects.

4. Read-only Repository Read:
   All read operations are non-destructive.
   Cannot be used to modify or delete files.

5. Controlled Test Execution:
   Tests run in subprocess with timeout.
   Cannot access arbitrary commands (pytest only).
   Returns structured output, not raw shell access.

6. No Git Operations:
   Intentionally excluded from Milestone 4.
   Deferred to later milestone for better control.

7. No Arbitrary Shell:
   No bash, sh, or command execution tools available.
   Only specific, narrowly-scoped operations.

========================================================
AGENT WORKFLOW (Milestone 4)
========================================================

Example: "Change MAX_ITEMS from 10 to 20 and verify"

Turn 1 (Inspection):
  Agent: read_file("README.md") -> understands project
         search_code("MAX_ITEMS") -> finds config.py
         list_files("src") -> sees structure

Turn 2 (Modification Request):
  Agent: read_file("src/config.py") -> sees exact content
         modify_file("src/config.py", 
                     old_content="MAX_ITEMS = 10",
                     new_content="MAX_ITEMS = 20")
  SDK calls modification tool
  LLM receives: {success: true, changes: 1, old: "...", new: "..."}

Turn 3 (Verification):
  Agent: run_tests() -> runs test suite
  SDK calls test execution tool
  LLM receives: {success: true, summary: "✓ Tests passed: 3 passed"}

Turn 4 (Response):
  Agent: Produces final response with evidence:
         "Successfully changed MAX_ITEMS from 10 to 20.
          Modified src/config.py (1 change).
          All tests pass (3 passed)."

========================================================
TEST GENERATION (Foundation for future work)
========================================================

Milestone 4 provides foundation for test generation:

Current capability:
1. Agent can read existing test files
2. Agent can identify what coverage is needed
3. Agent can propose test additions
4. Agent can modify test files using exact-match modify_file
5. Agent can run tests to verify coverage

Flow:
  1. Agent analyzes repository
  2. Agent identifies test file that needs updates
  3. Agent reads test file to understand current tests
  4. Agent proposes new test function as exact replacement
     modify_file("tests/test_app.py",
                 old_content="def test_existing():\n    pass",
                 new_content="def test_existing():\n    pass\n\ndef test_new():\n    ...")
  5. Agent runs tests to verify new test is valid
  6. Agent reports results

Limitations:
- Must identify exact old_content to replace
- Cannot add tests to empty file (need something to replace)
- Cannot append to end of file without knowing exact last content
- Works best when adding tests alongside existing ones

Future improvements (Milestone 5+):
- Could add append_file tool (append mode, less validation)
- Could add insert_file tool (insert at line N)
- Could have test generation LLM specialized for this
- Could track test coverage metrics

========================================================
DEFERRED CAPABILITIES
========================================================

Intentionally NOT included in Milestone 4:

1. Git Operations:
   - No git commit
   - No git push
   - No git PR creation
   - Deferred to Milestone 5 or later
   
   Reason: Need to establish patterns for:
   - Branch management
   - PR approval workflows
   - Risk management
   - Integration with GitHub/GitLab

2. File Deletion:
   - No delete_file tool
   - Can only modify existing files
   
   Reason: Deletion is destructive and risky
   Can be deferred until proven necessary

3. File Creation:
   - No create_file tool from agent
   
   Reason: create_file should go through modify_file if needed:
   - Create by modifying an empty stub file
   - Or defer to when file generation is well-understood

4. Arbitrary Shell Execution:
   - No shell, bash, sh tools
   
   Reason: Defeats purpose of controlled execution
   Specific operations (pytest) are better than shell access

5. Network Operations:
   - No curl, wget, http requests
   
   Reason: Requires API key management, security models
   Deferred to later milestone

========================================================
TESTING STRATEGY
========================================================

Unit Tests (test_modification_tool.py):
- Successful exact replacement
- Path validation (outside repo rejected)
- File existence validation
- Content matching (0 occurrences rejected)
- Content matching (>1 occurrence rejected)
- Multiline content replacement
- Nested file modification
- Evidence inclusion in result

Unit Tests (test_execution_tool.py):
- Successful test run
- Failed test run
- Specific test file execution
- Output capture
- Summary generation
- Result serialization

Integration Tests (test_dispatcher_integration.py):
- Tools available in dispatcher
- Tool calls routed correctly
- Modifications work through dispatcher
- Test execution works through dispatcher
- Read tools still work alongside new tools
- Unknown tools rejected
- Error handling

Agent Integration Tests (test_agent_with_new_tools.py):
- Agent handles modification results
- Agent continues reasoning after modification
- Agent handles modification errors
- Agent can request test execution
- Agent receives complete test results
- Full modification + test flow
- Max iterations protection maintained

Live Integration Test (run_milestone_4_test.py):
- End-to-end demo with sample repository
- Real Copilot LLM making decisions
- Agent inspects repository
- Agent identifies modification location
- Agent requests and receives modification
- Agent runs tests
- Agent reports results

========================================================
KNOWN LIMITATIONS & FUTURE WORK
========================================================

Limitations (Milestone 4):

1. Single Occurrence Requirement:
   Can only modify code when the old_content appears exactly once.
   Prevents silent partial changes but limits flexibility.
   Workaround: Agent must identify unique larger blocks.
   
   Future: Could add fuzzy matching or context-aware matching.

2. Text-only Modifications:
   Only works with UTF-8 text files.
   Cannot modify binary files.
   
   Future: May not be needed (most modifications are text).

3. No Transactional Rollback:
   If a modification succeeds but subsequent tests fail,
   no automatic rollback.
   
   Future: Could add modify_file with rollback capability.

4. Linear Agent Loop:
   Agent proceeds turn by turn with max_iterations limit.
   No sophisticated planning or backtracking.
   
   Future: Milestone 5+ will add planning/reasoning agents.

5. No Approval Workflow:
   Modifications execute immediately.
   No human approval step.
   
   Future: Could add approval step for production use.

6. Test Path Limitations:
   Can only run pytest from repository root.
   Cannot pass arbitrary pytest options.
   
   Future: Could parameterize pytest options.

7. No Test Selection:
   run_tests runs all tests in the specified path.
   Cannot select specific tests by name/pattern.
   
   Future: Could add test selection capability.

========================================================
MIGRATION FROM MILESTONE 3
========================================================

Backward Compatibility: PRESERVED

- All read tools work identically
- SimpleAgent behavior unchanged
- RepositoryAnalyst unaffected
- Existing tests pass with updated expectations (3→5 tools)
- All Milestone 1-3 functionality continues to work

New Agent Capabilities:
- SimpleAgent now automatically initialized with all 5 tools
- Agent can request modifications and tests if provided requirement asks for them
- No changes needed to existing agent code

LLM Integration:
- Copilot SDK now sees 5 tools instead of 3
- Tool allowlisting updated to include new tools
- Existing test/allowlist tests updated

========================================================
USAGE EXAMPLES
========================================================

Example 1: Simple Configuration Change
  requirement = "Change DEBUG=True to DEBUG=False in config.py"
  
  Agent:
  1. search_code("DEBUG") -> finds src/config.py
  2. read_file("src/config.py") -> sees "DEBUG = True"
  3. modify_file("src/config.py", "DEBUG = True", "DEBUG = False")
  4. read_file("src/config.py") -> verifies change
  5. Reports: "Configuration updated successfully"

Example 2: Bug Fix with Test Verification
  requirement = "Fix the off-by-one error in pagination and ensure tests pass"
  
  Agent:
  1. search_code("pagination") -> finds implementation
  2. read_file("src/pagination.py") -> understands bug
  3. search_code("test_pagination") -> finds tests
  4. read_file("tests/test_pagination.py") -> understands what should pass
  5. Proposes fix, modifies exact line
  6. modify_file("src/pagination.py", "range(n+1)" -> "range(n)")
  7. run_tests() -> verifies fix works
  8. Reports: "Bug fixed, pagination.py line X, all tests pass"

Example 3: Test Addition (Limited by single-occurrence requirement)
  requirement = "Add a test for the new feature"
  
  Agent:
  1. read_file("tests/test_features.py") -> understands structure
  2. Reads entire last test function
  3. modify_file("tests/test_features.py",
       old_content="def test_existing():\n    assert True",
       new_content="def test_existing():\n    assert True\n\ndef test_new():\n    assert False")
  4. run_tests("tests/test_features.py") -> new test appears
  5. Reports new test added

========================================================
CONCLUSION
========================================================

Milestone 4 successfully extends EIP from read-only analysis to controlled
execution. The architecture maintains security through strict validation,
exact-match requirements, and single-occurrence policies.

The agent can now not only inspect and understand code, but also make
targeted modifications and verify them through tests, enabling end-to-end
engineering workflows.

Future milestones will add:
- File creation and deletion (Milestone 5)
- Git operations and PR workflow (Milestone 6)
- Sophisticated planning and backtracking (Milestone 7+)
- More specialized test-generation models (Future)
"""
