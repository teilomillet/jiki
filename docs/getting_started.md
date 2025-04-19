# Getting Started with Jiki

Welcome to Jiki! This guide will walk you through the basics of using the Jiki orchestration framework.

Jiki is designed to be **easy to learn** for common use cases, yet **powerful and extensible** (hard to master) for advanced scenarios.

## 1. The Easiest Way: `Jiki()`

The simplest way to get started is using the `Jiki` factory function. It sets up a `JikiOrchestrator` instance with sensible defaults, including tool discovery and interaction tracing.

**Prerequisites:**

*   Install Jiki: `pip install jiki` (or `uv pip install jiki`)
*   Set up necessary API keys (e.g., `export ANTHROPIC_API_KEY=your_key`)
*   Have a compatible MCP tool server running or accessible (we'll use the example calculator server).

**Example:**

Let's assume you have the example `calculator_server.py` from the Jiki repository.

```python
# file: run_calculator.py
# Import the main factory function
from jiki import Jiki 

# Create a pre-configured orchestrator using auto-discovery
# Assumes servers/calculator_server.py is in the current directory or path
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_mode="stdio",
    mcp_script_path="servers/calculator_server.py"
)

# Option 1: Launch the built-in interactive CLI
print("Starting interactive Jiki session...")
orchestrator.run_ui() 

# Option 2: Process a single query programmatically
# print("\nProcessing single query...")
# result = orchestrator.process("What is 12 * 11?")
# print(f"Query: What is 12 * 11?\nResult: {result}")

# Traces are automatically saved on exit when using run_ui()
# or can be saved manually:
# orchestrator.export_traces("calculator_session.jsonl") 
```

Run this script (`python run_calculator.py`), and you'll get an interactive prompt where you can ask the AI questions that might require using the calculator tool (e.g., "What is 256 + 128?").

## 2. Core Concepts: Orchestrator and Client

Behind the scenes, `Jiki()` configures:

*   **`JikiOrchestrator`**: The main engine that manages the conversation flow, prompts the LLM, handles tool calls, and maintains context.
*   **`JikiClient`**: The default MCP client implementation used to communicate with the tool server (`calculator_server.py` in this case) for discovering and executing tools. It uses the `fastmcp` library.

For many use cases, you might only ever need `Jiki()`.

## 3. Easy to Learn, Hard to Master

Jiki's philosophy centers around this principle:

*   **Easy to Learn:** The `Jiki()` factory provides a high-level interface that hides most of the complexity. You can get a capable tool-using AI assistant running in just a few lines of code without needing to understand the underlying MCP protocol or prompt engineering details. The default `JikiClient` handles standard communication effectively.

*   **Hard to Master (Powerful & Extensible):** When you need more control, Jiki's power emerges. The `JikiOrchestrator` relies on well-defined interfaces (protocols) for its core components. This means you can:
    *   **Customize Prompts:** Implement your own `IPromptBuilder` to change how tools and context are presented to the LLM.
    *   **Implement Custom Clients:** Subclass `BaseMCPClient` (the parent of `JikiClient`) to use different communication transports or add custom logic around tool calls.
    *   **Integrate Different Models:** While `LiteLLMModel` is the default, the orchestrator interacts with the model via a simple interface.
    *   **Manage State Differently:** Plug in custom root or resource managers.

    This extensibility allows you to tailor Jiki precisely to your needs, integrate it into complex applications, or experiment with novel AI interaction patterns.

## Next Steps

*   Explore the **[Core Interfaces](core_interfaces.md)** to understand the protocols that enable Jiki's extensibility.
*   Dive into the **[MCP Client Overview](mcp_client.md)** to learn more about `JikiClient` and `BaseMCPClient`.
*   Check out the **[Orchestrator Interfaces](orchestrator_interfaces.md)** for more details on the orchestrator itself. 