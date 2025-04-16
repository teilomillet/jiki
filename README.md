# Jiki

Jiki is a flexible LLM orchestration framework with built-in tool calling capabilities.

## Overview

Jiki provides a clean interface for building AI assistants that can use tools to solve problems. It orchestrates the interaction between language models and external tools using the MCP (Model Context Protocol).

## Features

- Seamless integration with LiteLLM for support of multiple LLM providers
- Tool calling through FastMCP infrastructure
- Flexible MCP client with multiple transport options (stdio, SSE)
- Structured conversation logging for training data generation
- Simple CLI interface for interactive use
- XML-based tool call format for clear model interaction

## Quick Start

```bash
uv add jiki
```

```python
from jiki import create_jiki

# Create a pre‑configured orchestrator with sensible defaults
orchestrator = create_jiki(
    model="anthropic/claude-3-7-sonnet-latest",
    # Path to a JSON file that describes your tools (see below)
    tools="tools.json",
    mcp_mode="stdio"  # or "sse" to connect to a remote FastMCP server
)

# Process a user query (synchronous helper available)
result = orchestrator.process("What is 2 + 2?")
print(result)
```

## CLI Usage

```bash
uv run examples/simple_multiturn_cli.py --tools tools.json
```

## Detailed Responses & Tracing

Jiki can return a rich `DetailedResponse` object that includes the assistant's
answer **and** all tool calls / raw traces generated during the turn.  This is
useful for debugging, analytics, or offline reinforcement‑learning pipelines.

```python
# Get a structured response with trace metadata
detailed = orchestrator.process_detailed("What is the capital of France?")

print(detailed.result)      # The assistant's final answer
print(detailed.tool_calls)  # List[ToolCall] detailing every tool invocation
print(detailed.traces)      # Raw trace dictionaries for deeper inspection

# Persist traces from the current session
orchestrator.export_traces("interaction_traces/session.jsonl")
```

## Creating Custom Tools

Tools are defined in JSON format and implemented using FastMCP:

```json
{
  "tool_name": "add",
  "description": "Add two numbers",
  "arguments": {
    "a": {"type": "integer", "description": "First number"},
    "b": {"type": "integer", "description": "Second number"}
  }
}
```

Server implementation:

```python
from fastmcp import FastMCP

mcp = FastMCP("Calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

## Requirements

- Python 3.11+
- litellm >= 1.35.0 (or the latest)
- fastmcp >= 2.1.1
- mcp
- tiktoken (optional – enables exact token counting)