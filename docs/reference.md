# Jiki API Reference

This API reference documents the key components of Jiki's architecture. It's organized by functional areas to help you understand how the different pieces fit together.

## Core Components

This section covers the central components of Jiki that form the backbone of the orchestration framework.

### Factory Function

The factory function is the primary entry point for most users. It simplifies creating a properly configured orchestrator with sensible defaults.

#### The Jiki() Factory Pattern

The `Jiki()` function follows the factory pattern, creating and configuring all necessary components behind the scenes:

1.  **Initialization Flow**:
    *   Sets up a `TraceLogger` if tracing is enabled
    *   Configures the appropriate MCP transport (stdio or SSE)
    *   Creates a `JikiClient` instance for tool/resource management
    *   Discovers or loads tool configurations
    *   Initializes a language model wrapper (via LiteLLM)
    *   Creates and returns a fully configured `JikiOrchestrator`



2.  **Usage Examples**:

```python
# Basic usage with auto-discovery
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Advanced configuration
orchestrator = Jiki(
    model="openai/gpt-4o",
    tools="path/to/tools.json",
    mcp_mode="sse",
    mcp_url="http://localhost:8000",
    trace=True,
    trace_dir="custom_traces",
    prompt_builder=MyCustomPromptBuilder(),
    sampler_config=SamplerConfig(temperature=0.7)
)
```

::: jiki.Jiki
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

### Orchestrator

#### JikiOrchestrator Architecture and Functionality

The `JikiOrchestrator` is the central component responsible for coordinating the entire interaction lifecycle within Jiki. It manages communication between the language model (LLM), the tool execution layer (MCP client), and the conversation state.

Key responsibilities include component management, orchestrating the conversation flow, and handling state persistence. The orchestrator wraps the selected language model and holds references to the MCP client for tool operations, a `PromptBuilder` for formatting LLM inputs, and a `TraceLogger` for debugging. It manages the tool configurations and their corresponding schemas.

During a conversation, the orchestrator constructs the initial system prompt containing relevant tool and resource information. It processes user inputs, streams responses from the LLM, and actively monitors the output for tool call requests. When a tool call is detected, the orchestrator intercepts it, validates the request against the tool's schema, and executes it using the MCP client. The results from the tool call are then formatted and injected back into the conversation history, which is maintained in a format compatible with LiteLLM/OpenAI APIs. To manage context window limitations, the orchestrator also handles context trimming.

For state persistence, the `JikiOrchestrator` supports snapshotting the current conversation state, allowing it to be resumed later. It also keeps track of tool calls and execution traces within the current interaction turn. Core functionality is exposed through methods like `process()` for simple interactions and `process_detailed()` for retrieving structured results including tool call information.

##### Usage Example

```python
# Process a simple query
result = orchestrator.process("What is 2 + 2?")
print(result)

# Get detailed response with tool calls
detailed = orchestrator.process_detailed("What is the square root of 144?")
print(f"Result: {detailed.result}")
print(f"Tool calls: {detailed.tool_calls}")

# Save conversation state
state = orchestrator.snapshot()
# ... later ...
orchestrator.resume(state)
```

::: jiki.orchestrator.JikiOrchestrator
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

### Detailed Response

#### Working with Detailed Responses

The `DetailedResponse` and `ToolCall` classes provide structured access to the results of an interaction, particularly when tools are involved. Instead of just getting the final string output, you can inspect the sequence of operations.

The `DetailedResponse` object contains the overall `result` (the final text response from the LLM), a list of `tool_calls` made during the processing, and potentially the raw interaction `traces` if tracing was enabled. Each item in the `tool_calls` list is a `ToolCall` object.

A `ToolCall` object represents a single tool invocation and holds the `tool_name` that was called, the `arguments` dictionary passed to it, and the `result` returned by the tool execution.

This detailed structure is useful for various purposes, such as debugging (by analyzing which tools were used and with what parameters), extracting specific structured data returned by tools, building user interfaces that visualize the tool execution flow, or creating automated test cases for tool integrations.

##### Usage Example:

```python
detailed = orchestrator.process_detailed("What is 15 * 8?")

# Access the string result
print(f"Final answer: {detailed.result}")

# Examine tool calls
for call in detailed.tool_calls:
    print(f"Tool: {call.tool_name}")
    print(f"Arguments: {call.arguments}")
    print(f"Result: {call.result}")
```

::: jiki.models.response.DetailedResponse
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

::: jiki.models.response.ToolCall
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

## MCP Client Components

These components handle communication with Model Context Protocol (MCP) tool servers.

### Jiki Client

#### JikiClient Architecture and Role

The `JikiClient` acts as the primary interface between the Jiki orchestrator and MCP-compatible tool servers. It implements the full Model Context Protocol (MCP) to manage the lifecycle of communication and interaction with external tools and resources.

Its core responsibilities include managing the underlying transport layer, handling various tool and resource operations, managing conversation state via roots, and facilitating debugging through interaction tracing. The client uses `fastmcp.Client` internally to establish connections, supporting different transport mechanisms like stdio for local scripts and SSE or WebSockets for network communication, managing the connection lifecycle within asynchronous contexts.

For tool interactions, the `JikiClient` discovers available tools (`discover_tools()`) and executes them with specified arguments (`execute_tool_call()`), processing and formatting the results for the orchestrator. It similarly handles resource discovery (`list_resources()`) and retrieval (`read_resource()`).

In stateful conversations, the client manages root URIs (`list_roots()`, `send_roots_list_changed()`) to synchronize context with the MCP server. For debugging, it captures all MCP messages, including server-side logs, making these traces available via `get_interaction_traces()`. The client also maintains backward compatibility through the `EnhancedMCPClient` layer, handling deprecations gracefully.

While typically instantiated by the main `Jiki()` factory function, the `JikiClient` can be used directly for more specialized scenarios.

##### Usage Example:

```python
# Creating a client directly (usually done by Jiki() factory)
client = JikiClient("servers/calculator_server.py")

# Initialize and discover tools
await client.initialize()
tools = await client.discover_tools()

# Execute a tool call
result = await client.execute_tool_call("add", {"a": 5, "b": 3})
print(result)  # "8"

# Get traces for debugging
traces = client.get_interaction_traces()
```

::: jiki.mcp_client.JikiClient
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

### Client Interfaces

#### Purpose and Structure

The client interfaces, `IToolClient` and `IMCPClient`, define the essential contracts for how the Jiki orchestrator interacts with tool execution backends. `IToolClient` represents the base interface, requiring methods for fundamental tool operations like discovery and execution. `IMCPClient` extends this base contract, adding methods specific to the Model Context Protocol (MCP), such as resource listing/reading and roots management for conversation state.

These interfaces serve as crucial extension points, allowing developers to create custom client implementations for specialized scenarios. This could include building mock clients for testing purposes, creating adapters for integrating with non-MCP tool systems, or developing clients with unique transport or communication logic. All interface methods are defined as asynchronous to ensure non-blocking performance during operations like tool discovery and execution.

##### Usage Example:

```python
# Implementing a custom client
class MyCustomClient(IMCPClient):
    async def initialize(self) -> None:
        # Custom initialization logic
        ...

    async def discover_tools(self) -> List[Dict[str, Any]]:
        # Custom tool discovery implementation
        ...

    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        # Custom tool execution implementation
        ...

    # Implement other required methods...
```

::: jiki.tool_client.IMCPClient
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      show_bases: true

::: jiki.tool_client.IToolClient
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      show_bases: true

## Configuration and Customization

These components allow customizing Jiki's behavior for advanced use cases.

### Sampling Configuration

::: jiki.sampling.SamplerConfig
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.sampling.ISamplerConfig
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3
      show_bases: true

SamplerConfig controls how the LLM generates responses by adjusting parameters like temperature and top_p.

### Prompt Building

#### Prompt Builder Pattern and Customization

Prompt builders are essential components that control how Jiki structures and formats the input sent to the language model (LLM). They are responsible for assembling system instructions, tool schemas, resource information, and conversation history into a coherent prompt.

The core contract is defined by the `IPromptBuilder` interface, which specifies methods for generating the tool schema block (`create_available_tools_block`), the resource information block (`create_available_resources_block`), and constructing the complete initial system prompt (`build_initial_prompt`).

Jiki provides a `DefaultPromptBuilder` implementation that adheres to the Model Context Protocol (MCP) specifications, ensuring standard, compatible formatting. However, the prompt builder pattern allows for significant customization. Developers can create their own implementations of `IPromptBuilder` to tailor the prompts for specific needs, such as modifying the system instructions for different application domains, changing how tool schemas are presented to optimize for particular LLMs, or injecting custom contextual information or few-shot examples into the prompt.

##### Usage Example:

```python
# Custom prompt builder
class MyPromptBuilder(IPromptBuilder):
    def create_available_tools_block(self, tools_config):
        # Custom tool block formatting
        ...

    def create_available_resources_block(self, resources_config):
        # Custom resources block formatting
        ...

    def build_initial_prompt(self, user_input, tools_config, resources_config=None):
        # Custom prompt assembly with domain-specific instructions
        ...

# Use with orchestrator
orchestrator = Jiki(
    prompt_builder=MyPromptBuilder(),
    # other parameters...
)
```

::: jiki.prompts.prompt_builder.IPromptBuilder
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3
      show_bases: true

::: jiki.prompts.prompt_builder.DefaultPromptBuilder
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

### Roots and Conversation State Management

The Model Context Protocol (MCP) includes the concept of "Roots", which allows a client application (like Jiki) to inform the MCP server about its current contextual boundaries or accessible resources. This might include accessible file paths, user identifiers, or database schemas relevant to the ongoing interaction. The server can leverage this information to tailor its behavior or the actions of its tools.

Managing these roots is particularly important for enabling persistent, stateful conversations, especially across different sessions. Jiki abstracts the handling of this state through the `IConversationRootManager` interface. Implementations of this interface are responsible for determining the relevant roots and other contextual data for a conversation, providing methods to `snapshot` this state into a serializable format, and allowing the conversation context (including roots) to be restored later using `resume`. This mechanism is key to enabling Jiki applications to maintain continuity in long-running or multi-session interactions.

::: jiki.roots.conversation_root_manager.IConversationRootManager
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4 # Adjusted heading level for better hierarchy
      show_bases: true

## Tools and Resources

These components handle the definition and management of executable actions (Tools) and informational assets (Resources) available during LLM interactions, following the Model Context Protocol (MCP) concepts.

### Tools: Enabling Actions

Tools are a core concept in MCP, representing executable functions or capabilities exposed by a server. They empower the LLM, guided by the orchestrator, to interact with external systems, perform calculations, fetch dynamic data, or execute specific actions. Each tool is defined with a unique name, a description (to guide the LLM on its usage), and an input schema (typically JSON Schema) specifying the parameters the tool expects. This allows the orchestrator to validate requests and the LLM to correctly format its tool calls.

In Jiki, the `jiki.tools.tool.Tool` class encapsulates this definition. Tool configurations are often loaded from external sources like JSON files using helper functions.

::: jiki.tools.tool.Tool
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4 # Adjusted heading level for better hierarchy

::: jiki.tools.config.load_tools_config
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4 # Adjusted heading level for better hierarchy

### Resources: Providing Context

Resources, distinct from tools, represent data assets or contextual information made available to the LLM. They are typically passive information sources rather than executable actions. Examples include relevant documentation snippets, user profiles, project files, or templates that can inform the LLM's responses or actions. Resources are generally identified by a URI, and their content can be retrieved by the client/orchestrator as needed during the conversation.

In Jiki, the management of these resources (discovery, retrieval) is abstracted through the `jiki.resources.resource_manager.IResourceManager` interface. Implementations of this interface handle how resources are located and their content fetched.

::: jiki.resources.resource_manager.IResourceManager
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4 # Adjusted heading level for better hierarchy
      show_bases: true

## Logging and Debugging

Jiki provides mechanisms for detailed tracing of interactions and basic debugging output, primarily through the `TraceLogger`.

### Structured Interaction Tracing

The main component for logging is the `jiki.logging.TraceLogger`. Its primary purpose is to record detailed, structured information about conversations, including prompts, LLM responses, tool calls, and results. Crucially, it aims to capture this information in a format consistent with the Model Context Protocol (MCP) interaction trace standards. This structured format makes the logs suitable for detailed analysis, debugging complex interaction flows, and potentially generating training data for downstream tasks like reinforcement learning.

The `TraceLogger` works by accumulating *complete interaction traces*. Each trace typically represents a full turn or significant segment of the conversation. The `log_complete_trace` method is used to record these complete traces, often incorporating intermediate events logged via `log_event`. These accumulated traces are stored in memory and can be persisted explicitly by calling the `save_all_traces` method, which writes them to a JSON or JSONL file.

### Basic Debug Output

For simpler, less structured debugging needs, the `TraceLogger` also provides a `debug` method. This method currently offers basic functionality, simply printing the provided debug message directly to the standard error stream (`stderr`). This is distinct from the structured tracing mechanism.

::: jiki.logging.TraceLogger
    options:
      show_root_heading: false # Keep focus on the manual explanation above
      show_source: false
      heading_level: 4 # Subordinated under the main section heading

## Utility Functions

Helpful utility functions for working with Jiki.

::: jiki.utils.cleaning.clean_output
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.utils.context.trim_context
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.utils.token.count_tokens
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

## Complete Module Reference

This reference document has detailed the core components, interfaces, and configuration options available in the Jiki framework. For specifics on individual classes and functions, please refer to the relevant sections above. For a comprehensive view of all modules and their contents, exploring the source code directly is recommended. 