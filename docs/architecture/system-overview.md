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
- → Next: Human approval and planning

**Phase 3 — Engineering Workflow**
- Human approval gates
- Structured planning for requirements
- Test debugging and iteration
- Code review and evaluation

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
