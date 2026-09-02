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

**Phase 1 — Foundation (Current)**
- ✅ Repository tools implemented
- ✅ LLM integration via Copilot SDK
- ✅ Basic agent loop
- → Next: Connect real LLM tool calling

**Phase 2 — Engineering Agent**
- Repository investigation through controlled tools
- Structured planning for requirements
- → Next: Human approval and implementation

**Phase 3 — Engineering Workflow**
- Human approval gates
- Code modification
- Test execution and debugging
- Code review and evaluation

**Phase 4 — Platform Services**
- LLM gateway (multi-provider, routing, accounting)
- Usage and token controls
- Observability and audit logging

**Phase 5 — Secure Autonomous Engineering**
- Isolated execution environments
- Git and PR integration
- CI/CD integration

**Phase 6 — Product Validation**
- Real engineering tasks
- Comparison with existing tools
- Identification of valuable use cases
