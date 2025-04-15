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
from jiki import create_orchestrator

# Create a preconfigured orchestrator with sensible defaults
components = create_orchestrator(
    model_name="anthropic/claude-3-7-sonnet-latest",
    tools_config_path="tools.json",
    mcp_mode="stdio"
)

# Get the orchestrator instance
orchestrator = components["orchestrator"]

# Process a user query
import asyncio
result = asyncio.run(orchestrator.process_user_input("What is 2+2?"))
print(result)
```

## CLI Usage

```bash
uv run main.py
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
- litellm
- fastmcp >= 2.1.1
- mcp