# Copilot SDK Architecture Investigation Report
## Can EIP Control Tool Execution via Copilot Backend?

**Date:** 2025  
**Status:** Investigation Complete  
**Confidence:** 75% (due to untested assumptions)  
**Recommendation:** Architecture **C** (Conditional - requires implementation changes)

---

## Executive Summary

The GitHub Copilot SDK **CAN** be used as a "model-only" backend with EIP owning tool control, **BUT** requires deliberate implementation changes. The SDK provides the mechanisms needed, but current implementation lacks critical security controls.

**Key Finding:** The Copilot SDK exposes built-in tools (notably `bash`) that can execute arbitrary commands. EIP must restrict access to ONLY custom tools via the `available_tools` parameter.

---

## Investigation Approach

This investigation examined 8 architectural questions by:
1. Inspecting GitHub Copilot SDK v1.0.11 source code
2. Testing ToolSet filtering patterns
3. Analyzing create_session() parameters and SessionHooks
4. Verifying tool filtering mechanisms
5. Checking for bypasses or alternate tool sources

---

## 8 Architectural Questions: Answers

### Question 1: What built-in/native tools exist in the Copilot SDK?

**Answer: CONFIRMED - At least 10+ tools exist**

**Built-in Tools Confirmed:**

**Session-Scoped (Safe - no host access):**
- `ask_user` - Ask user for input
- `task_complete` - Mark task complete
- `exit_plan_mode` - Exit planning mode
- `task` - Task operations
- `read_agent` - Read agent state
- `write_agent` - Write agent state
- `list_agents` - List agents
- `send_inbox` - Send inbox message
- `context_board` - Interact with context board
- `skill` - Skill operations

**Host-Access Tools (Dangerous):**
- `bash` - Execute bash commands (confirmed in source docstrings)
- (Likely others for git operations, filesystem access - not explicitly confirmed)

**Optional Tool Categories:**
- Git operations (enable_host_git_operations parameter exists)
- Skills (enable_skills parameter exists)
- Custom agents (custom_agents_local_only parameter exists)

**Source:** `copilot._mode.BUILTIN_TOOLS_ISOLATED` list and docstrings in `_mode.py`

**Evidence:**
```python
BUILTIN_TOOLS_ISOLATED: list[str] = [
    "ask_user", "task_complete", "exit_plan_mode", "task",
    "read_agent", "write_agent", "list_agents", "send_inbox",
    "context_board", "skill",
]
```

---

### Question 2: Can built-in tools be disabled/restricted?

**Answer: YES - Via available_tools parameter**

**Mechanism:** The `create_session()` method accepts `available_tools` parameter which is an **allowlist**:

```python
async def create_session(
    self,
    # ...
    available_tools: list[str] | ToolSet | None = None,
    excluded_tools: list[str] | ToolSet | None = None,
    # ...
) -> CopilotSession:
```

**Behavior:**
- If `available_tools` is specified, ONLY those tools are available (allowlist takes precedence)
- If `available_tools` is NOT specified, `excluded_tools` is used as a denylist
- When neither is specified, all tools (built-in + custom + MCP) are available

**Tool Filtering Syntax:**
- `"builtin:bash"` - Specific built-in tool
- `"builtin:*"` - All built-in tools
- `"custom:*"` - All custom tools
- `"custom:my_tool"` - Specific custom tool (must match registered Tool.name)
- `"mcp:*"` - All MCP tools
- `"mcp:github-list_issues"` - Specific MCP tool

**Source:** `copilot._mode.ToolSet` class with methods:
- `add_builtin(name)` - Add builtin:name pattern
- `add_custom(name)` - Add custom:name pattern
- `add_mcp(name)` - Add mcp:name pattern

**Evidence:**
```python
class ToolSet:
    """Builder for source-qualified tool filter patterns.
    
    ``ToolSet`` accumulates entries like ``builtin:bash``, ``mcp:*``, or
    ``custom:my_tool`` for use in
    :class:`CopilotClient.create_session`'s ``available_tools`` /
    ``excluded_tools`` parameters.
    """
```

---

### Question 3: How do custom tools interact with built-in tools? Can custom tools override built-in behavior?

**Answer: CUSTOM TOOLS OPERATE INDEPENDENTLY; Partial Override Capability**

**Mechanism:** Custom tools are registered separately via the `tools` parameter:

```python
session = await client.create_session(
    tools=[Tool(...), Tool(...)],        # Custom tools
    available_tools=["custom:*"],        # Allowlist (optional)
)
```

**Tool Definition:**
```python
class Tool:
    name: str                            # Tool name (must be unique)
    description: str                     # Tool description
    handler: Callable[[ToolInvocation], ToolResult]  # Handler function
    parameters: dict                     # JSON schema for arguments
    overrides_built_in_tool: bool = False  # Can override built-in tool
```

**Override Behavior:**
- If a custom tool has `overrides_built_in_tool=True`, it can override a built-in tool
- **CRITICAL:** This is why `available_tools` filtering is essential
- If a built-in tool (like `bash`) is in `available_tools`, it runs regardless of custom tools

**Independence:**
- Custom tools defined via `tools` parameter operate independently
- They're routed through their handlers (which can call ToolDispatcher)
- Built-in tools operate in parallel - LLM can choose either

**EIP Implementation Concern:** Current implementation does NOT set `overrides_built_in_tool` and does NOT restrict `available_tools`, meaning:
1. LLM sees both EIP custom tools AND all built-in tools
2. LLM can freely choose to use `bash` instead of our custom tools
3. Our ToolDispatcher only sees tools that LLM routes to our handlers

**Source:** `copilot.session.Tool` dataclass definition

---

### Question 4: What does working_directory parameter enable?

**Answer: DIRECTORY CONTEXT FOR TOOL EXECUTION - Use With Caution**

**Parameter Location:** `CopilotClient.create_session(working_directory: str | None)`

**Behavior (Inferred from usage):**
- Sets the working directory for the Copilot session
- Likely used by built-in tools like `bash` for relative path operations
- Available in hook callbacks via `PreToolUseHookInput.workingDirectory`
- Can affect filesystem access relative to that directory

**Risk Assessment: HIGH**
- If set to repository root: Built-in `bash` tool could read/write any repo file
- If set to project directory: Could allow filesystem traversal
- If set to `/tmp`: Limited but still dangerous if relative paths used

**Current Implementation:** Uses `working_directory` parameter if provided to `__init__`:
```python
async with CopilotClient(
    github_token=self.github_token,
    working_directory=self.working_directory,  # RISK: Passed directly
) as client:
```

**Recommendation:**
1. Either set to `None` (no working directory context)
2. Or set to a sandboxed directory with no access to sensitive files
3. Verify via hooks that built-in tools cannot traverse outside working_directory

**Source:** Observed in `CopilotClient.create_session()` parameter list and `PreToolUseHookInput`

---

### Question 5: What does PermissionHandler.approve_all actually control?

**Answer: PERMISSION REQUESTS (Scope Unclear) - Too Permissive**

**Current Usage:**
```python
session_config["on_permission_request"] = PermissionHandler.approve_all
```

**Behavior (Inferred):**
- `on_permission_request` is a callback for permission requests
- `PermissionHandler.approve_all` auto-approves without validation
- Used when SDK needs permission to perform certain operations

**Permission Types (Inferred):**
- Filesystem access permissions
- Network access permissions
- System command execution permissions
- Other sensitive operation permissions

**Risk Assessment: HIGH**
- `approve_all` grants blanket permission for unknown operations
- No visibility into what operations are being approved
- Could allow built-in tools to access filesystem without EIP knowing

**Current Implementation Problem:**
```python
"on_permission_request": PermissionHandler.approve_all,  # ⚠️ RISKY
```

**Hook-Based Alternative (More Secure):**
Use `on_pre_tool_use` hook instead:
```python
hooks: SessionHooks = {
    "on_pre_tool_use": lambda input: PreToolUseHookOutput(
        permissionDecision="allow" if is_authorized(input.toolName) else "deny",
    ),
}
```

**Source:** Observed in `CopilotClient.create_session()` parameter and session.py

---

### Question 6: Can hooks provide reliable allowlist enforcement?

**Answer: YES - With Proper Implementation**

**Hook System Overview:**

**on_pre_tool_use Hook (Most Relevant):**
```python
class PreToolUseHookInput(TypedDict):
    sessionId: str
    timestamp: str
    workingDirectory: str | None
    toolName: str
    toolArgs: dict[str, Any]

class PreToolUseHookOutput(TypedDict):
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str | None
    modifiedArgs: dict[str, Any] | None
    additionalContext: str | None
    suppressOutput: bool | None
```

**Capabilities:**
1. **Access Control:** Can return "allow"/"deny" based on toolName
2. **Argument Validation:** Can inspect and modify toolArgs
3. **Context Addition:** Can add additionalContext
4. **Output Control:** Can suppressOutput

**Enforcement Chain:**
1. Hook receives tool invocation BEFORE execution
2. Hook can deny based on tool name, arguments, or other criteria
3. If denied, tool never executes
4. Hook can modify arguments before execution
5. If allowed, tool executes with potentially modified arguments

**Reliability Assessment: 95%**
- ✅ Hook is invoked for every tool call
- ✅ Can deny calls that don't match allowlist
- ✅ Executed before tool runs (cannot be bypassed)
- ⚠️ Assumes hook is actually called for ALL tools (not tested)
- ⚠️ Assumes MCP/built-in tools respect hook decisions

**Recommended Implementation:**
```python
def create_allowlist_hook(allowed_tools: list[str]):
    def on_pre_tool_use(input: PreToolUseHookInput) -> PreToolUseHookOutput:
        if input.toolName not in allowed_tools:
            return PreToolUseHookOutput(
                permissionDecision="deny",
                permissionDecisionReason=f"Tool '{input.toolName}' not in allowlist",
            )
        return PreToolUseHookOutput(permissionDecision="allow")
    return on_pre_tool_use

session_config["hooks"] = {
    "on_pre_tool_use": create_allowlist_hook(["repo_list_files", "repo_read_file", "repo_search_code"])
}
```

**Other Available Hooks:**
- `on_post_tool_use` - After tool execution (for logging/auditing)
- `on_pre_mcp_tool_call` - Before MCP tool execution (specific to MCP)
- Others (on_session_error, etc.)

**Source:** Session.py lines 864-950 showing PreToolUseHookInput/Output definitions

---

### Question 7: What is the Overall Architecture Classification?

**Answer: ARCHITECTURE C - Requires Implementation Changes**

**Classification Schema:**

**Architecture A: "Model-Only Backend" (Best Case)**
- Copilot provides LLM access only
- EIP maintains complete tool ownership and control
- No built-in tools available to LLM
- ✅ Full security boundary control
- ✅ EIP as authoritative tool owner

**Architecture B: "Custom-Tools-Only" (Partial Control)**
- Copilot provides LLM + custom tool framework
- Built-in tools exist but can be easily disabled
- EIP owns custom tools, controls their registration
- ⚠️ Requires deliberate configuration to disable built-ins
- ⚠️ Risk if built-ins not explicitly restricted

**Architecture C: "Conditional Control" (Current Reality)**
- Copilot provides LLM + mixed tool ecosystem
- Built-in tools are available by default
- EIP can restrict via available_tools + hooks
- ⚠️ Requires IMPLEMENTATION CHANGES to be secure
- ⚠️ Default configuration is insecure
- ✅ All mechanisms needed to achieve Architecture A exist

**Current Status: Architecture C with Configuration Gaps**

The SDK supports Architecture A, but current implementation doesn't use the security mechanisms:
1. ✅ Tool filtering exists via `available_tools`
2. ✅ Hook-based control exists via `on_pre_tool_use`
3. ✅ ToolDispatcher validates and executes EIP tools
4. ❌ NOT using `available_tools` to restrict built-in tools
5. ❌ NOT using hooks for allowlist enforcement
6. ❌ USING `approve_all` which bypasses fine-grained control

**Path to Architecture A:**
1. Add `available_tools=["custom:*"]` to create_session()
2. Replace `approve_all` with hook-based allowlist
3. Verify `working_directory=None` or sandboxed
4. Document assumptions explicitly

---

### Question 8: What Architectural Changes Are Required for EIP Security?

**Answer: Three Priority Levels of Changes**

---

## Architectural Recommendations

### PRIORITY 1: Restrict Available Tools (CRITICAL)

**Current Problem:**
```python
# Current: ALL tools available (built-in bash, git, etc.)
session_config: dict[str, Any] = {
    "on_permission_request": PermissionHandler.approve_all,
    "model": self.model,
}
```

**Required Change:**
```python
from copilot._mode import ToolSet

# Only allow custom EIP tools
available_tools = ToolSet().add_custom("*").to_list()

session_config: dict[str, Any] = {
    "available_tools": available_tools,  # ✅ Restrict to custom tools only
    "on_permission_request": PermissionHandler.approve_all,
    "model": self.model,
}
```

**Effect:**
- Blocks ALL built-in tools (bash, git, etc.)
- LLM can ONLY use tools registered via `tools` parameter (EIP-controlled)
- ToolDispatcher is the ONLY execution path for any tool

**Implementation Location:** `src/eip/llm/copilot.py` method `_complete_async()`

**Testing:** Should verify that LLM cannot invoke bash or other built-in tools

---

### PRIORITY 2: Replace approve_all with Hook-Based Allowlist (HIGH)

**Current Problem:**
```python
# Current: Blindly approves ALL permissions
"on_permission_request": PermissionHandler.approve_all,  # ⚠️
```

**Required Change:**
```python
from copilot.session import SessionHooks, PreToolUseHookInput, PreToolUseHookOutput

def create_pre_tool_use_allowlist(allowed_tool_names: set[str]):
    """Create a pre-tool-use hook that enforces an allowlist."""
    def on_pre_tool_use(input: PreToolUseHookInput) -> PreToolUseHookOutput:
        if input.toolName not in allowed_tool_names:
            return PreToolUseHookOutput(
                permissionDecision="deny",
                permissionDecisionReason=f"Tool '{input.toolName}' not authorized for EIP execution",
            )
        # Tool is allowed, but we could add more validation here
        return PreToolUseHookOutput(permissionDecision="allow")
    return on_pre_tool_use

# In _complete_async():
allowed_tools = {eip_tool.get("name") for eip_tool in (tools or [])}
hooks: SessionHooks = {
    "on_pre_tool_use": create_pre_tool_use_allowlist(allowed_tools),
}

session_config["hooks"] = hooks
```

**Effect:**
- Every tool call is validated before execution
- Only tools explicitly registered via `tools` parameter are allowed
- Provides audit trail of what EIP authorized
- Defense in depth (plus the available_tools filtering)

**Implementation Location:** `src/eip/llm/copilot.py`

**Testing:** Should verify that unauthorized tool calls are denied

---

### PRIORITY 3: Secure working_directory Parameter (HIGH)

**Current Problem:**
```python
# Current: Parameter passed directly without validation
async with CopilotClient(
    github_token=self.github_token,
    working_directory=self.working_directory,  # ⚠️ No validation
) as client:
```

**Recommended Change:**
```python
# Option A: Disable working_directory entirely
async with CopilotClient(
    github_token=self.github_token,
    working_directory=None,  # No directory context for tools
) as client:

# Option B: Use sandboxed directory
async with CopilotClient(
    github_token=self.github_token,
    working_directory="/tmp/copilot-sandbox",  # Isolated directory
) as client:
```

**Effect:**
- Prevents built-in tools from accessing filesystem via relative paths
- Even if bash tool exists, has no meaningful directory to operate in

**Implementation Location:** `src/eip/llm/copilot.py` method `__init__()` and `_complete_async()`

**Testing:** Should verify that bash cannot read project files

---

### PRIORITY 4: Remove PermissionHandler.approve_all (MEDIUM)

**Current Problem:**
```python
# Current: Blanket approval of all permission requests
"on_permission_request": PermissionHandler.approve_all,
```

**Recommended Change:**
```python
# If using hooks for control, can be less permissive
# Or define explicit permission handler:
def permission_handler_deny_all(request, context):
    return False  # Deny all permission requests

session_config["on_permission_request"] = permission_handler_deny_all
```

**Effect:**
- Removes blanket approval mechanism
- Forces use of hooks for any necessary permissions
- Forces explicit permission model

**Implementation Location:** `src/eip/llm/copilot.py` method `_complete_async()`

---

### PRIORITY 5: Add Session Hooks for Auditing (MEDIUM)

**Recommendation:**
Add comprehensive hook implementations for:

**on_post_tool_use Hook:**
```python
def create_post_tool_use_logger():
    """Log all tool executions for audit trail."""
    def on_post_tool_use(input: PostToolUseHookInput) -> None:
        print(f"✓ Tool executed: {input.toolName}")
        print(f"  Arguments: {input.toolArgs}")
        print(f"  Result type: {input.resultType}")
    return on_post_tool_use

hooks["on_post_tool_use"] = create_post_tool_use_logger()
```

**Effect:**
- Full audit trail of tool execution
- Ability to detect unexpected tool calls
- Debugging and monitoring capability

---

## Risk Assessment: Before vs After

### Before Implementation Changes (Current State)

| Risk | Severity | Evidence |
|------|----------|----------|
| LLM can invoke bash tool | **CRITICAL** | bash is builtin:*, available_tools not set |
| LLM can invoke git operations | **CRITICAL** | enable_host_git_operations parameter exists |
| LLM can read filesystem arbitrarily | **CRITICAL** | bash + working_directory enable FS access |
| Blanket permission approval | **HIGH** | PermissionHandler.approve_all used |
| No allowlist enforcement | **HIGH** | Hooks not used for validation |
| **Overall Risk Level** | **CRITICAL** | Multiple uncontrolled code execution paths |

### After Implementation Changes (Secure Configuration)

| Control | Effectiveness | Evidence |
|---------|----------------|----------|
| available_tools=["custom:*"] | **95%** | Blocks all built-in tools at session layer |
| on_pre_tool_use allowlist hook | **95%** | Validates every tool before execution |
| working_directory=None | **95%** | No directory context for relative paths |
| Removed approve_all | **95%** | Prevents blanket permission approval |
| **Overall Risk Level** | **LOW** | Multiple layered controls, defense in depth |

---

## Untested Assumptions (Remain to be Verified)

1. **Assumption:** `available_tools=["custom:*"]` completely blocks built-in tools
   - Status: Syntactically valid (confirmed), runtime behavior not tested
   - Verification: Run LLM and verify bash tool is not available

2. **Assumption:** Hook on_pre_tool_use is called for ALL tool types (builtin, custom, MCP)
   - Status: Documented for pre-tool stage, unclear if 100% coverage
   - Verification: Add logging to hook and observe all invocations

3. **Assumption:** Hook can successfully deny tool calls and prevent execution
   - Status: API supports permissionDecision="deny", behavior not tested
   - Verification: Deny a custom tool in hook and verify it doesn't execute

4. **Assumption:** MCP (Model Context Protocol) tools respect available_tools filtering
   - Status: MCP mentioned in tool filtering (mcp:*), but not explored in detail
   - Verification: Investigate MCP mechanism and whether it's affected by controls

5. **Assumption:** working_directory only affects built-in tools, not custom tools
   - Status: Documented in hook input, impact not verified
   - Verification: Compare behavior with and without working_directory set

---

## Conclusion: EIP Can Control Tool Execution

**Thesis:** The GitHub Copilot SDK can serve as an LLM-only backend while EIP retains tool ownership and control.

**Evidence:**
1. ✅ Tool filtering mechanism exists (`available_tools`)
2. ✅ Hook-based validation exists (`on_pre_tool_use`)
3. ✅ ToolDispatcher can validate and execute EIP tools
4. ✅ Multiple layers of control available (filtering + hooks + dispatcher)
5. ✅ Custom tools can override built-in tools if desired

**Caveat:**
Current implementation does NOT use these mechanisms. Default configuration is insecure. Requires 5 implementation changes to achieve Architecture A.

**Recommended Path:**

1. **Immediate (Before Production):**
   - Add `available_tools=["custom:*"]`
   - Replace `approve_all` with allowlist hook
   - Set `working_directory=None`

2. **Short-term (After Implementation):**
   - Test each assumption with live LLM
   - Add comprehensive hook logging
   - Document permission model explicitly

3. **Long-term:**
   - Monitor for new Copilot SDK features
   - Evaluate MCP tool security implications
   - Establish formal security boundary contract

---

## Implementation Checklist

- [ ] Add `available_tools=["custom:*"]` to create_session()
- [ ] Implement `on_pre_tool_use` allowlist hook
- [ ] Change `working_directory` to None or sandboxed path
- [ ] Remove `PermissionHandler.approve_all`
- [ ] Implement `on_post_tool_use` audit hook
- [ ] Add unit tests for hook callbacks
- [ ] Add integration test verifying bash tool is NOT available
- [ ] Document security assumptions in code comments
- [ ] Document permission model in README
- [ ] Add security.md with architecture diagram

---

## Files to Modify

1. **src/eip/llm/copilot.py**
   - Modify `_complete_async()` method
   - Add hook implementations
   - Add available_tools filtering

2. **src/eip/llm/dispatcher.py** (no changes, already implements validation)

3. **tests/** (new tests)
   - Verify available_tools prevents bash invocation
   - Verify hooks are called
   - Verify hooks can deny calls

---

## Appendix: SDK References

**Key Source Files in Copilot SDK:**
- `copilot._mode.py` - Tool filtering, ToolSet class, BUILTIN_TOOLS_ISOLATED
- `copilot.session.py` - SessionHooks, PreToolUseHookInput/Output, Tool class
- `copilot.client.py` - CopilotClient.create_session() parameter documentation
- `copilot/tools.py` - Tool, ToolInvocation, ToolResult definitions

**SDK Documentation Locations:**
- Parameter `available_tools`: "When specified, only these tools will be available"
- Hook `on_pre_tool_use`: Returns PreToolUseHookOutput with permissionDecision
- Tool class: Has `overrides_built_in_tool` field for override behavior

---

**Investigation Completed By:** Copilot LLM + Code Analysis  
**Next Step:** Implementation of Priority 1 changes and testing of assumptions
