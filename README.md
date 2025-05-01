# Jiki

![Jiki Logo](logo.png)

Jiki is a Python framework designed to bridge the gap between Large Language Models (LLMs) and external capabilities. It allows LLMs to reliably interact with tools and access data resources by connecting them to tool servers using the Model Context Protocol (MCP). At its core, Jiki uses an **Orchestrator** to manage the conversation flow and an **MCP Client** to handle the communication with tool servers, enabling powerful AI applications with just a few lines of code.

## Quick Start

Get started quickly with these steps.

### Installation

Install the `jiki` package using your preferred package manager:

```bash
# Using pip
pip install jiki

# Or using uv (recommended for faster installation)
uv add jiki
```

### Set Up API Key

Jiki uses [LiteLLM](https://litellm.ai/) internally, allowing it to work with a wide range of LLM providers (OpenAI, Anthropic, Gemini, etc.). You need to set the appropriate environment variable for your chosen provider.

```bash
# Example for Anthropic Claude (often used as default)
export ANTHROPIC_API_KEY=your_key_here

# Example for OpenAI
# export OPENAI_API_KEY=your_key_here
```

### Run Interactive Chat

The Jiki CLI provides an interactive way to chat with an LLM augmented by tools.

```bash
# Start interactive chat with the calculator example
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```

*   `--auto-discover`: Tells Jiki's MCP Client to ask the server (specified by the script path) which tools it offers.
*   `--mcp-script-path`: Tells the MCP Client to start the specified Python script (`calculator_server.py`) and communicate with it using standard input/output (stdio).

Try asking: "What is 25 * 16?" or "Can you calculate 128 / 4?" The orchestrator will guide the LLM to use the appropriate tool via the client.

### Single Query Mode

Process a single query directly from the command line.

```bash
# Process a single query using the calculator
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py "What is 42 + 17?"
```
This works similarly to the interactive mode but exits after processing the one query.

### Simple Python Example

Use Jiki programmatically in your Python scripts.

```python
from jiki import Jiki

# The Jiki() factory function simplifies setup. It creates and configures
# the core JikiOrchestrator, the JikiClient (for tool communication),
# the LLM model wrapper, and other necessary components based on the arguments.
print("Initializing Jiki...")
orchestrator = Jiki(
    auto_discover_tools=True, # Ask the server for available tools
    mcp_script_path="servers/calculator_server.py" # Connect via stdio
)
print("Initialization complete.")

# The orchestrator's process() method handles the full interaction:
# sending the prompt, managing tool calls with the client, and returning the final response.
print("Processing query...")
result = orchestrator.process("What is 15 * 8?")
print(f"Result: {result}") 
```

## Common Use Cases

The following examples illustrate common ways to configure and use Jiki, often by changing arguments to the `Jiki()` factory or the CLI to modify how the orchestrator, client, or model behave.

| Use Case                   | Example Command                                                                                                    | Python Example                                                                                  | Explanation                                                                   |
|----------------------------|--------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| **Interactive Chat**       | `python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py`                            | `orchestrator = Jiki(...)` followed by a loop calling `orchestrator.process(input())`         | Multi-turn conversation using a specified tool server via stdio.            |
| **Single Query**           | `python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py "What is 5 + 10?"`      | `result = orchestrator.process("What is 5 + 10?")`                                          | Get a single response for one input.                                          |
| **Detailed Response**      | `python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py --detailed "What is 7*8?"` | `detailed = orchestrator.process_detailed("What is 7 * 8?")`                                | Get structured output including which tools were called (`detailed.tool_calls`). |
| **Custom Tools**           | `python -m jiki.cli run --tools tools.json --mcp-script-path servers/calculator_server.py`                         | `orchestrator = Jiki(tools="tools.json", mcp_script_path="...")`                           | Provide tool definitions directly instead of using auto-discovery.            |
| **Custom LLM**             | `python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py --model openai/gpt-4o`     | `orchestrator = Jiki(model="openai/gpt-4o", auto_discover_tools=True, ...)`                  | Specify a different LLM via LiteLLM model strings.                             |
| **HTTP Transport (SSE)**   | `python -m jiki.cli run --auto-discover --mcp-mode sse --mcp-url http://localhost:8000`                            | `orchestrator = Jiki(auto_discover_tools=True, mcp_mode="sse", mcp_url="http://localhost:8000")` | Connect to a running MCP server over the network using Server-Sent Events. |

## Troubleshooting

If you encounter issues, check these common solutions:

| Issue                        | Solution                                                                                                                                 | Where to Look for More Info                                                                 |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Missing API Key**          | Ensure the correct environment variable (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) is set for your chosen LLM provider.                  | [LiteLLM Documentation](https://docs.litellm.ai/docs/providers)                             |
| **Tool Discovery Fails**     | Verify the `--mcp-script-path` is correct, the script exists, and is executable. Check server logs if running separately.                | [Getting Started Guide](docs/getting_started.md), Your MCP server's documentation           |
| **Transport Error (SSE/HTTP)**| Make sure the MCP server is running at the specified `--mcp-url` and that the `--mcp-mode` (e.g., `sse`) matches the server's setup. | [Reference - MCP Client Transports](docs/reference.md#mcp-client-transports)                |
| **ImportError**              | Ensure all dependencies are installed. Sometimes specific features require extras: `pip install "jiki[all]"`                           | Jiki `pyproject.toml` file                                                                  |
| **Calculator Example Missing** | The example server (`servers/calculator_server.py`) is part of the source repository. Clone the repo: `git clone https://github.com/your-org/jiki.git` | Jiki GitHub Repository                                                                      |
| **Understanding Flow**       | Need to understand how components interact (Orchestrator, Client, LLM)?                                                                    | [Architecture Overview](docs/architecture_overview.md), [Reference Guide](docs/reference.md) |

## Examples in Action

Explore complete, runnable examples in the `examples/` directory of the repository to see various features in practice:

-   **`simple_multiturn_cli.py`**: Demonstrates a basic interactive chat loop using auto-discovery and the calculator server via stdio.
-   **`custom_transport_example.py`**: Shows how to connect to an MCP server running over HTTP (SSE).
-   **`detailed_and_roots_example.py`**: Focuses on retrieving structured `DetailedResponse` objects to inspect tool calls and potentially interaction traces.
-   **`advanced_examples.py`**: Illustrates more advanced configurations like custom LLM sampling parameters (`SamplerConfig`) and managing conversation state persistence using `snapshot()` and `resume()`.

## Next Steps

To effectively use Jiki, consider your goal and explore the documentation accordingly:

1.  **Practical Integration:** If you want to quickly integrate tools into your application, start with the [Getting Started Guide](docs/getting_started.md) and the calculator examples. Adapt them by creating your own tool server (perhaps using [FastMCP](https://gofastmcp.com/)) and modifying the `mcp_script_path` or `mcp_url`.

2.  **Understanding the System:** To grasp how Jiki manages interactions, handles tool calls, and communicates with servers, read the [Architecture Overview](docs/architecture_overview.md). This explains the roles of the Orchestrator, MCP Client, Transports, and Prompt Builders.

3.  **Configuration & Customization:** For fine-grained control over LLM behavior (sampling), prompt structure, tool definitions, or communication methods, consult the [API Reference](docs/reference.md). It details the `Jiki()` factory parameters, core classes like `JikiOrchestrator` and `JikiClient`, configuration objects (`SamplerConfig`), and utility functions.

4.  **Advanced Use & Extension:** If you need to implement custom communication clients, complex state management, or unique prompt strategies, study the [Core Interfaces](docs/core_interfaces.md) (`IMCPClient`, `IPromptBuilder`, `IConversationRootManager`) documented in the reference guide and core interfaces document.

## Key Capabilities

Jiki offers a robust set of features for building tool-augmented LLM applications. It supports multiple LLM backends through LiteLLM (including OpenAI, Anthropic, Gemini, Mistral, and more) and provides flexible tool integration via auto-discovery or manual definition using the Model Context Protocol. Communication with tool servers is handled transparently, supporting both local scripts (stdio) and network services (HTTP/SSE). For development and analysis, Jiki provides detailed structured responses containing tool call information and optional interaction tracing. It also includes capabilities for managing conversation state persistence and a full command-line interface for quick interaction and testing.

## Contributing

Contributions are welcome! Please refer to the `CONTRIBUTING.md` guide (TODO: Create and link contributing guide).

## License

Jiki is licensed under the Apache 2.0 License. See the `LICENSE` file for details.
