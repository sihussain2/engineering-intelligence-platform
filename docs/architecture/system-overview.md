# System Overview

## Product Vision

The Engineering Intelligence Platform is an AI-powered software engineering system designed to take a software requirement and work through a structured software engineering lifecycle against a real software repository. The long-term vision includes understanding codebases, analyzing impact, creating engineering plans, implementing changes, testing, debugging, reviewing, and evaluating whether requirements are satisfied before preparing pull requests.

## Current Implementation

The current system establishes the architectural foundation for this vision:

### Current Data Flow

The LLM communication layer:

```
Requirement
    ↓
SimpleAgent
    ↓
LLMClient Protocol (provider-independent)
    ↓
CopilotLLMClient (GitHub Copilot SDK adapter)
    ↓
GitHub Copilot SDK
    ↓
Claude Haiku 4.5 (via Copilot)
    ↓
Text Response
```

The EIP-controlled tool execution layer (currently disconnected from LLM):

```
SimpleAgent
    ↓
ToolDispatcher
    ↓
RepositoryTool (read-only access)
    ↓
Repository
```

**Current Status:**
- ✅ LLM integration via Copilot SDK is fully implemented and tested
- ✅ Text-only responses from Copilot work end-to-end
- ✅ EIP's controlled tool execution architecture is implemented
- ✅ SimpleAgent can iterate with agent logic and call tools
- ❌ **Connection point:** Copilot's native tool calling is not yet plumbed to EIP's ToolDispatcher. LLM currently returns text responses only; tool execution happens through SimpleAgent's iterative loop, not through Copilot's native tool invocation system.

### Core Components Implemented

1. **SimpleAgent** — Agent loop that manages iterations, tool calls, and conversation history
2. **LLMClient Protocol** — Provider-independent interface enabling swapping between OpenAI, Anthropic, Copilot, etc.
3. **CopilotLLMClient** — GitHub Copilot SDK adapter with text-only responses currently
4. **ToolDispatcher** — Routes and executes tool calls (architecture ready)
5. **RepositoryTool** — Read-only access to repository:
   - list_files
   - read_file
   - search_code
6. **RepositoryAnalyst Foundation** — Framework for requirement analysis

### Milestone 4: Controlled Engineering Execution (NEW)

**Status: ✅ COMPLETE**

Milestone 4 extends EIP from read-only analysis into controlled code modification and test execution:

**New Capabilities:**
- **RepositoryModificationTool** — Controlled file modification:
  - `modify_file(path, old_content, new_content)`: Replace exact text with validation
  - Validation: Path boundary check, file existence, exact match requirement, single occurrence check
  - Returns evidence: what was changed, old content, new content

- **TestExecutionTool** — Controlled test execution:
  - `run_tests(test_path=None)`: Execute pytest with timeout
  - Captures output: exit code, stdout, stderr, summary
  - Returns structured results for agent reasoning

**Control Principle:**
"The agent proposes; EIP validates and executes."

The agent cannot:
- Access arbitrary shell commands
- Delete files
- Create files directly
- Access git operations
- Access network operations

The agent can only:
- Read and analyze code (3 read tools)
- Request targeted modifications (1 write tool)
- Execute tests to verify (1 verify tool)

**Security Measures:**
- Path traversal prevention
- Exact-match requirement (no regex, no partial)
- Single occurrence enforcement (prevents ambiguous changes)
- Timeout protection on test execution
- Subprocess isolation

**Implementation:**
- `src/eip/repository/modification.py`: 11-step validation for file modifications
- `src/eip/repository/execution.py`: Subprocess-based pytest execution
- `src/eip/llm/tools.py`: Tool definitions updated to include 5 tools
- `src/eip/llm/dispatcher.py`: Routing for new tools added
- Backward compatible: All existing read tools unchanged

**Testing:**
- 11 tests for modification tool (path validation, content matching, atomicity)
- 9 tests for execution tool (success/failure, output capture, summary)
- 9 tests for dispatcher integration (routing, backward compatibility)
- 7 tests for agent integration (multi-turn workflows)
- Live integration test: Real Copilot LLM successfully modifying code and running tests

**Known Limitations:**
- Single occurrence requirement: Can only modify when exact content appears once
- Exact match only: No fuzzy/regex matching
- Text-only: Cannot modify binary files
- No transactional rollback: Modifications persist even if tests fail
- Test path must be under repository root

For detailed documentation, see [docs/MILESTONE_4.md](MILESTONE_4.md)

### Milestone 5: Iterative Verification & Recovery (NEW)

**Status: ✅ COMPLETE**

Milestone 5 extends EIP from simple "modify → test → report" into a full engineering recovery workflow:

```
Requirement
    ↓
INVESTIGATE (read tools)
    ↓
IMPLEMENT (modify_file)
    ↓
VERIFY (run_tests)
    ↓
    IF tests PASS:
    ├─→ REVIEW (quality assessment)
    ├─→ EVALUATE (requirement satisfaction)
    └─→ REPORT (final result)

    IF tests FAIL:
    ├─→ DIAGNOSE (inspect failure)
    ├─→ FIX (corrective modification)
    ├─→ RETEST (run_tests again)
    └─→ ITERATE (loop back to DIAGNOSE or succeed)
```

**Core Principle:**
"Verification is iterative. Success means tests pass AND requirement is satisfied, not just that code was modified."

**New Capabilities:**

1. **Enhanced TestResult** — Rich failure diagnostics:
   - Failure type classification: "test_failure", "execution_error", "timeout"
   - Test count extraction: passed_count, failed_count
   - Failed test identification: names of specific failing tests
   - LLM-friendly serialization

2. **Failure Recovery Loop**:
   - Agent receives test failure information
   - Agent uses existing tools (read_file, search_code) to diagnose
   - Agent proposes corrective modification
   - Agent re-runs tests
   - Process continues up to max_iterations limit
   - No infinite loops (safety mechanism)

3. **AgentSession Enhancements**:
   - Tracks test pass/fail status
   - Tracks recovery attempts
   - Records modified files
   - Maintains engineering context across iterations

4. **Verification-Aware System Prompts**:
   - First iteration: Full workflow guidance (investigate → implement → verify → review → evaluate)
   - Continuation iterations: Emphasize diagnosis and recovery
   - Guides LLM to distinguish between success and failure recovery

5. **Structured Engineering Result**:
   - EngineringResult class with status enum (SATISFIED / PARTIALLY_SATISFIED / NOT_SATISFIED / VERIFICATION_INCOMPLETE)
   - ImplementationSummary: files changed, description, modification count, iterations required
   - VerificationSummary: test pass/fail, counts, diagnosed failures, recovery attempts
   - ReviewFindings: requirement addressed, implementation correct, test coverage, risks, limitations

**Implementation:**
- `src/eip/llm/verification.py`: Result models for structured evaluation
- `src/eip/repository/execution.py`: Enhanced with _parse_test_output() for diagnostics
- `src/eip/llm/agent.py`: Updated to track test state, handle failure continuation, provide verification-aware prompts
- Backward compatible: All existing tools and agent behavior preserved

**Testing:**
- 9 tests for enhanced TestResult (failure types, test counts, diagnostics)
- 10 tests for agent recovery loop (state tracking, continuation, prompts)
- Live integration test: Real Copilot LLM successfully diagnosing and recovering from test failures

**Control Boundary:**

LLM Responsibilities:
- Reason about code structure
- Interpret test failures
- Propose diagnostic modifications
- Decide on fixes

EIP Responsibilities:
- Control available tools
- Validate modifications (exact match, single occurrence)
- Execute tests (pytest, subprocess)
- Limit iterations (max_iterations)
- Record state and evidence

**Example Recovery Sequence:**

```
1. Agent reads requirement: "Change MAX_RETRIES from 3 to 5"
2. Agent investigates: read_file("src/settings.py") → sees MAX_RETRIES = 3
3. Agent modifies: modify_file() with MAX_RETRIES = 3 → 5
4. Agent tests: run_tests() → FAIL (test expects 5 but got 5... wait, let me check)
5. Agent diagnoses: read_file("src/settings.py") → sees MAX_RETRIES = 5 ✓
                    read_file("tests/test_settings.py") → sees test validates value
                    → realizes issue might be in implementation logic
6. Agent modifies: modify_file() in src/settings.py to fix logic
7. Agent tests: run_tests() → PASS
8. Agent reviews: Confirms modification matches requirement, tests pass
9. Agent evaluates: status = SATISFIED, requirement = "Change MAX_RETRIES from 3 to 5"
10. Agent reports final EngineringResult with evidence
```

**Known Limitations:**
- Recovery limited by max_iterations (default 10)
- Agent reasoning depends on LLM quality
- Cannot diagnose issues requiring file creation/deletion
- Cannot diagnose issues requiring git/branching
- Cannot diagnose issues requiring network calls

**Architectural Notes:**
- Copilot SDK session isolation preserved (still recreated per complete() call)
- Existing max_iterations safety mechanism reused for failure recovery
- LLM receives full failure context (stdout, stderr, failed test names)
- No new persistent state (all in AgentSession in-memory)

## Intended Full Platform Architecture

The complete platform vision:

```
Software Requirement
        ↓
Engineering Agent
        ↓
Code Intelligence / Context
        ↓
Controlled Tools
        ↓
Planning
        ↓
Human Approval
        ↓
Implementation
        ↓
Testing
        ↓
Debugging
        ↓
Review
        ↓
Evaluation
        ↓
GitHub PR
```

This represents the intended platform. Not all components are implemented yet.

## Key Architectural Principles

1. **Provider Independence:** LLMClient protocol allows swapping LLM providers without changing core code

2. **Controlled AI:** The AI decides what it wants to do; EIP decides what it's allowed to do. Tools provide:
   - Capability boundaries
   - Validation and authorization
   - Safe execution
   - Human approval gates
   - Auditing

3. **Structured Workflow:** Explicit engineering state (understanding → planning → approval → implementation → testing → review → evaluation) rather than unconstrained conversation

4. **Verification Loop:** The system doesn't stop when code is generated; it verifies the result satisfies the requirement

## Development Phases

**Phase 1 — Foundation**
- ✅ Repository tools implemented (read-only)
- ✅ LLM integration via Copilot SDK
- ✅ Basic agent loop

**Phase 2 — Controlled Execution (Milestone 4)**
- ✅ File modification tool with strict validation
- ✅ Test execution tool with output capture
- ✅ Agent integration with new tools
- ✅ Live testing with real Copilot LLM

**Phase 3 — Iterative Verification (Milestone 5)**
- ✅ Enhanced test result model with diagnostics
- ✅ Failure recovery loop with diagnosis capability
- ✅ Structured engineering result evaluation
- ✅ Agent tracking of verification state
- ✅ Live recovery workflow with real Copilot LLM
- → Next: File creation/deletion, git integration

**Phase 4 — Advanced Capabilities**
- File creation and deletion tools
- Git and PR integration
- Isolated execution environments
- CI/CD integration

**Phase 5 — Platform Services**
- LLM gateway (multi-provider, routing, accounting)
- Usage and token controls
- Observability and audit logging

**Phase 6 — Product Validation**
- Real engineering tasks at scale
- Comparison with existing tools
- Identification of valuable use cases
