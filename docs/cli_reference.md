# Jiki Command-Line Reference

This guide provides a comprehensive reference for using Jiki's command-line interface (CLI). All examples include expected outputs and are organized by common use cases.

## Overview

The Jiki CLI is accessed via `python -m jiki.cli` and provides three main commands:

- `run` - Launch an interactive chat session
- `process` - Process a single query
- `trace` - Manage interaction traces

## Command Cheat Sheet

| Task | Command |
|------|---------|
| **Interactive Chat** | `python -m jiki.cli run --auto-discover --mcp-script-path PATH` |
| **Process Query** | `python -m jiki.cli process --auto-discover --mcp-script-path PATH "QUERY"` |
| **With Custom Tools** | `python -m jiki.cli run --tools tools.json --mcp-script-path PATH` |
| **With Custom Model** | `python -m jiki.cli run --model MODEL_NAME --auto-discover --mcp-script-path PATH` |
| **Using HTTP Transport** | `python -m jiki.cli run --auto-discover --mcp-mode sse --mcp-url URL` |
| **Get Detailed Output** | `python -m jiki.cli process --detailed --show-tools --auto-discover --mcp-script-path PATH "QUERY"` |
| **Export Traces** | `python -m jiki.cli trace export --output traces.jsonl` |

## Environment Setup

Before using Jiki, set up your environment:

```bash
# Set API key for your LLM provider (default is Anthropic)
export ANTHROPIC_API_KEY=your_key_here

# Or for other providers 
export OPENAI_API_KEY=your_key_here
export GOOGLE_API_KEY=your_key_here
export MISTRAL_API_KEY=your_key_here
```

## Interactive Chat (`run`)

The `run` command launches an interactive chat session where you can have a multi-turn conversation with the LLM using available tools.

### Basic Usage

```bash
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using default model and discovering tools from servers/calculator_server.py...
[INFO] Tools discovered: add, subtract, multiply, divide
>> What is 25 * 16?
To calculate 25 * 16, I'll use the multiply tool.

25 * 16 = 400

>> Can you calculate 128 / 4?
I'll calculate 128 / 4 using the divide tool.

128 / 4 = 32

>> exit
[INFO] Interactive session ended.
```

### Options

```bash
python -m jiki.cli run --help
```

**Expected Output:**
```
usage: jiki.cli run [-h] [--model MODEL] [--trace-dir TRACE_DIR]
                    [--mcp-mode {stdio,sse}] [--mcp-script-path MCP_SCRIPT_PATH]
                    [--mcp-url MCP_URL]
                    [--tools TOOLS | --auto-discover]

options:
  -h, --help            show this help message and exit
  --model MODEL, -m MODEL
                        Model name (e.g., 'anthropic/claude-3-haiku-20240307'). Uses default if omitted.
  --trace-dir TRACE_DIR
                        Directory to store interaction traces (default: ./interaction_traces)

MCP Connection:
  --mcp-mode {stdio,sse}
                        MCP transport mode (default: stdio)
  --mcp-script-path MCP_SCRIPT_PATH
                        Path to MCP server script (for stdio mode)
  --mcp-url MCP_URL     URL of MCP server (for sse mode)

Tool Configuration:
  --tools TOOLS, -t TOOLS
                        Tools config: path to JSON file or inline JSON list. Cannot be used with --auto-discover.
  --auto-discover, -a   Auto-discover tools from MCP server. Cannot be used with --tools.
```

### With Custom Model

```bash
python -m jiki.cli run --model openai/gpt-4o --auto-discover --mcp-script-path servers/calculator_server.py
```

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using model openai/gpt-4o and discovering tools from servers/calculator_server.py...
[INFO] Tools discovered: add, subtract, multiply, divide
>> 
```

### With HTTP Transport

```bash
# First start the MCP server with SSE transport
fastmcp run servers/calculator_server.py --transport sse --port 8000

# Then in another terminal
python -m jiki.cli run --auto-discover --mcp-mode sse --mcp-url http://localhost:8000
```

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using default model and connecting to MCP server at http://localhost:8000...
[INFO] Tools discovered: add, subtract, multiply, divide
>> 
```

## Single Query Processing (`process`)

The `process` command handles a single query and outputs the result, optionally with detailed information about tool calls and traces.

### Basic Usage

```bash
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py "What is 42 + 17?"
```

**Expected Output:**
```
To calculate 42 + 17, I'll use the add tool.

42 + 17 = 59
```

### Detailed Output

```bash
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py --detailed --show-tools "What is 7 * 8?"
```

**Expected Output:**
```
Result: To calculate 7 * 8, I'll use the multiply tool.

7 * 8 = 56

Tool Calls:
  - Tool: multiply
    Args: {"a": 7, "b": 8}
    Result: 56
```

### JSON Output

```bash
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py --detailed --json "What is 15 - 7?"
```

**Expected Output:**
```json
{
  "result": "To calculate 15 - 7, I'll use the subtract tool.\n\n15 - 7 = 8",
  "tool_calls": [],
  "traces": []
}
```

### With Tool Calls and Traces

```bash
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py --detailed --show-tools --show-traces --json "What is 15 - 7?"
```

**Expected Output:**
```json
{
  "result": "To calculate 15 - 7, I'll use the subtract tool.\n\n15 - 7 = 8",
  "tool_calls": [
    {
      "tool_name": "subtract",
      "arguments": {
        "a": 15,
        "b": 7
      },
      "result": 8
    }
  ],
  "traces": [
    {
      "type": "user_message",
      "timestamp": "2023-07-21T14:32:45.123456",
      "content": "What is 15 - 7?"
    },
    {
      "type": "tool_call",
      "timestamp": "2023-07-21T14:32:46.234567",
      "tool_name": "subtract",
      "arguments": {
        "a": 15,
        "b": 7
      }
    },
    {
      "type": "tool_result",
      "timestamp": "2023-07-21T14:32:46.345678",
      "tool_name": "subtract",
      "result": 8
    }
  ]
}
```

### Options

```bash
python -m jiki.cli process --help
```

**Expected Output:**
```
usage: jiki.cli process [-h] [--model MODEL] [--trace-dir TRACE_DIR]
                       [--mcp-mode {stdio,sse}] [--mcp-script-path MCP_SCRIPT_PATH]
                       [--mcp-url MCP_URL]
                       [--tools TOOLS | --auto-discover]
                       [--trace] [--detailed] [--show-tools]
                       [--show-traces] [--json]
                       [query]

positional arguments:
  query                 Query text (reads from stdin if omitted)

options:
  -h, --help            show this help message and exit
  --model MODEL, -m MODEL
                        Model name (e.g., 'anthropic/claude-3-haiku-20240307'). Uses default if omitted.
  --trace-dir TRACE_DIR
                        Directory to store interaction traces (default: ./interaction_traces)
  --trace               Enable interaction tracing for this run

MCP Connection:
  --mcp-mode {stdio,sse}
                        MCP transport mode (default: stdio)
  --mcp-script-path MCP_SCRIPT_PATH
                        Path to MCP server script (for stdio mode)
  --mcp-url MCP_URL     URL of MCP server (for sse mode)

Tool Configuration:
  --tools TOOLS, -t TOOLS
                        Tools config: path to JSON file or inline JSON list. Cannot be used with --auto-discover.
  --auto-discover, -a   Auto-discover tools from MCP server. Cannot be used with --tools.

Detailed Output:
  --detailed, -d        Output detailed response object instead of just the result string
  --show-tools          Include tool calls in detailed output (requires --detailed)
  --show-traces         Include raw traces in detailed output (requires --detailed)
  --json, -j            Output detailed response in JSON format (requires --detailed)
```

## Trace Management (`trace`)

The `trace` command helps manage interaction traces, allowing you to export them for analysis or debugging.

### Export Traces

```bash
python -m jiki.cli trace export --output traces.jsonl
```

**Expected Output:**
```
[INFO] Exporting traces to traces.jsonl...
[INFO] Exported 3 trace(s).
```

### Options

```bash
python -m jiki.cli trace --help
```

**Expected Output:**
```
usage: jiki.cli trace [-h] {export} ...

positional arguments:
  {export}    Trace action
    export    Export accumulated traces from the default trace directory to a file

options:
  -h, --help  show this help message and exit
```

```bash
python -m jiki.cli trace export --help
```

**Expected Output:**
```
usage: jiki.cli trace export [-h] --output OUTPUT

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output file path (e.g., traces.jsonl)
```

## Common Patterns

### Reading Query from Standard Input

```bash
echo "What is 100 / 5?" | python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py
```

**Expected Output:**
```
To calculate 100 / 5, I'll use the divide tool.

100 / 5 = 20
```

### Using Custom Tools

```bash
python -m jiki.cli run --tools tools.json --mcp-script-path servers/calculator_server.py
```

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using default model and tools from tools.json...
[INFO] Connected to MCP server via stdio transport
>> 
```

### Debugging with Traces

```bash
# Run a session with tracing
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
# ...use the session...

# Later, export the traces
python -m jiki.cli trace export --output debug_session.jsonl
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"No such file or directory"** | Check that the path to the MCP script is correct |
| **"Failed to initialize Jiki"** | Ensure your API key is set and the MCP server is accessible |
| **"Connection refused"** | For SSE mode, ensure the server is running on the specified port |
| **"No query provided"** | When using `process`, provide a query as an argument or via stdin |
| **"No tool schemas found"** | Check that your MCP server properly exposes tools for discovery |

## Next Steps

After exploring the CLI, you might want to:

1. Learn how to create your own MCP tool servers with [FastMCP](https://github.com/fastmcp/fastmcp)
2. Integrate Jiki into your Python application using the programmatic API
3. Explore advanced features like custom prompt builders and conversation state management 