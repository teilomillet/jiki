# Jiki

Jiki is a flexible LLM orchestration framework with built-in tool calling capabilities.

## Overview

Jiki provides a clean interface for building AI assistants that can use tools to solve problems. It orchestrates the interaction between language models and external tools using the MCP (Model Context Protocol).

## Features

- Seamless integration with LiteLLM for support of multiple LLM providers
- Tool calling through FastMCP infrastructure (manual config or auto-discovery)
- Flexible MCP client with multiple transport options (stdio, SSE)
- Structured conversation logging for training data generation
- Simple built-in interactive CLI (`run_ui()`)
- Primary CLI interface (`python -m jiki.cli ...`) for non-interactive processing, trace management, and interactive sessions.
- XML-based tool call format for clear model interaction

## Quick Start

Install Jiki (using [uv](https://github.com/astral-sh/uv) recommended):
```bash
# Using uv
uv pip install jiki
```

You need to export your API keys to the environment, ANTHROPIC_API_KEY is the default model:
```bash
export ANTHROPIC_API_KEY=<your_api_key>
```

Create and run an orchestrator programmatically:
```python
from jiki import create_jiki

# Create a pre-configured orchestrator using auto-discovery
# This assumes a compatible FastMCP server (like servers/calculator_server.py)
# is running or accessible via the specified mcp_script_path.
# It also uses default model and tracing settings.
orchestrator = create_jiki(
    auto_discover_tools=True,
    mcp_mode="stdio",
    mcp_script_path="servers/calculator_server.py"
)

# Launch the built-in interactive CLI
orchestrator.run_ui() # Defaults to frontend='cli'

# If using programmatically *without* run_ui:
# result = orchestrator.process("What is 2 + 2?")
# print(result)
# orchestrator.export_traces("my_traces.jsonl") # Manually save traces if needed
```

## Primary CLI Usage

The main way to interact with Jiki from the command line is via `python -m jiki.cli`.

**Run an interactive session:**
```bash
# Uses defaults (model, auto-discovery from servers/calculator_server.py)
python -m jiki.cli run

# Specify model and tool source (e.g., a config file)
python -m jiki.cli run --model <model_name> --tools path/to/tools.json 

# Specify model and auto-discovery source
python -m jiki.cli run --model <model_name> --auto-discover --mcp-script-path path/to/server.py
```

**Process a single query:**
```bash
python -m jiki.cli process "What is 5 * 12?" --tools path/to/tools.json

echo "What is 5 * 12?" | python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py
```

**Manage traces:**
```bash
# Export traces saved during a previous run with tracing enabled
python -m jiki.cli trace export --output traces/my_session.jsonl
```

Use `--help` for more details on commands and options:
```bash
python -m jiki.cli --help
python -m jiki.cli run --help
python -m jiki.cli process --help
```

## Detailed Responses & Tracing

Jiki can return a rich `DetailedResponse` object that includes the assistant's
answer **and** all tool calls / raw traces generated during the turn. Tracing 
is enabled by default (`trace=True` in `create_jiki`).

```python
from jiki import create_jiki

orchestrator = create_jiki(auto_discover_tools=True, mcp_script_path="servers/calculator_server.py")

# Get a structured response with trace metadata
detailed = orchestrator.process_detailed("What is the result of adding 10 and 5?")

print(detailed.result)      # The assistant's final answer
print(detailed.tool_calls)  # List[ToolCall] detailing every tool invocation
print(detailed.traces)      # Raw trace dictionaries for deeper inspection

# Persist traces from the current session
# The run_ui() method and `jiki run` command handle this automatically on exit.
# If using programmatically without run_ui, call this when needed:
# orchestrator.export_traces("interaction_traces/session.jsonl") 
```

## Providing Tools Manually

If you don't use `auto_discover_tools=True`, you can provide tool schemas 
to `create_jiki` via the `tools` argument. This can be a path to a JSON 
file or a list of dictionaries, where each dictionary follows the FastMCP 
tool schema format.

Example `tools.json`:
```json
[
  {
    "tool_name": "add",
    "description": "Add two numbers",
    "arguments": {
        "a": {"type": "integer", "description": "First number", "required": True},
        "b": {"type": "integer", "description": "Second number", "required": True}
    }
  }
  // ... other tools
]
```

Example Python usage:
```python
from jiki import create_jiki

orchestrator = create_jiki(
    tools="path/to/your/tools.json", # Path to config
    mcp_script_path="path/to/your/corresponding/server.py" # Server implementing the tools
)
# Use orchestrator...
```

Server implementation (`servers/calculator_server.py`):
```python
from fastmcp import FastMCP

mcp = FastMCP("Calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# ... other tool definitions ...

if __name__ == "__main__":
    mcp.run()
```

## Requirements

- Python 3.11+
- litellm >= 1.35.0 (or the latest)
- fastmcp >= 2.1.1
- mcp
- tiktoken (optional – enables exact token counting)
