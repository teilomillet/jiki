# MCP Client Overview

Jiki provides two levels of MCP (Model Context Protocol) clients based on a hybrid inheritance/protocol approach:

1. **`BaseMCPClient`**: Abstract base class defining the structure and shared utilities for MCP clients. Designed for **extension** if you need custom transport logic or behaviors.
2. **`JikiClient`**: The standard, concrete, full-featured client inheriting from `BaseMCPClient`. Implements the complete `IMCPClient` protocol using `fastmcp`. Recommended for **most use cases**.

*Deprecated Aliases:* For backward compatibility, `MCPClient` aliases `BaseMCPClient` and `EnhancedMCPClient` aliases `JikiClient`, but these will be removed in a future version and emit `DeprecationWarning`.

---

## 1. BaseMCPClient (Abstract Base)

Subclass `BaseMCPClient` when you need to build a custom MCP client, for example:
- To integrate with a transport library other than `fastmcp`.
- To add custom retry logic around RPC calls.
- To implement specialized error handling or logging.

You would inherit from `BaseMCPClient` and implement the abstract `_call_rpc` method to handle the actual communication.

```python
# Conceptual example - Do not run directly
from jiki.mcp_client import BaseMCPClient
from typing import Any
# import my_custom_rpc_library # Assume this exists

class MyCustomClient(BaseMCPClient):
    def __init__(self, endpoint: str):
        super().__init__(connection_info=endpoint)
        # self._rpc_conn = my_custom_rpc_library.connect(endpoint)

    async def _call_rpc(self, method: str, params: dict | None = None) -> Any:
        # Implementation using the custom library
        # response = await self._rpc_conn.call(method, params)
        # if response.is_error:
        #     raise ConnectionError(f"RPC Error: {response.error_message}")
        # return response.result
        pass # Placeholder

# You would then need to implement the full IMCPClient interface methods
# often by calling self._call_rpc and self._process_mcp_result
```

- **Extensibility**: Provides a clear structure for building custom clients.
- **Shared Logic**: Inherits utility methods like `_process_mcp_result` (for parsing standard MCP results).

### When to use `BaseMCPClient`
* You are building a significantly different client implementation (e.g., different transport).
* You need fine-grained control over the RPC call mechanism itself.
* You are comfortable implementing the required abstract methods and potentially the public interface methods (`discover_tools`, etc.) using `_call_rpc`.

---

## 2. JikiClient (Standard Concrete Client)

This is the **recommended client** for standard Jiki usage. It bundles key MCP capabilities using `fastmcp`:
- Tool discovery
- Resource listing & reading
- Roots management
- Interaction tracing
- Spec-compliant handshakes

### Construction

It's typically constructed **internally** by the `Jiki()` factory function based on the `mcp_mode`, `mcp_script_path`, or `mcp_url` arguments provided.

```python
# Example of how Jiki() might create it internally for stdio
from jiki.mcp_client import JikiClient 

connection_info = {"type": "stdio", "script_path": "servers/calculator_server.py"}
client = JikiClient(connection_info=connection_info)

# Example for SSE
# connection_info_sse = {"type": "sse", "url": "http://localhost:8000/mcp"}
# client_sse = JikiClient(connection_info=connection_info_sse)
```

### Key Methods (used by `JikiOrchestrator`)

- `initialize()`: Handles the MCP handshake.
- `discover_tools()`: Retrieves tool schemas.
- `execute_tool_call()`: Runs a specific tool.
- `list_resources()`, `read_resource()`: Manages resources.
- `list_roots()`, `send_roots_list_changed()`: Manages roots.

### Tracing & Server Log Capture

The `JikiClient` automatically logs all MCP interactions when a `TraceLogger` is provided (via `Jiki(trace=True)`). This includes:
  - JSON‑RPC handshake records
  - `<mcp_tool_call>` blocks
  - `<mcp_tool_result>` blocks
  - Server‑side log entries emitted via the `utilities/logging/log` notification (per the MCP spec)

Each saved trace bundle includes handshakes, tool calls/results, and any server-side log entries.

```python
# Example trace output fragment
# (Assuming logger is active)

# MCP call log
print("[DEBUG] Calling MCP method: tools/call") 
# ... JSON-RPC request logged ...

# MCP result log
print("[DEBUG] Received MCP result for tools/call")
# ... JSON-RPC response logged ...

# Or for handshakes:
print("[DEBUG] Performing MCP initialize handshake...")

# Traces are stored by the TraceLogger passed to Jiki()

# Example of accessing traces after a run:
# from jiki import Jiki
# jiki_instance = Jiki(trace=True, ...)
# jiki_instance.process("...")
# traces = jiki_instance.get_traces()
# for t in traces:
#     print(t)
```

---

## Choosing the Right Client

| Feature               | `BaseMCPClient` (Abstract) | `JikiClient` (Concrete) |
| --------------------- | -------------------------- | ------------------------- |
| Handshake management  | No (must be impl. by subclass) | Yes (via `initialize`)   |
| Tool discovery        | No (must be impl. by subclass) | Yes (`discover_tools`)   |
| Resource & roots      | No (must be impl. by subclass) | Yes (built-in methods)   |
| Tracing & logging     | No (subclass responsibility) | Yes (built-in, needs logger) |
| Transport Agnostic    | Yes                        | No (uses `fastmcp`)      |
| Ready to Use          | No                         | Yes                      |
| Extensibility Point   | Yes                        | Limited (composition pref.)|
| Default via `Jiki()`  | No                         | Yes                      |

Use **`JikiClient`** (implicitly via `Jiki()`) for a complete, ready‑to‑use MCP implementation based on `fastmcp`. Subclass **`BaseMCPClient`** only if you need to build a custom client with different transport or core RPC logic.

---

## 3. Easy to Learn, Hard to Master

- **Zero boilerplate**: The `Jiki()` factory handles client creation and configuration automatically for the common case.
- **Protocol‑driven**: Swap in your own transport (by subclassing `BaseMCPClient`), tool client, or root manager by implementing the corresponding interface and manually constructing `JikiOrchestrator`.
- **Advanced tracing**: `JikiClient` (when given a logger by `Jiki()`) automatically logs every handshake, call, and result for deep inspection.
- **Error resilience**: Catches and formats JSON‑RPC errors, falling back to human‑readable messages.

With `Jiki()`, you get a robust MCP implementation in a few lines—yet the underlying `BaseMCPClient` structure allows plugging in custom behavior when needed.

```python
# Easy to learn: default orchestrator creation via Jiki()
from jiki import Jiki

# Jiki() uses JikiClient internally
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py" 
)
# ... use orchestrator ...
```

```python
# Harder to master: manually creating orchestrator with custom client
from jiki.orchestrator import JikiOrchestrator
from jiki.models.litellm import LiteLLMModel
# from my_custom_client import MyCustomClient # Assume this exists

# model = LiteLLMModel(...)
# custom_client = MyCustomClient(...)
# tools = [...]

# orch = JikiOrchestrator(
#     model=model,
#     mcp_client=custom_client,
#     tools_config=tools
# )
```
