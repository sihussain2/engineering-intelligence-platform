# GitHub Copilot SDK Adapter

This directory contains the GitHub Copilot SDK adapter for the Engineering Intelligence Platform.

## Overview

The `CopilotLLMClient` adapter implements the `LLMClient` protocol, enabling seamless integration with GitHub Copilot while maintaining provider independence.

**Key Features:**
- ✅ Implements `LLMClient` protocol (provider-agnostic interface)
- ✅ Uses official GitHub Copilot SDK (no separate API keys required)
- ✅ Authenticates via user's existing GitHub Copilot subscription
- ✅ Adapts async SDK to sync `complete()` interface
- ✅ Converts between message formats internally
- ✅ Accepts tool definitions in interface (architecture-ready)
- ✅ Handles system prompts
- ✅ 25+ unit tests with mock-based testing (no network calls)
- ✅ Manual integration test for real Copilot verification

## Files

| File | Purpose |
|------|---------|
| [copilot.py](copilot.py) | `CopilotLLMClient` adapter |
| [../../tests/test_copilot_adapter.py](../../tests/test_copilot_adapter.py) | Unit tests with mocks (25+ tests) |
| [../../tests/manual_test_copilot.py](../../tests/manual_test_copilot.py) | Manual integration test |

## Installation

The GitHub Copilot SDK is already included in `pyproject.toml`:

```bash
# Install project with Copilot SDK
pip install -e .

# Or install separately
pip install github-copilot-sdk>=1.0.0
```

## Authentication

The adapter supports multiple authentication methods (in priority order):

1. **Explicit token:** `CopilotLLMClient(github_token="ghp_...")`
2. **Environment variables:** 
   - `COPILOT_GITHUB_TOKEN`
   - `GH_TOKEN`
   - `GITHUB_TOKEN`
3. **GitHub Copilot CLI login:** Stored OAuth credentials from `copilot login`

No separate API keys are needed—uses your existing GitHub Copilot subscription.

## Usage

### Basic Usage

```python
from eip.llm.copilot import CopilotLLMClient
from eip.repository.tool import RepositoryTool
from pathlib import Path

# Create adapter
client = CopilotLLMClient(model="claude-haiku-4.5")

# Use in conversation
messages = [
    {"role": "user", "content": "What is this code doing?"}
]

result = client.complete(messages)
print(result["content"])  # Assistant response
print(result["done"])     # True when finished
print(result["tool_calls"])  # Tool calls if any
```

### With Tools

```python
from eip.llm.dispatcher import ToolDispatcher
from eip.repository.tool import RepositoryTool

# Set up tools
repo = RepositoryTool(Path("."))
dispatcher = ToolDispatcher(repo)
tools = dispatcher.get_tools()  # list_files, read_file, search_code

# Complete with tools
result = client.complete(messages, tools=tools)
```

### With System Prompt

```python
system_prompt = "You are a code reviewer. Focus on security and performance."
result = client.complete(messages, system_prompt=system_prompt)
```

### With SimpleAgent

```python
from eip.llm.agent import SimpleAgent
from eip.repository.tool import RepositoryTool

agent = SimpleAgent(
    llm_client=client,
    repository_tool=RepositoryTool(Path(".")),
    max_iterations=5
)

session = agent.run("Analyze the repository structure")
print(session.final_response)
```

## Testing

### Run Unit Tests (no network)

```bash
# Run only Copilot adapter tests
pytest tests/test_copilot_adapter.py -v

# Run all tests
pytest -v

# Run without integration tests (default)
pytest  # -m "not integration" is default
```

### Run Integration Tests (requires real Copilot)

```bash
# Run the manual integration test
python tests/manual_test_copilot.py
```

**Integration tests require:**
- Active GitHub Copilot subscription
- GitHub Copilot CLI authenticated (`copilot login`)
- Internet connection to Copilot service

## Architecture

The adapter preserves provider independence with clear separation of concerns:

```
SimpleAgent (orchestration)
    ↓
LLMClient Protocol (interface)
    ↓
CopilotLLMClient (adapter)
    ↓
copilot.CopilotClient (GitHub Copilot SDK)
    ↓
Copilot CLI Runtime (bundled with SDK)
```

**Current State:**
The adapter currently provides **text-only responses** from the Copilot LLM. Tool definitions are accepted in the `complete()` interface for architectural readiness, and the EIP tool execution foundation exists (via ToolDispatcher and RepositoryTool). However, real Copilot provider-level tool calling is not yet connected end-to-end. 

In the current milestone:
- ✅ `CopilotLLMClient` sends requests to Copilot and receives text responses
- ✅ `SimpleAgent` can parse tool calls from LLM responses and iterate
- ✅ `ToolDispatcher` routes and executes repository tools via `RepositoryTool`
- ❌ Copilot's native tool execution is not connected to EIP's `ToolDispatcher`
- ❌ SimpleAgent receives text only; tool execution happens through agent iteration, not Copilot's native tool system

**Next Milestone:**
Enable real Copilot provider-level tool calling to be bridged to EIP's `ToolDispatcher`, allowing the LLM to dynamically invoke repository tools through Copilot's native tool system rather than through text-based response parsing. This requires SDK updates and plumbing between Copilot's tool result callbacks and EIP's tool execution logic.

**Key Design Decisions:**

1. **Sync-to-Async Bridge:** SDK is async, protocol is sync. Adapter uses `asyncio.run()` to bridge them.
2. **Duck Typing:** Uses duck typing for Copilot event types to avoid brittle type checking.
3. **Message Pass-through:** Copilot's message format is compatible with our protocol, so minimal conversion needed.
4. **Tool Format Conversion:** Converts between our JSON schema format and Copilot's tool definitions.
5. **Encapsulation:** All Copilot SDK specifics stay inside adapter; rest of codebase knows only about protocol.

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `COPILOT_GITHUB_TOKEN` | GitHub token for Copilot | `ghp_...` |
| `GH_TOKEN` | GitHub token (fallback) | `github_...` |
| `GITHUB_TOKEN` | GitHub token (fallback) | `ghp_...` |
| `COPILOT_CLI_PATH` | Custom Copilot CLI binary | `/usr/local/bin/copilot` |
| `RUN_COPILOT_INTEGRATION` | Enable integration tests | `1` |

### Models Supported

The adapter supports any model available via your Copilot installation:

- `"claude-haiku-4.5"` - Claude Haiku 4.5 (current default)
- `"claude-sonnet-5"` - Claude Sonnet 5
- Others available in your Copilot subscription

Full list available via `CopilotClient.list_models()`.

## Limitations and Future Work

**Current Limitations:**
- ❌ No streaming responses yet
- ❌ No parallel tool execution
- ❌ No tool caching
- ❌ No session persistence (each `complete()` call is independent)
- ❌ No observability/telemetry integration
- ❌ LLM tool calling not yet connected to EIP ToolDispatcher (text-only responses currently)

**Future Enhancements:**
- Add streaming support via event filtering
- Implement tool result caching
- Add session persistence
- Support model-specific reasoning/thinking
- Add telemetry integration
- Create provider adapters for OpenAI, Anthropic, etc.
- Add rate limiting and retry logic

## Test Coverage

**25+ Unit Tests** covering:

| Component | Tests | Coverage |
|-----------|-------|----------|
| Initialization | 8 | Token sources, model selection, config |
| Message Conversion | 6 | Format passthrough, tool conversion |
| Tool Handling | 1 | Tool definition conversion |
| Protocol Compliance | 2 | Interface implementation, signature |
| Response Handling | 7 | Valid responses, None response, empty response, missing attributes |
| Event Processing | Additional | SDK event handling and session management |

All tests use mocks/fakes and don't make real Copilot SDK calls.

## Error Handling

The adapter provides clear error messages:

```python
# Error: called from async context
RuntimeError: "CopilotLLMClient.complete() cannot be called from async context"

# Error: missing import
ImportError: "github-copilot-sdk is required. Install with: pip install github-copilot-sdk"

# Error: invalid message order
ValueError: "Last message must be from user role for complete()"
```

## Performance

**Note:** Performance characteristics depend heavily on Copilot service response times and network conditions. No systematic measurements are currently documented. For production use, conduct benchmarking with your typical workloads.

## Security

**Authentication:**
- Uses GitHub's OAuth flow (via `copilot` CLI login)
- Tokens not stored in code
- Supports environment variable injection

**Access Control (Architectural Intent):**
- Tools can be filtered via `ToolDispatcher`
- Permission requests supported via SDK hooks
- RepositoryTool provides read-only access with path validation
- **Note:** Current Copilot integration receives text responses only. Real tool-based access control will be enforced once LLM tool calling is connected.

**Data:**
- No request caching
- Session data managed by Copilot CLI
- Messages passed through adapter unchanged

## Compatibility

| Component | Version | Tested |
|-----------|---------|--------|
| Python | ≥3.11 | 3.14.4 ✓ |
| github-copilot-sdk | ≥1.0.0 | 1.0.11 ✓ |
| Copilot CLI | auto-downloaded | Latest ✓ |

## See Also

- [GitHub Copilot SDK Docs](https://github.com/github/copilot-sdk)
- [LLMClient Protocol](protocol.py)
- [SimpleAgent Implementation](agent.py)
- [ToolDispatcher](dispatcher.py)
