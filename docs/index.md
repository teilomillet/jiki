# Jiki: LLM Tool Orchestration Framework

Jiki connects large language models to tool servers using the Model Context Protocol (MCP), enabling powerful AI applications with just a few lines of code.

## What Can You Do With Jiki?

- **Build AI Assistants** that use specialized tools to solve complex tasks
- **Connect to Any LLM Provider** through LiteLLM (OpenAI, Anthropic, Google, etc.)
- **Create Custom Tools** that Jiki can discover and invoke automatically
- **Trace and Debug** AI interactions with comprehensive logging

## Quick Start

```python
from jiki import Jiki

# Create an orchestrator with calculator tools
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Process a query
result = orchestrator.process("What is 15 * 8?")
print(result)  # Output: "15 * 8 = 120"
```

## Documentation

### Getting Started
- 🚀 [Getting Started Guide](getting_started.md) - Step-by-step installation and first run
- 💻 [CLI Reference](cli_reference.md) - Command-line interface documentation
- 📝 [Code Examples](code_examples.md) - Ready-to-run example scripts

### Concepts & Architecture
- 🏛️ [Architecture Overview](architecture_overview.md) - How Jiki works
- 🧩 [Core Interfaces](core_interfaces.md) - Main protocols and extension points
- 🔧 [Orchestrator](orchestrator_interfaces.md) - The main engine
- 🤝 [MCP Client](mcp_client.md) - Tool discovery and invocation
- 📊 [Logging & Tracing](logging.md) - Recording interactions

### Reference
- 📚 [API Reference](reference.md) - Detailed API documentation

## Key Features

| Feature | Description |
|---------|-------------|
| **Tool Discovery** | Automatically detect available tools from an MCP server |
| **Multiple Transport Options** | Connect via stdio (subprocess) or HTTP (SSE) |
| **Detailed Responses** | Get structured data about tool calls and execution traces |
| **Conversation State** | Save and resume conversations between sessions |
| **LLM Flexibility** | Works with all major LLM providers via LiteLLM |

## Next Steps

After getting familiar with the basics:

1. Follow the [Getting Started Guide](getting_started.md) to install and run your first example
2. Try the [CLI commands](cli_reference.md) for quick interactive sessions
3. Explore the [code examples](code_examples.md) for more advanced use cases 