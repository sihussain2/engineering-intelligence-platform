# Engineering Intelligence Platform

**A structured AI engineering system where AI reasoning meets controlled execution.**

---

## 1. What is Engineering Intelligence Platform?

Engineering Intelligence Platform (EIP) is an AI software engineering platform designed to take a software requirement and work through a structured software engineering lifecycle against a real software repository.

The long-term vision is an AI engineering system that can:

- **Understand** an existing codebase
- **Understand** a software requirement
- **Investigate** relevant parts of the system
- **Analyze** impact and dependencies
- **Create** an engineering plan
- **Request** human approval where appropriate
- **Implement** changes
- **Generate** and run tests
- **Diagnose** failures
- **Review** the implementation
- **Evaluate** whether the requirement was actually satisfied
- **Prepare** a GitHub pull request

**This is the overall vision. The current implementation is an early foundation.**

---

## 2. Why Does This Product Need to Exist?

AI coding assistants are increasingly capable of generating and modifying software. However, software engineering is much broader than writing code.

**Real engineering requires:**

- Understanding existing systems and their constraints
- Understanding requirements precisely
- Determining what parts of a system are affected
- Making architectural and design decisions
- Considering risks and dependencies
- Implementing changes carefully
- Testing the implementation thoroughly
- Debugging and diagnosing failures
- Reviewing the result critically
- Determining whether the original requirement was actually satisfied
- Maintaining traceability and engineering discipline

**The product hypothesis:**

> The opportunity is to move from AI as a code-generation assistant toward AI as a structured engineering system.

EIP explores whether AI can perform more of the engineering lifecycle when it operates inside a **controlled workflow** rather than simply being asked to "write some code."

**Is this true?** That's one of the questions this project is designed to answer.

---

## 3. The Key Idea

**The AI should be capable, but the engineering platform should remain in control.**

The LLM provides reasoning and decision-making. EIP provides workflow, controlled tools, engineering state, permissions, validation, human approval, testing, evaluation, observability, and resource controls.

**Core principle:**

> **The AI decides what it wants to do. EIP decides what it is allowed to do.**

### Why Controlled Access Matters

The LLM should not receive unrestricted access to a repository and the surrounding system.

Instead:

```
                   EIP (Platform)
                      │
                      ▼
                    LLM
                      │
          "I need to search
           the repository"
                      │
                      ▼
             Tool Dispatcher
                      │
       ┌──────────────┴──────────────┐
       │ Validate / Authorize        │
       │ Control / Audit / Sandbox   │
       └──────────────┬──────────────┘
                      ▼
             Repository Tool
                      │
                      ▼
                  Codebase
```

This architecture allows the platform to control increasingly powerful capabilities:

```
Read repository
      ↓ (with controls)
Modify files
      ↓ (with validation)
Run tests
      ↓ (in sandbox)
Execute commands
      ↓ (with approval)
Create commits
      ↓ (with review)
Create pull requests
```

As AI capabilities become more powerful, the platform applies increasingly strong controls: argument validation, sandboxing, approval requirements, and auditing.

---

## 4. The Overall Engineering Workflow

The intended complete workflow:

```
Software Requirement
        ↓
Understand Codebase
        ↓
Analyze Impact
        ↓
Create Engineering Plan
        ↓
Human Approval
        ↓
Implement Changes
        ↓
Generate / Update Tests
        ↓
Run Tests
        ↓
Debug Failures
        ↓
Review Implementation
        ↓
Evaluate Requirement Satisfaction
        ↓
Prepare Pull Request
```

**The important idea is the closed engineering loop:**

> Requirement → Implementation → Verification → Evaluation

The system should not stop simply because code was generated successfully. It should determine whether the resulting software actually satisfies the requirement.

---

## 5. System Organization

A simple conceptual architecture:

```
                        User
                         │
                         ▼
                   Requirement
                         │
                         ▼
                 Engineering Agent
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Context      Tools        LLM
          / RAG      / Controls      │
             │           │           │
             └───────────┼───────────┘
                         ▼
                Engineering Workflow
                         │
             ┌───────────┼────────────┐
             ▼           ▼            ▼
          Planning   Implementation  Testing
             │           │            │
             └───────────┼────────────┘
                         ▼
                 Review / Evaluation
                         │
                         ▼
                    GitHub PR
```

This is a conceptual view. Details belong in architecture documentation.

---

## 6. Major Platform Capabilities

### Repository / Code Intelligence

The system needs to understand an existing software repository before making changes.

Eventually this can evolve from basic file search and reading into richer code intelligence:

- Symbol discovery and definition
- Dependency relationships  
- Call relationships and dataflow
- Semantic code search
- Architecture understanding
- Test discovery and categorization

**Purpose:** Help AI reason about the actual system rather than isolated files.

### Agent / Workflow Engine

The agent controls the engineering process and maintains explicit workflow state:

```
RECEIVED
→ UNDERSTANDING
→ PLANNING
→ AWAITING_APPROVAL
→ IMPLEMENTING
→ TESTING
→ DEBUGGING
→ REVIEWING
→ EVALUATING
→ READY_FOR_PR
```

**Purpose:** Explicit state makes the process more controllable, observable, and recoverable than an unconstrained conversation.

### Controlled Tool Layer

Tools provide capabilities to the AI without giving it unrestricted system access.

Examples:

- Search repository
- Read files
- Modify files
- Run tests
- Execute controlled commands
- Inspect Git status
- Create commits
- Create pull requests

**Purpose:** The platform decides which tools are available and under what conditions they execute.

### LLM Gateway

Eventually provide a platform-level boundary between agents and model providers.

Potential responsibilities:

- Provider abstraction and swapping
- Model selection based on task
- Authentication and token management
- Rate limiting and retries
- Token accounting and budgets
- Usage tracking
- Cost tracking

**Status:** Provider abstraction exists via LLMClient protocol. Full gateway is future work.

### Secure Execution

When the system eventually modifies and executes code, execution should occur in controlled environments rather than directly on the host machine.

Potential capabilities:

- Isolated workers
- Containerization
- Resource limits
- Filesystem restrictions
- Network restrictions
- Command policies
- Approval gates

**Status:** Not yet implemented.

### Human Approval

Human approval should be part of the workflow for appropriate actions.

**Important:** The goal is not to remove humans from software engineering. The goal is to allow AI to perform more work while keeping humans responsible for important engineering decisions and approvals.

### Testing and Evaluation

**Testing** answers: "Does the software behave correctly?"

**Evaluation** answers: "Did the engineering work actually satisfy the original requirement?"

This distinction is critical. A program can be correct without satisfying the requirement.

### Observability

The platform should maintain an engineering "flight recorder" showing:

- What requirement was given
- What the agent investigated
- Which tools it used and when
- What decisions it made
- What changes were made
- What tests were executed and results
- What failed and how failures were resolved
- How the final result was evaluated

**Value:** Debugging, auditing, understanding AI behavior, establishing accountability.

---

## 7. What Are the Advantages?

### More Than Code Generation

The system addresses the broader engineering lifecycle rather than only generating code.

### Controlled Autonomy

AI can perform increasingly complex tasks while the platform controls what actions are permitted.

### Verification Instead of Blind Trust

The system tests, reviews, and evaluates its own work rather than assuming generated code is correct.

### Traceability

Engineering decisions and AI actions can eventually be recorded and connected back to the original requirement.

### Repeatable Engineering Process

The same structured workflow can be applied across different repositories and engineering tasks.

### Human-in-the-Loop

Humans remain involved at important decision points without having to manually perform every engineering task.

### Potential for Regulated Environments

A structured, controlled, and auditable approach may be particularly valuable in environments where software correctness, traceability, safety, security, or compliance matter.

**Important:** EIP is not yet suitable for regulated or safety-critical production use. This is a potential advantage and area for exploration.

---

## 8. How Is This Different from an AI Coding Assistant?

**Traditional AI coding assistants** primarily optimize the interaction between a developer and an AI that can generate or modify code.

**EIP** explores a broader system in which the AI operates as an engineering agent inside a controlled workflow with:

- Explicit tools
- Structured workflow state
- Human approval
- Testing and evaluation
- Traceability
- Resource controls

**Whether this provides enough additional value to become a useful product is one of the questions this project is intended to answer.**

---

## 9. What Works Today

The current implementation is an **early foundation**. It does NOT yet implement the full engineering workflow.

### Implemented Components

✅ **RepositoryTool** — Read-only access to repository content:
- `list_files(path)` — List all files and directories
- `read_file(path)` — Read individual source files  
- `search_code(query)` — Search repository for text patterns with line numbers

✅ **SimpleAgent** — Minimal agent loop that:
- Accepts a requirement
- Calls LLM with tools
- Executes tool calls via ToolDispatcher
- Collects results and continues until done

✅ **LLMClient Protocol** — Provider-independent interface:
- Enables swapping between OpenAI, Anthropic, Copilot, local models without changing core code
- Method: `complete(messages, tools, system_prompt) → dict`

✅ **ToolDispatcher** — Routes and executes LLM tool requests:
- Validates tool calls
- Executes against RepositoryTool
- Returns results to agent loop

✅ **GitHub Copilot SDK Integration** — Real LLM responses:
- Authenticated requests using Claude Haiku 4.5
- Proper error handling and response validation
- Session management with timeout protection

✅ **RepositoryAnalyst Foundation** — Skeleton for requirement analysis against repositories

✅ **Automated Test Suite** — 93 tests:
- Component integration testing
- Protocol compliance verification
- Error handling and edge cases
- Repository tool operations
- LLM client initialization and response handling

### NOT Yet Implemented

❌ **Real LLM Tool Calling** — The LLM currently returns text-only responses. Tool calls are structurally supported in SimpleAgent but Copilot integration doesn't yet invoke Copilot's native tool calling.

❌ **Code Modification** — No ability to modify repository files yet.

❌ **Test Execution** — No automated testing or test framework integration yet.

❌ **Human Approval Workflows** — No mechanism for human approval gates.

❌ **Review and Evaluation** — No code review or requirement satisfaction evaluation logic.

❌ **GitHub Integration** — No pull request creation or Git integration.

❌ **Secure Execution Environments** — No containerization or sandboxing.

❌ **Observability Systems** — No engineering flight recorder or audit logging yet.

❌ **LLM Gateway** — No multi-provider routing, rate limiting, token accounting, or cost tracking.

---

## 10. Current Architecture vs. Future Architecture

### Current Implementation

What has actually been built:

```
Requirement
    ↓
SimpleAgent
    ↓
LLMClient (protocol)
    ↓
CopilotLLMClient (adapter)
    ↓
GitHub Copilot SDK
    ↓
Claude Haiku 4.5
```

Separately:

```
LLM → SimpleAgent
       ↓
ToolDispatcher
       ↓
RepositoryTool
       ↓
Repository
```

**Status:** SimpleAgent can call tools and iterate, but Copilot integration currently provides text-only responses.

### Intended Future Platform

```
User
  │
  ▼
Engineering Platform
  │
  ├─ Workflow Engine
  ├─ Approval Gates
  ├─ Observability
  │
  ▼
Agent Runtime
  │
  ├─ Context/RAG
  ├─ Planning
  ├─ Implementation
  ├─ Testing
  ├─ Evaluation
  │
  ▼
LLM Gateway
  │
  ├─ Provider abstraction
  ├─ Model routing
  ├─ Rate limiting
  ├─ Token accounting
  │
  ▼
LLM (Copilot / OpenAI / Anthropic / Local)
  │
  ↕ (bidirectional)
  │
Controlled Tools
  │
  ├─ Code intelligence
  ├─ Execution controls
  ├─ Approval enforcement
  ├─ Audit logging
  │
  ▼
Secure Execution
  │
  ├─ Containers
  ├─ Resource limits
  ├─ File restrictions
  │
  ▼
Testing / Review / Evaluation
  │
  ▼
GitHub (PRs, commits, integration)
```

---

## 11. Development Roadmap

**Phase 1 — Foundation** (current)
- ✅ Repository tools (list, read, search)
- ✅ LLM integration and provider abstraction
- ✅ Basic agent loop
- → Next: Real tool calling from LLM

**Phase 2 — Engineering Agent**
- Real LLM tool calling
- Repository investigation through controlled tools
- Structured planning for requirements
- → Next: Human approval and implementation

**Phase 3 — Engineering Workflow**
- Human approval gates
- File modification and implementation
- Automated testing integration
- Failure diagnosis and recovery
- Code review
- Requirement satisfaction evaluation
- → Next: Platform services

**Phase 4 — Platform Services**
- LLM gateway (multi-provider, routing, accounting)
- Token and usage controls
- Quotas and budgets
- Observability and audit logging
- → Next: Secure execution

**Phase 5 — Secure Autonomous Engineering**
- Isolated execution environments
- Containerization
- Git integration
- Pull request creation
- CI/CD integration
- → Next: Real-world validation

**Phase 6 — Product Validation**
- Real engineering tasks
- Measurement and analysis
- Comparison with existing AI coding tools
- Identification of strongest use cases
- Determination of meaningful product value

**Critical:** The final phase matters most. The project is not only about building technology. It is about determining whether the resulting system solves a valuable problem better than existing alternatives.

---

## 12. TradePredictor

[TradePredictor](https://github.com/sihussain2/TradePredictor) is the real software repository being used to develop and demonstrate EIP.

**EIP is the engineering system. TradePredictor is the software being engineered.**

---

## Getting Started

```bash
# Install dependencies
pip install -e .
pip install -r requirements.txt

# Run the test suite (93 tests)
python -m pytest

# Manual integration test (requires GitHub Copilot subscription)
python tests/manual_test_copilot.py
```

---

## Documentation

- [Architecture decisions](docs/decisions/) — ADRs explaining key design choices
- [System overview](docs/architecture/) — Detailed system architecture
- [Copilot SDK integration](src/eip/llm/README-COPILOT.md) — Technical details on LLM integration

