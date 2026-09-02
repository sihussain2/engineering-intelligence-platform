# Architectural Review: Real Copilot Tool Calling Implementation

## 1. IMPLEMENTATION OVERVIEW

### Code Components

#### A. `src/eip/llm/copilot.py::_complete_async()`

```python
async def _complete_async(self, messages, tools=None, system_prompt=None) -> dict:
    """
    Async implementation of complete().
    """
    # Build session config
    session_config: dict[str, Any] = {
        "on_permission_request": PermissionHandler.approve_all,
        "model": self.model,
    }

    # Add system prompt if provided
    if system_prompt:
        session_config["system_message"] = {
            "mode": "append",
            "content": system_prompt,
        }

    # Build SDK Tool objects if dispatcher and tools are provided
    sdk_tools = None
    if self.dispatcher and tools:
        sdk_tools = self._build_sdk_tools(tools)
        session_config["tools"] = sdk_tools

    # Create and use client
    async with CopilotClient(
        github_token=self.github_token,
        working_directory=self.working_directory,  # ⚠️ RISK POINT
    ) as client:
        async with await client.create_session(**session_config) as session:
            return await self._run_session(session, messages)
```

**Control Analysis:**
- **EIP-controlled**: `system_prompt`, `tools` (via `session_config`)
- **SDK-controlled**: `CopilotClient()` initialization, `create_session()` parameters
- **Real LLM behavior**: Determined by Claude Haiku 4.5 runtime
- **Potential bypass vector**: `working_directory` parameter passed to `CopilotClient()`

---

#### B. `src/eip/llm/copilot.py::_build_sdk_tools()`

```python
def _build_sdk_tools(self, eip_tools: list[dict]) -> list[Tool]:
    """Build Copilot SDK Tool objects from EIP tool definitions."""
    
    if not self.dispatcher:
        return []

    sdk_tools = []
    for eip_tool in eip_tools:
        tool_id = eip_tool.get("tool_id", "")
        name = eip_tool.get("name", tool_id)
        description = eip_tool.get("description", "")
        parameters = eip_tool.get("parameters", {})

        # Create a handler for this specific tool
        # Use a closure to capture tool_id
        def make_handler(tid):
            def tool_handler(invocation: ToolInvocation) -> ToolResult:
                return self._handle_tool_invocation(tid, invocation)
            return tool_handler

        # Create SDK Tool with handler
        sdk_tool = Tool(
            name=name,
            description=description,
            handler=make_handler(tool_id),
            parameters=parameters,
        )
        sdk_tools.append(sdk_tool)

    return sdk_tools
```

**Control Analysis:**
- **EIP-controlled**: Tool definitions source (name, description, parameters)
- **SDK-controlled**: `Tool()` class, handler callback mechanism
- **Closure pattern**: Each tool gets independent handler, captures `tool_id` in scope

**Design Note**: The closure pattern is correct and necessary. Each tool needs its own handler that knows its `tool_id`.

---

#### C. `src/eip/llm/copilot.py::_handle_tool_invocation()`

```python
def _handle_tool_invocation(self, tool_id: str, invocation: ToolInvocation) -> ToolResult:
    """Handle a tool invocation from Copilot SDK."""
    
    if not self.dispatcher:
        return ToolResult(
            text_result_for_llm="Error: No dispatcher configured",
            result_type="failure",
            error="ToolDispatcher not available",
        )

    try:
        # Import here to avoid circular dependencies
        from eip.llm.dispatcher import ToolCall

        # Convert SDK invocation to EIP ToolCall
        tool_call = ToolCall(
            tool_id=tool_id,
            arguments=invocation.arguments or {},
        )

        # Execute through EIP's ToolDispatcher
        tool_result = self.dispatcher.execute_call(tool_call)

        # Convert EIP ToolResult to SDK ToolResult
        if tool_result.success:
            return ToolResult(
                text_result_for_llm=str(tool_result.result),
                result_type="success",
            )
        else:
            return ToolResult(
                text_result_for_llm=f"Error: {tool_result.error}",
                result_type="failure",
                error=tool_result.error or "Unknown error",
            )
    except Exception as e:
        # Catch any errors and return as failure to SDK
        return ToolResult(
            text_result_for_llm=f"Exception: {str(e)}",
            result_type="failure",
            error=str(e),
        )
```

**Control Analysis:**
- **Input**: `ToolInvocation` from SDK (tool_name, arguments)
- **Conversion**: SDK invocation → EIP `ToolCall` (tool_id, arguments)
- **Execution**: `dispatcher.execute_call()` (EIP-controlled)
- **Output**: EIP `ToolResult` → SDK `ToolResult`
- **EIP-controlled**: Everything after `ToolCall` creation
- **SDK-controlled**: `ToolInvocation` structure, `ToolResult` format

---

#### D. `src/eip/llm/agent.py::SimpleAgent.__init__()`

```python
def __init__(self, llm_client: LLMClient, repository_tool: RepositoryTool, max_iterations: int = 10):
    """Initialize agent."""
    self.llm_client = llm_client
    self.dispatcher = ToolDispatcher(repository_tool)
    self.max_iterations = max_iterations

    # Configure the LLM client with dispatcher if it supports tool execution.
    # For CopilotLLMClient, this enables real provider tool calling.
    # For other clients, this is a no-op (they don't have a dispatcher attribute).
    if hasattr(llm_client, "dispatcher") and not llm_client.dispatcher:
        llm_client.dispatcher = self.dispatcher
```

**Control Analysis:**
- **EIP-controlled**: `ToolDispatcher` creation and configuration
- **Assumption**: Duck typing - assumes objects with `dispatcher` attribute support tool calling
- **Risk**: No type contract, fragile interface

---

#### E. `tests/run_live_integration_test.py::main()`

**Flow:**
```python
# 1. Create RepositoryTool
repo = RepositoryTool(repo_root)

# 2. Create ToolDispatcher
dispatcher = ToolDispatcher(repo)

# 3. Create wrapper to track tool calls
tool_calls_received = []
original_execute = dispatcher.execute_call

def tracking_execute_call(tool_call):
    tool_calls_received.append({
        "tool_id": tool_call.tool_id,
        "arguments": tool_call.arguments,
    })
    result = original_execute(tool_call)
    print tracking info
    return result

dispatcher.execute_call = tracking_execute_call

# 4. Create CopilotLLMClient WITH dispatcher
client = CopilotLLMClient(
    model="claude-haiku-4.5",
    dispatcher=dispatcher,
)

# 5. Send requirement to LLM
requirement = """
Analyze the EIP repository structure and configuration.

Determine:
1. What is the main purpose of this project (read README or key docs)?
2. What are the key components in the src/ directory structure?
3. How does the tool calling integration work (explain the flow)?

Use the available repository tools to explore files and understand 
the project. Provide a clear summary of your findings.

Do NOT modify any files.
"""

# 6. Get tools from dispatcher
tools = dispatcher.get_tools()

# 7. Send to LLM with tools
result = client.complete(
    messages=[{"role": "user", "content": requirement}],
    tools=tools,
    system_prompt="You are a helpful code analyzer...",
)

# 8. Capture and verify tool calls
print tool calls received: 3
  - repo.list_files (path: '.')
  - repo.list_files (path: 'src')
  - repo.read_file (path: 'README.md')
```

**Verification Method:**
- Wraps `dispatcher.execute_call()` to track invocations
- Verifies tool calls occurred via tracking list
- Confirms each call was a known tool ID
- Validates result structure

---

#### F. `tests/test_copilot_tool_calling.py::TestLiveToolCallingIntegration`

```python
@pytest.mark.skip(reason="Live integration test - requires Copilot API access")
@pytest.mark.integration
def test_live_copilot_tool_calling_flow(self):
    """
    LIVE TEST: Real Copilot LLM requests and executes EIP repository tools.
    
    [Implementation similar to run_live_integration_test.py]
    """
```

**Skip/Deselection Mechanism:**
- `@pytest.mark.skip` decorator tells pytest to skip this test
- `skip()` marker is always applied, not conditional
- When pytest collects tests: `1 deselected`
- Test does NOT run in normal test suite (`pytest tests/`)
- Only runs when executed directly or with special flags

**Why it's marked skip:**
- Requires Copilot authentication (external resource)
- Makes real API calls (network dependency)
- Consumes Copilot usage quota
- Would break CI/CD without authentication
- Not part of unit test suite

---

## 2. CRITICAL ARCHITECTURAL QUESTION

### "Can the Copilot SDK/runtime independently access the repository filesystem, execute shell commands, or use its own native tools during this session, bypassing EIP's ToolDispatcher?"

#### Current Implementation Analysis

**What we know from the code:**

1. **CopilotClient Initialization:**
   ```python
   async with CopilotClient(
       github_token=self.github_token,
       working_directory=self.working_directory,  # ⚠️ RISK POINT
   ) as client:
   ```

2. **Session Creation:**
   ```python
   async with await client.create_session(**session_config) as session:
   ```

3. **Session Config contains:**
   - `on_permission_request`: PermissionHandler.approve_all
   - `model`: self.model
   - `system_message`: Optional system prompt
   - `tools`: List of our custom Tool objects (if dispatcher configured)

**Analysis:**

| Factor | Status | Risk Level |
|--------|--------|-----------|
| **Only custom tools passed** | ✅ Yes | Low |
| **working_directory parameter** | ⚠️ Passed | **HIGH** |
| **PermissionHandler.approve_all** | ⚠️ Enabled | **HIGH** |
| **System prompt control** | ✅ EIP-controlled | Low |
| **Model parameter** | ✅ EIP-controlled | Low |
| **SDK native capabilities** | ❓ Unknown | **UNKNOWN** |

#### The `working_directory` Risk

The Copilot SDK is initialized with:
```python
working_directory=self.working_directory
```

**Potential consequences:**

1. **Direct File System Access**: The Copilot runtime may have native capabilities to:
   - Read files from `working_directory`
   - List directories
   - Execute commands in the working directory
   - These operations could bypass our ToolDispatcher entirely

2. **PermissionHandler.approve_all**: This setting may grant the Copilot runtime permission to:
   - Access the working directory
   - Execute operations without additional authorization
   - Use any built-in tools it provides

3. **SDK-Native Tools**: The Copilot SDK may provide built-in tools such as:
   - File system operations
   - Shell command execution
   - Git operations
   - Code execution
   - These would NOT be custom Tool objects and would NOT go through our handlers

#### What the Live Test Actually Proves

**Proven:**
- ✅ The LLM requested 3 specific repository tools
- ✅ The tool calls went through `ToolDispatcher`
- ✅ No errors occurred during tool execution
- ✅ Tool results were returned to the LLM

**NOT Proven:**
- ❌ The LLM cannot access the filesystem directly
- ❌ The LLM cannot execute shell commands
- ❌ The LLM cannot use SDK-native tools
- ❌ The LLM did NOT use alternative access methods

**Why:**
- The test only observes what the LLM chose to do
- The LLM might have legitimately chosen NOT to use shell commands
- The test doesn't attempt to prevent direct access
- The test doesn't verify what SDK capabilities exist

#### Architectural Guarantee Status

| Guarantee | Level | Explanation |
|-----------|-------|-------------|
| **"Only EIP-defined tools are available"** | ❌ NOT Guaranteed | SDK may have native tools |
| **"LLM cannot access filesystem directly"** | ❌ NOT Guaranteed | `working_directory` parameter enables access |
| **"LLM cannot execute shell commands"** | ❌ NOT Guaranteed | SDK may have this capability |
| **"All operations go through ToolDispatcher"** | ❌ NOT Guaranteed | Only custom tools guaranteed |
| **"RepositoryTool enforces access control"** | ✅ Guaranteed | Only for tools routed through it |

#### Specific SDK Knowledge Gaps

We do NOT know:

1. **SDK-Native Tools**: Does Copilot SDK provide built-in tools for:
   - File system access?
   - Shell command execution?
   - Git operations?
   - Code execution?

2. **Permission Scope**: What does `PermissionHandler.approve_all` actually approve?
   - Only our custom tools?
   - Or also SDK-native operations?

3. **Working Directory Behavior**: What can the SDK do with `working_directory`?
   - Just set the context?
   - Or enable direct filesystem access?

4. **Runtime Capabilities**: What capabilities does Claude Haiku 4.5 have when running via Copilot SDK?
   - Same as base model?
   - Plus Copilot-specific tools?
   - Plus filesystem access?

#### How to Verify

To definitively answer this question, we would need to:

1. **Inspect SDK Source**: Review `copilot` package for native capabilities
2. **Test LLM Boundaries**: Create tests where LLM attempts:
   - Direct file read: "Read /etc/passwd"
   - Shell execution: "Run: ls -la /"
   - Git commands: "Show git log"
   - And observe what happens
3. **Review SDK Documentation**: Look for:
   - Built-in tool definitions
   - Permission model
   - Capabilities and limitations
4. **Test Isolation**: Run SDK without tools parameter and see what the LLM can do

---

## 3. ARCHITECTURAL WEAKNESSES

### Weakness #1: Duck Typing for Dispatcher Configuration

**Code:**
```python
# In SimpleAgent.__init__:
if hasattr(llm_client, "dispatcher") and not llm_client.dispatcher:
    llm_client.dispatcher = self.dispatcher
```

**Issues:**

1. **No Type Contract**
   - Uses `hasattr()` instead of isinstance check
   - Assumes any object with `dispatcher` attribute is an LLM client
   - Could accidentally configure non-LLM objects

2. **Fragility**
   - If any other class gains a `dispatcher` attribute for unrelated reasons, it breaks
   - No IDE support or type checking
   - Maintainers won't know which classes this applies to

3. **Silent Failures**
   - If dispatcher configuration fails, no exception is raised
   - Future developers might not know this side-effect exists

**Better Approach:**
```python
# Use protocol/interface
from typing import Protocol

class ToolCallingSupportedLLMClient(Protocol):
    """LLM client that supports tool calling."""
    dispatcher: Optional[ToolDispatcher]

# Then use isinstance with protocol
if isinstance(llm_client, ToolCallingSupportedLLMClient):
    if not llm_client.dispatcher:
        llm_client.dispatcher = self.dispatcher
```

Or explicit type checking:
```python
from eip.llm.copilot import CopilotLLMClient

if isinstance(llm_client, CopilotLLMClient):
    if not llm_client.dispatcher:
        llm_client.dispatcher = self.dispatcher
```

**Current Risk Level:** ⚠️ Medium
- Works in practice
- But fragile and undocumented
- Could break silently if attribute names conflict

---

### Weakness #2: working_directory Parameter Enables Potential Bypass

**Code:**
```python
async with CopilotClient(
    github_token=self.github_token,
    working_directory=self.working_directory,  # ⚠️ RISK
) as client:
```

**Issues:**

1. **Unknown SDK Behavior**
   - We don't document what `working_directory` enables
   - SDK might use it to provide direct filesystem access
   - No restrictions or sandboxing

2. **PermissionHandler.approve_all**
   - Grants blanket permission to any operations
   - May enable SDK-native tools we're unaware of
   - No fine-grained permission control

3. **Unverified Security Assumption**
   - Implementation assumes working_directory is "safe"
   - No evidence that SDK cannot use it for direct access
   - Test only proves what LLM chose to do, not what it cannot do

**Better Approach:**
```python
# Option 1: Don't pass working_directory
async with CopilotClient(
    github_token=self.github_token,
    # working_directory=None,  # Don't enable filesystem access
) as client:

# Option 2: Use minimal working directory
async with CopilotClient(
    github_token=self.github_token,
    working_directory="/dev/null",  # Isolated
) as client:

# Option 3: Document and justify
async with CopilotClient(
    github_token=self.github_token,
    working_directory=self.working_directory,
    # NOTE: working_directory is used only for context, not direct access
    # All filesystem operations must go through our custom tools
) as client:
```

**Current Risk Level:** 🔴 High
- Unverified security assumption
- Implementation assumes SDK doesn't bypass our tools
- No evidence this assumption is valid

---

### Weakness #3: Permission Handler Grants Blanket Access

**Code:**
```python
session_config: dict[str, Any] = {
    "on_permission_request": PermissionHandler.approve_all,
    ...
}
```

**Issues:**

1. **No Granular Control**
   - `approve_all` means yes to everything
   - No way to selectively deny operations
   - No audit trail or logging

2. **Unknown Scope**
   - Don't know what permissions `approve_all` covers
   - May include file access, shell execution, etc.
   - No documentation of permission types

3. **Security Model**
   - Should be "deny by default" not "approve all"
   - We should explicitly approve only known operations

**Better Approach:**
```python
# Create custom permission handler
class RestrictedPermissionHandler:
    """Only approve our known tool operations."""
    def handle_permission_request(self, permission_type: str, operation: str):
        # Only approve operations related to our custom tools
        allowed = {"tool_call", "read_repository", "list_files", "search_code"}
        return operation in allowed

# Use it
session_config: dict[str, Any] = {
    "on_permission_request": RestrictedPermissionHandler(),
    ...
}
```

**Current Risk Level:** 🔴 High
- Blanket permission with no restrictions
- Could enable unexpected capabilities

---

### Weakness #4: Incomplete Tool Execution Verification

**Live Test Implementation:**
```python
# Wraps dispatcher.execute_call to track invocations
def tracking_execute_call(tool_call):
    tool_calls_received.append({...})
    result = original_execute(tool_call)
    return result
```

**Issues:**

1. **Only Tracks Explicit Calls**
   - Doesn't detect if SDK calls methods directly
   - Doesn't detect if LLM accesses filesystem without our tools
   - Doesn't track shell commands

2. **No Integrity Verification**
   - Doesn't confirm data actually went through RepositoryTool
   - Could be monkey-patched or bypassed
   - No cryptographic signature or hash

3. **Test Only Observes One Scenario**
   - LLM voluntarily chose to use our tools
   - Doesn't test if LLM can use other methods
   - Test passes even if alternative access exists

**Better Approach:**
```python
# Audit all repository access attempts
class AuditingRepositoryTool(RepositoryTool):
    def __init__(self, repo_path):
        super().__init__(repo_path)
        self.access_log = []
    
    def list_files(self, path: str):
        self.access_log.append(("list_files", path))
        return super().list_files(path)
    
    def read_file(self, path: str):
        self.access_log.append(("read_file", path))
        return super().read_file(path)

# Verify all access went through audit
def verify_all_access_audited():
    # Check that repository was NOT accessed any other way
    # (This would require instrumentation at OS level)
    pass
```

**Current Risk Level:** ⚠️ Medium
- Test is not comprehensive
- Only verifies happy path
- Doesn't detect alternative access methods

---

### Weakness #5: Circular Dependency Avoided with Local Import

**Code:**
```python
def _handle_tool_invocation(self, tool_id: str, invocation: ToolInvocation):
    try:
        # Import here to avoid circular dependencies
        from eip.llm.dispatcher import ToolCall
```

**Issues:**

1. **Indicates Design Tension**
   - Local import suggests circular dependency in module structure
   - `copilot.py` imports from `dispatcher.py` type hints
   - `dispatcher.py` probably imports from `copilot.py` or indirectly
   - Runtime import hides the dependency

2. **Performance Implication**
   - Import happens on every tool invocation
   - Should be cached after first import (Python caches modules)
   - But semantically unclear

3. **Type Checking Issues**
   - Type checkers may not understand local imports
   - `ToolCall` type not available at function signature level
   - Using `TYPE_CHECKING` would be clearer

**Better Approach:**
```python
# At top of file with TYPE_CHECKING guard
if TYPE_CHECKING:
    from eip.llm.dispatcher import ToolCall

# Runtime - actual import in __init__
def __init__(self, ...):
    from eip.llm.dispatcher import ToolCall
    self._ToolCall = ToolCall

def _handle_tool_invocation(self, tool_id: str, invocation: ToolInvocation):
    try:
        tool_call = self._ToolCall(
            tool_id=tool_id,
            arguments=invocation.arguments or {},
        )
```

**Current Risk Level:** ⚠️ Low-Medium
- Works correctly
- But indicates architectural issue
- Makes codebase harder to understand

---

## 4. CONTROL BOUNDARY DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    Real Copilot SDK / LLM                     │
│                   (GitHub Copilot Claude 4.5)                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  LLM Model Runtime                                      │ │
│  │  - Can receive requirement + tool definitions           │ │
│  │  - Can decide which tools to call                       │ │
│  │  - Potential access to working_directory?  ⚠️          │ │
│  │  - Potential native tools?  ⚠️                         │ │
│  │  - Potential shell commands?  ⚠️                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  SDK Tool Handler Mechanism                             │ │
│  │  - Receives ToolInvocation when LLM requests tool       │ │
│  │  - Has access to working_directory                      │ │
│  │  - Has permissions from PermissionHandler.approve_all   │ │
│  │  - Can theoretically access filesystem independently    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                  │
│                            │ Invokes handler callback         │
│                            ↓                                  │
└────────────────────────────┼──────────────────────────────────┘
                             │
                             │ ToolInvocation
                             ↓
                ┌──────────────────────────────┐
                │  CopilotLLMClient            │
                │  ._handle_tool_invocation()  │
                │                              │
                │  - Receives SDK invocation   │
                │  - Validates tool_id         │
                │  - Converts to ToolCall      │
                └──────────────────────────────┘
                             │
                             │ ToolCall (tool_id, arguments)
                             ↓
                ┌──────────────────────────────┐
                │  ToolDispatcher              │
                │  .execute_call()             │
                │                              │
                │  - Validates tool_id         │
                │  - Validates arguments       │
                │  - Routes to tool impl       │
                └──────────────────────────────┘
                             │
                             │ ToolCall
                             ↓
                ┌──────────────────────────────┐
                │  RepositoryTool              │
                │  .list_files()               │
                │  .read_file()                │
                │  .search_code()              │
                │                              │
                │  - Path validation           │
                │  - Read-only enforcement     │
                │  - Traversal protection      │
                └──────────────────────────────┘
                             │
                             │ ToolResult
                             ↓
                ┌──────────────────────────────┐
                │  Convert to SDK ToolResult   │
                └──────────────────────────────┘
                             │
                             │ SDK ToolResult
                             ↓
    ┌────────────────────────────────────────────────┐
    │  Copilot SDK sends result to LLM              │
    │  LLM continues conversation or generates      │
    │  final response                               │
    └────────────────────────────────────────────────┘


RISK POINTS (marked ⚠️):
┌────────────────────────────────────────────────────────────────┐
│ 1. LLM has potential working_directory access                 │
│ 2. SDK handler has working_directory access                   │
│ 3. PermissionHandler.approve_all grants blanket permission     │
│ 4. Unknown SDK native tool capabilities                        │
│ 5. Unknown what operations approve_all permits                │
└────────────────────────────────────────────────────────────────┘

GUARANTEED CONTROL POINTS (✅):
┌────────────────────────────────────────────────────────────────┐
│ 1. Custom tools only - we define tool list                     │
│ 2. System prompt - EIP controlled                              │
│ 3. Tool handler callback - EIP code execution                  │
│ 4. ToolDispatcher validation - EIP-controlled                  │
│ 5. RepositoryTool enforcement - EIP-controlled                 │
│ 6. Result conversion - EIP-controlled                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. SUMMARY TABLE: What's Guaranteed vs Inferred

| Aspect | Status | Evidence | Confidence |
|--------|--------|----------|-----------|
| **LLM receives tools** | ✅ Guaranteed | Tools passed to create_session | Very High |
| **LLM decides to use tools** | ✅ Guaranteed | Live test shows LLM chose tools | High |
| **Our handlers are called** | ✅ Guaranteed | Handlers invoked when tools requested | High |
| **Tools routed through ToolDispatcher** | ✅ Guaranteed | Code shows explicit routing | Very High |
| **RepositoryTool methods executed** | ✅ Guaranteed | Tracked in live test | High |
| **LLM cannot access filesystem** | ❌ Inferred | Only assumed, not proven | Low |
| **LLM cannot execute shell commands** | ❌ Inferred | Only assumed, not proven | Low |
| **No SDK native tools available** | ❌ Inferred | Not verified | Low |
| **working_directory doesn't enable access** | ❌ Inferred | Not documented or tested | Low |
| **PermissionHandler.approve_all is safe** | ❌ Inferred | Not verified | Low |

---

## 6. FINAL ASSESSMENT

### Architectural Correctness

**For the specific tests we ran:**
- ✅ Tool calling flow works correctly
- ✅ Handlers are invoked
- ✅ ToolDispatcher routes calls
- ✅ RepositoryTool executes operations
- ✅ Results returned to LLM

**For the broader security model:**
- ⚠️ Multiple unverified assumptions about SDK behavior
- 🔴 `working_directory` parameter is a potential bypass vector
- 🔴 `PermissionHandler.approve_all` grants blanket permissions
- ⚠️ Duck typing for dispatcher configuration is fragile
- ❓ SDK native capabilities are unknown

### Confidence Level

| Claim | Confidence |
|-------|-----------|
| "Our tool calling works" | 95% |
| "LLM went through ToolDispatcher for requested tools" | 90% |
| "LLM cannot bypass our controls" | 30% |
| "This is production-ready" | 40% |

### Recommendations for Hardening

**High Priority:**
1. Remove or restrict `working_directory` parameter
2. Replace `PermissionHandler.approve_all` with explicit permission model
3. Verify SDK has no native filesystem/shell capabilities
4. Document security assumptions explicitly

**Medium Priority:**
5. Replace `hasattr()` duck typing with explicit type contracts
6. Add comprehensive test attempting LLM bypass
7. Instrument repository access at OS level to verify all goes through RepositoryTool

**Low Priority:**
8. Move circular dependency imports to module level with TYPE_CHECKING
9. Add SDK capability documentation
10. Create security audit trail

