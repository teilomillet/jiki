# Jiki

![Jiki Logo](logo.png)

## Overview

Jiki is a flexible LLM orchestration framework designed for building applications that leverage tool calling via the Model Context Protocol (MCP). It integrates seamlessly with LiteLLM for broad LLM provider support and FastMCP for robust tool server communication.

Jiki aims to be easy to start with for simple use cases while providing the depth needed for complex, customized applications.

## Quick Start

Get started quickly with Jiki's interactive CLI or by integrating it into your Python application.

**Installation:** (using [uv](https://github.com/astral-sh/uv) recommended)
```bash
# Using uv
uv pip install jiki
```

**Environment Setup:** Export your LLM provider API key (default is Anthropic):
```bash
export ANTHROPIC_API_KEY=<your_api_key>
# Or OPENAI_API_KEY, etc., depending on the model used
```

**Run Interactive CLI:**
The simplest way to start is using the built-in CLI with automatic tool discovery (requires a compatible MCP server, like the example `servers/calculator_server.py`).
```bash
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```
Exit with Ctrl-D, Ctrl-C, or `exit`.

**Programmatic Usage (Simple):**
```python
from jiki import Jiki

# Create an orchestrator using auto-discovery
# Assumes servers/calculator_server.py is accessible
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_mode="stdio",
    mcp_script_path="servers/calculator_server.py"
)

# Get a simple response
result = orchestrator.process("What is 2 + 2?")
print(result) # Output: 4

# Or run the interactive CLI programmatically
# orchestrator.run_ui()
```

## Examples

Explore the `examples/` directory to see Jiki's capabilities in action:

-   **`simple_multiturn_cli.py`**: Demonstrates launching the interactive CLI programmatically with just a few lines, relying on automatic tool discovery for immediate use.
-   **`custom_transport_example.py`**: Shows how to connect to a tool server using a different protocol (SSE over HTTP), interact directly with the MCP client to list resources, and execute tool calls (RPC) without involving the LLM.
-   **`detailed_and_roots_example.py`**: Illustrates retrieving a `DetailedResponse` containing the final result *plus* structured tool call data and raw interaction traces using `process_detailed()`. Also shows interaction with MCP "roots".
-   **`advanced_examples.py`**: Highlights several advanced techniques:
    -   Loading tool definitions manually from a JSON file instead of auto-discovery.
    *   Customizing LLM generation parameters (like temperature, max tokens) using `SamplerConfig`.
    *   Implementing persistent conversation state using a `ConversationRootManager` for snapshot and resume functionality across sessions.

Run these examples (uv recommended):
```bash
uv run examples/simple_multiturn_cli.py
uv run examples/custom_transport_example.py
uv run examples/detailed_and_roots_example.py
uv run examples/advanced_examples.py
```

## Key Capabilities

Jiki offers a range of features, progressing from simple defaults to fine-grained control:

-   **Multiple LLM Backends:** Leverages LiteLLM for compatibility with OpenAI, Anthropic, Gemini, Mistral, Cohere, Azure, Bedrock, and more.
-   **Flexible Tool Integration:**
    -   `auto_discover_tools=True`: Simple start by automatically fetching tool schemas from an MCP server.
    *   `tools="path/to/tools.json"` or `tools=[{...}]`: Provide tool schemas manually for explicit control.
-   **Varied MCP Transport:** Connect to tool servers via `stdio` (default, for local scripts) or `sse` (for servers exposing an HTTP endpoint). See `custom_transport_example.py`.
-   **Detailed Interaction Data:**
    -   `orchestrator.process()`: Returns the final string result.
    *   `orchestrator.process_detailed()`: Returns a `DetailedResponse` object containing `.result`, `.tool_calls` (structured list), and `.traces` (raw logs). Essential for debugging and complex logic. See `detailed_and_roots_example.py`.
-   **Tracing & Logging:** Built-in tracing (`trace=True`) captures interactions, exportable via `orchestrator.export_traces()` or automatically by `run_ui()` and the main CLI.
-   **LLM Sampling Configuration:** Pass a `SamplerConfig` object during `Jiki` initialization to control temperature, top_p, max_tokens, etc. See `advanced_examples.py`.
-   **State Management:** Implement the `IConversationRootManager` interface to manage conversation state, enabling snapshot and resume capabilities. See `advanced_examples.py`.
-   **Direct MCP Client Access:** Use `orchestrator.mcp_client` for lower-level interactions with the tool server (listing resources, direct RPC calls). See `custom_transport_example.py`.
-   **Command-Line Interface:** `python -m jiki.cli` provides commands for `run` (interactive), `process` (single query), and `trace` management. Use `--help` for details.

## Contributing

Contributions are welcome! (TODO: Add contributing guide link)

## License

Jiki is licensed under the Apache 2.0 License.
