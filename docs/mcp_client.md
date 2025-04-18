# MCP Client Overview

Jiki provides two levels of MCP (Model Context Protocol) clients:

1. **MCPClient**: Low‑level wrapper around any MCP transport
2. **EnhancedMCPClient**: High‑level, opinionated client implementing discovery, resources, roots, tracing, and error handling

---

## 1. Raw MCPClient

Use this when you need direct control over your transport.

```python
from jiki.mcp_client import MCPClient

# 1. Choose a transport (e.g., stdio to a local script)
transport = 'python servers/calculator_server.py'
client = MCPClient(transport)

# 2. Call a tool by name with arguments
async def demo_raw():
    result = await client.execute_tool_call('add', {'a': 2, 'b': 3})
    print(result)  # → '5'
```

- **Flexibility**: Swap in any transport (stdio, HTTP, WebSocket) that fastmcp supports.
- **Low-level control**: You see exactly what payload goes over the wire.
- **Minimal dependencies**: No extra protocol handshakes or tracing logic.

### When to use Raw MCPClient
* You are building a custom transport or debugging low-level calls.
* You want full control of JSON-RPC messages without wrapper logic.
* You prefer a minimal dependency surface.

---

## 2. EnhancedMCPClient

This client bundles key MCP capabilities: tool discovery, resource listing, roots management, and interaction tracing.

### Construction

```python
from jiki.mcp_client import EnhancedMCPClient

# stdio transport to a local script
client = EnhancedMCPClient(
    transport_type='stdio',
    script_path='servers/calculator_server.py',
    roots=['file:///current/dir']
)
```

- **transport_type**: `'stdio'` or `'sse'`
- **script_path / URL**: Local script path for stdio, or HTTP endpoint for SSE
- **roots**: Optional list of file:// URIs or a callable returning them

### Tool Discovery & Invocation

```python
tools = await client.discover_tools()
# Example schema returned:
# [{
#   'tool_name': 'add',
#   'description': 'Add two numbers.',
#   'arguments': {
#       'a': {'type': 'integer', 'description': 'First addend'},
#       'b': {'type': 'integer', 'description': 'Second addend'}
#   },
#   'required': ['a', 'b']
# }, ...]
```

- **discover_tools()** runs an initialize handshake (MCP `initialize`/`initialized`) and returns tool schemas
- **execute_tool_call()** wraps calls in `<mcp_tool_call>` tags, logs traces, and returns raw string or JSON error payload

### When to use EnhancedMCPClient
* You want a turnkey MCP experience with minimal setup.
* You need automatic discovery of tools and resources.
* You rely on built-in logging and interaction tracing for auditing or debugging.
* You want spec‑compliant handshakes (`initialize`/`initialized`) without extra code.

### Resources & Roots

```python
# List and read resources
resources = await client.list_resources()
contents  = await client.read_resource(resources[0]['uri'])

# List and notify roots
roots = await client.list_roots()
await client.send_roots_list_changed()
```

- **list_resources() / read_resource(uri)** follow the MCP resources spec
- **list_roots() / send_roots_list_changed()** follow the MCP roots spec

**Note:** The above schemas include JSON-schema properties and `required` arrays for each argument. Nested or structured inputs (arrays, objects, Pydantic models) are preserved from the server's `inputSchema`, enabling deep validation on the client side. See the MCP Tools spec for structured inputs.

### Interaction Traces

```python
# After any calls, inspect traces for debugging
traces = client.get_interaction_traces()
for t in traces:
    print(t)
```

- Each trace includes JSON‑RPC handshakes, `<mcp_tool_call>`, `<mcp_tool_result>`, and notifications

---

## Choosing the Right Client

| Feature               | MCPClient (raw)         | EnhancedMCPClient (opinionated) |
| --------------------- | ----------------------- | ------------------------------- |
| Handshake management  | No                      | Yes                            |
| Tool discovery        | Manual                  | Automatic via `discover_tools` |
| Resource & roots      | No                      | Built‑in                       |
| Tracing & logging     | No                      | Yes                            |
| Custom transports     | Yes                     | Yes (via factory)              |
| Complexity            | Low‑level, minimal      | High‑level, feature‑rich        |

Use **MCPClient** if you need fine‑grained control or are building new transport layers. Use **EnhancedMCPClient** for a complete, ready‑to‑use MCP implementation that handles protocol details, discovery, and tracing for you.

---

## 3. Easy to Learn, Hard to Master

- **Zero boilerplate**: Default constructor and methods just work out of the box.
- **Protocol‑driven**: Swap in your own transport, tool client, or root manager by implementing the corresponding interface.
- **Advanced tracing**: Automatically logs every handshake, call, and result for deep inspection.
- **Error resilience**: Catches and formats JSON‑RPC errors, falling back to human‑readable messages.

With `EnhancedMCPClient`, you get a robust MCP implementation in a few lines—yet every stage is pluggable when you need custom behavior. 