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

The current implementation spans **Milestones 1–5**. It implements repository analysis, controlled code modification, test execution, and failure recovery. The full engineering workflow (approval gates, evaluation, Git integration) is not yet implemented.

### Fully Implemented Components (Milestones 1–5)

✅ **RepositoryTool** — Read-only access to repository content (Milestone 1):
- `list_files(path)` — List all files and directories
- `read_file(path)` — Read individual source files  
- `search_code(query)` — Search repository for text patterns with line numbers
- Validation: Path normalization, security (prevents path traversal)

✅ **RepositoryModificationTool** — Controlled file modification (Milestone 4):
- `modify_file(path, old_content, new_content)` — Replace exact content with strict validation
- Validation: Requires exact match, must occur exactly once, preserves rest of file
- Returns structured evidence of changes

✅ **TestExecutionTool** — Automated test execution (Milestone 4):
- `run_tests(test_path=None)` — Execute pytest test suite
- Enhanced diagnostics: Failure classification, test count extraction, failed test names
- Enables agent to understand test results for recovery

✅ **SimpleAgent** — Iterative agent loop with failure recovery (Milestone 5):
- Accepts a requirement
- Investigates repository with tools
- Makes controlled modifications
- Runs tests and detects failures
- Diagnoses failures and makes corrective modifications
- Continues iteration until tests pass or max iterations reached
- Tracks session state: tests_passed, recovery_attempts, modifications_made

✅ **Real LLM Tool Calling** — Native Copilot SDK tool invocation (Milestone 2):
- Copilot SDK's `send_and_wait()` handles native tool calling
- Tool handlers bridge SDK tool invocations to EIP's ToolDispatcher
- Tool execution tracking provides visibility to agent
- Tool allowlisting via Copilot's `available_tools` parameter

✅ **LLMClient Protocol** — Provider-independent interface:
- Enables swapping between OpenAI, Anthropic, Copilot, local models without changing core code
- Method: `complete(messages, tools, system_prompt) → dict`

✅ **ToolDispatcher** — Routes and executes all LLM tool requests:
- Validates tool calls
- Executes against RepositoryTool, RepositoryModificationTool, TestExecutionTool
- Returns structured results to agent loop

✅ **GitHub Copilot SDK Integration** — Real LLM with native tool calling:
- Authenticated requests using Claude Haiku 4.5
- Native tool calling with callback handlers
- Proper error handling and response validation
- Session management with timeout protection

✅ **RepositoryAnalyst** — LLM-driven requirement analysis (Milestone 3):
- Uses SimpleAgent to explore repository
- Produces structured analysis results

✅ **Structured Verification Models** — End-to-end result tracking (Milestone 5):
- EngineringResult with status, implementation summary, verification evidence
- Enables structured tracking of requirement satisfaction

✅ **Comprehensive Test Suite** — 192 tests:
- Repository tool operations (13 tests)
- File modification validation (11 tests)
- Test execution and parsing (enhanced suite)
- Agent loops and iterative recovery (10+ tests)
- Copilot SDK integration and tool tracking (9+ tests)
- Tool dispatch and execution (multiple tests)
- Component integration testing
- Protocol compliance verification
- Error handling and edge cases

### NOT Yet Implemented

❌ **Human Approval Workflows** — No mechanism for human approval gates.

❌ **Requirement Satisfaction Evaluation** — No logic to verify requirement was actually satisfied (vs. just tests passing).

❌ **Code Review** — No code review or architectural analysis.

❌ **GitHub Integration** — No pull request creation or Git operations.

❌ **Secure Execution Environments** — No containerization or sandboxing.

❌ **Observability Systems** — No engineering flight recorder or audit logging.

❌ **LLM Gateway** — No multi-provider routing, model selection, token accounting, or cost tracking.

---

## 10. Token Efficiency and Cost Control Strategy

**Why This Matters**

Running an autonomous AI engineering system at scale requires managing both capability and cost. An AI that can solve problems but consumes unlimited tokens is not productionizable.

**The Challenge**

- A complex engineering requirement might involve deep investigation, multiple iterations, recovery from failures, testing, review, and evaluation
- Each step consumes LLM tokens
- Tokens cost money
- If token consumption scales poorly with task complexity, the system becomes economically unviable

**The Strategy**

EIP is designed with token efficiency and cost control as first-class concerns:

### 1. Intelligent Model Selection

**Problem:** Not all tasks need a powerful (and expensive) model.
- Reading a file: doesn't need Claude 3.5 Sonnet
- Searching code: doesn't need advanced reasoning
- Analyzing complex architecture: might need stronger reasoning

**Solution:** Route tasks to appropriate models
```
Simple lookup      → Fast model (Claude Haiku - 1/10 token cost)
Code search        → Fast model (Claude Haiku)
Reading files      → Fast model (Claude Haiku)
Planning           → Standard model (Claude 3.5 Sonnet)
Complex reasoning  → Standard model (Claude 3.5 Sonnet)
Recovery/debug     → Standard model (if needed)
Final review       → Strong model (Claude 3 Opus)
```

**Benefit:** 70-80% token cost reduction by using cheaper models for simpler tasks.

### 2. Context Optimization

**Problem:** Long conversations with full history consume exponentially more tokens.

**Solutions:**
- **Summary compression:** Summarize completed phases before moving to next phase
- **Selective context:** Include only relevant file snippets, not entire files
- **Context hierarchy:** Keep current step context small, archive old context
- **Smart chunking:** Break large files into relevant sections, only pass needed sections to LLM

**Example:**
```
❌ BAD: "Here are 10,000 lines of repository code, analyze all of it"
         (Tokens: 15,000+)

✅ GOOD: "The failing test is in test_payment.py lines 42-58. 
          The implementation is in payment.py lines 100-150.
          Search results show 3 related files."
         (Tokens: 800)
```

**Benefit:** 10x token reduction through focused context.

### 3. Iteration Control

**Problem:** An agent that repeats itself or explores exhaustively can waste tokens.

**Solutions:**
- **Iteration budgets:** Limit agent iterations per phase
- **Early termination:** Stop exploring when requirements are met
- **Branching control:** Limit number of alternative approaches tried
- **Caching:** Remember results from previous similar investigations

**Example:**
```
Agent Loop Budget:
├─ Investigation phase: max 3 iterations
├─ Implementation phase: max 5 iterations
├─ Testing phase: max 4 iterations
└─ Recovery phase: max 3 iterations
Total: 15 iterations max (vs unlimited)
```

**Benefit:** Predictable token consumption, avoids runaway costs.

### 4. Cost Tracking and Budgets

**Design:**
- **Per-requirement budget:** Each requirement gets a token budget
- **Per-phase tracking:** Know costs at each workflow stage
- **Real-time accounting:** Track spend during execution
- **Budget alerts:** Warn before exceeding budget
- **Cost analysis:** Understand which tasks are expensive

**Example:**
```
Requirement: "Add payment feature to checkout"
├─ Budget: 50,000 tokens
├─ Investigation: 5,000 / 10,000 (50% of phase budget)
├─ Planning: 8,000 / 15,000 (53% of phase budget)
├─ Implementation: 12,000 / 15,000 (80% of phase budget)
├─ Testing: 3,000 / 5,000 (60% of phase budget)
├─ Review: 2,000 / 5,000 (40% of phase budget)
└─ TOTAL: 30,000 / 50,000 tokens used (60%)
```

**Benefit:** Transparency and control over AI operating costs.

### 5. Structured Workflow Efficiency

**Problem:** Unstructured conversations with LLMs often waste tokens on:
- Explaining the same context repeatedly
- Asking clarifying questions
- Backtracking due to misunderstandings
- Repeating analysis in different words

**Solution:** Structured workflow with explicit phases
- Each phase has a clear input, expected output, and success criteria
- Prompts are tailored to the current phase, not the full history
- Context is passed strategically, not conversationally
- Results are validated before moving forward

**Benefit:** 5-10x efficiency improvement through focused, structured workflow.

### 6. Parallel Execution

**Problem:** Sequential analysis of independent tasks multiplies token cost.

**Solution:** Parallelize where safe
- Analyze multiple code paths simultaneously
- Run multiple test scenarios in parallel
- Investigate different potential solutions in parallel

**Benefit:** Same work in 1/N time and tokens (where N = parallelism).

### The Payoff

Combined, these strategies can achieve:
- **75-90% token reduction** vs. unoptimized approaches
- **Predictable costs** through budgeting and accounting
- **Scalability** from single requirements to enterprise workloads
- **Sustainability** as an economically viable autonomous system

**Concrete Example:**
```
Same engineering task:

Unoptimized approach (chat with LLM):
├─ Repeated context: 20,000 tokens wasted
├─ Clarification loops: 15,000 tokens
├─ Backtracking: 10,000 tokens
├─ Redundant analysis: 8,000 tokens
└─ Total: 53,000 tokens, $1.06 (at GPT-4 pricing)

EIP optimized approach:
├─ Model selection: Claude Haiku for 60% of work
├─ Context pruning: Only relevant code excerpts
├─ Structured phases: No repetition or backtracking
├─ Iteration control: Budget enforcement
└─ Total: 8,000 tokens, $0.12 (90% savings)
```

**Long-term Vision:** As EIP matures, token efficiency becomes a competitive advantage. Systems that achieve high-quality results with low token consumption can operate sustainably at scale.

---

## 11. Current Architecture vs. Future Architecture

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

**Status:** Complete with real tool calling. Copilot SDK's `send_and_wait()` handles native tool invocations via registered handlers, enabling full iterative workflows.

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

## 12. Development Roadmap

**Phase 1 — Foundation** ✅ COMPLETE
- ✅ Repository tools (list, read, search)
- ✅ LLM integration and provider abstraction
- ✅ Basic agent loop
- ✅ Real LLM tool calling (native Copilot SDK)

**Phase 2 — Engineering Agent** ✅ COMPLETE
- ✅ Real LLM tool calling with tool handlers
- ✅ Repository investigation through controlled tools
- ✅ Structured planning for requirements
- ✅ File modification with strict validation
- ✅ Automated test execution
- ✅ Failure diagnosis and recovery loop

**Phase 3 — Verification & Recovery** ✅ COMPLETE
- ✅ Test failure classification and parsing
- ✅ Iterative recovery: diagnose → fix → retest
- ✅ Session state tracking (tests_passed, modifications, recovery_attempts)
- ✅ Verification-aware prompts (first vs. continuation iterations)
- ✅ Structured result models

**Phase 4 — Engineering Workflow** (Next)
- Human approval gates
- Requirement satisfaction evaluation
- Code review and architectural analysis
- → Next: Platform services

**Phase 5 — Platform Services**
- LLM gateway (multi-provider, routing, accounting)
- Token and usage controls
- Quotas and budgets
- Observability and audit logging
- → Next: Secure execution

**Phase 6 — Secure Autonomous Engineering**
- Isolated execution environments
- Containerization
- Git integration
- Pull request creation
- CI/CD integration
- → Next: Real-world validation

**Phase 7 — Product Validation**
- Real engineering tasks
- Measurement and analysis
- Comparison with existing AI coding tools
- Identification of strongest use cases
- Determination of meaningful product value

**Critical:** The final phase matters most. The project is not only about building technology. It is about determining whether the resulting system solves a valuable problem better than existing alternatives.

---

## 13. TradePredictor

[TradePredictor](https://github.com/sihussain2/TradePredictor) is the real software repository being used to develop and demonstrate EIP.

**EIP is the engineering system. TradePredictor is the software being engineered.**

---

## Getting Started

```bash
# Install dependencies
pip install -e .
pip install -r requirements.txt

# Run the test suite (192 tests)
python -m pytest

# Manual integration test (requires GitHub Copilot subscription)
python tests/manual_test_copilot.py
```

---

## Documentation

- [Architecture decisions](docs/decisions/) — ADRs explaining key design choices
- [System overview](docs/architecture/) — Detailed system architecture
- [Copilot SDK integration](src/eip/llm/README-COPILOT.md) — Technical details on LLM integration

