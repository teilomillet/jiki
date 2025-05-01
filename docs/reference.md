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

Key responsibilities include component management, orchestrating the conversation flow, and handling state persistence. The orchestrator wraps the selected language model (`model`) and holds references to the MCP client (`mcp_client`) for tool operations, a `PromptBuilder` for formatting LLM inputs, and an optional `TraceLogger` for debugging. It manages the tool configurations (`tools_config`) and builds an internal map (`_tools_map`) for efficient validation.

Internally, the orchestrator maintains the conversation history as a list of messages (`_messages`). When processing user input (`process_user_input`), it distinguishes between the first turn (where it may fetch resources via `mcp_client.list_resources()` and builds an initial system prompt using the `prompt_builder`) and subsequent turns (where it simply appends the user message). Before sending messages to the LLM, it uses the `jiki.utils.context.trim_context` utility to ensure the history fits within the model's context window, relying on `jiki.utils.token.count_tokens` for measurement. The core LLM interaction, including streaming responses and intercepting tool calls, is delegated to the `jiki.utils.streaming.generate_and_intercept` utility function. This function uses callbacks (`_handle_tool_call`) provided by the orchestrator to manage tool execution.

The `_handle_tool_call` method is responsible for parsing the LLM's tool call request (using `jiki.utils.parsing.extract_tool_call` and `jiki.utils.tool.parse_tool_call_content`), validating it against the tool schema map (`_tools_map` via `jiki.utils.tool.validate_tool_call`), executing the validated call via the `mcp_client.execute_tool_call`, and formatting the result (as `<mcp_tool_result>...`) to be injected back into the conversation history. It also records successful calls in `_last_tool_calls`.

For state persistence, the `JikiOrchestrator` itself implements `snapshot()` and `resume()` methods, allowing the current conversation state (primarily `_messages` and `_last_tool_calls`) to be saved and restored externally. It also accepts an optional `conversation_root_manager` during initialization for custom state handling (see Roots and Conversation State Management section). Core functionality is exposed through methods like `process()` for simple interactions and `process_detailed()` for retrieving structured results including tool call information.

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

### MCP Client Transports

The connection between the `JikiClient` and the MCP server is managed by a **Transport** layer. This layer handles the specifics of how communication occurs, whether it's launching a local script or connecting to a network service. Jiki leverages the transport system provided by the underlying `fastmcp` library.

While `fastmcp` supports various transport types [https://gofastmcp.com/clients/transports], the `Jiki()` factory function provides convenient configuration for the most common ones used with Jiki:

*   **Stdio (`PythonStdioTransport`)**:
    *   **Use Case:** Running a Python-based MCP server as a local subprocess. Communication happens via the subprocess's standard input and standard output.
    *   **Configuration:** Specify the path to the server script using the `mcp_script_path` argument in `Jiki()`. This is the default if `mcp_mode` is not set or set to `'stdio'`.
    *   **Details:** Jiki uses `fastmcp.client.transports.PythonStdioTransport` for this, as seen in `jiki.transports.factory.py`. Ideal for development or simple self-contained tools.

*   **SSE (`SSETransport`)**:
    *   **Use Case:** Connecting to a persistent MCP server running over a network via HTTP/S using Server-Sent Events.
    *   **Configuration:** Set `mcp_mode="sse"` and provide the server's URL via the `mcp_url` argument in `Jiki()` (defaults to `http://localhost:6277/mcp` if not provided, according to `jiki.transports.factory.py`).
    *   **Details:** Uses `fastmcp.client.transports.SSETransport`. Suitable for connecting to deployed MCP services. See [https://gofastmcp.com/clients/transports#sse-server-sent-events](https://gofastmcp.com/clients/transports#sse-server-sent-events) for more on SSE transport.

**Other FastMCP Transports:**

The underlying `fastmcp.Client` used by `JikiClient` can also potentially work with other transports like WebSockets (`WSTransport`) or connect directly to in-process servers (`FastMCPTransport`) for testing, though these might require more direct configuration of the `JikiClient` rather than using the main `Jiki()` factory function's simpler parameters. Refer to the FastMCP documentation [https://gofastmcp.com/clients/transports] for the full list and capabilities.

### Client Interfaces

#### Purpose and Structure

The client interfaces, `IToolClient` and `IMCPClient` (defined in `jiki.tool_client`), establish the essential contracts for how the Jiki orchestrator interacts with tool execution backends.

*   `IToolClient`: Represents the base interface, requiring methods for fundamental tool operations like discovery (`discover_tools`) and execution (`execute_tool_call`).
*   `IMCPClient`: Extends `IToolClient`, adding methods specific to the full Model Context Protocol (MCP), including resource listing/reading (via `IResourceManager` inheritance) and roots management (`list_roots`, `send_roots_list_changed`). This is the interface expected by the `JikiOrchestrator`.

**Standard Usage vs. Custom Implementations:**

For most use cases involving standard MCP servers, the built-in `jiki.mcp_client.JikiClient` is the recommended implementation. It leverages the robust `fastmcp.Client` library [https://gofastmcp.com/clients/client] and handles various transports (Stdio, SSE, WebSockets) and the MCP protocol details automatically. Customization for standard clients typically involves configuring the `transport_source` and `roots` when initializing `JikiClient` (often done indirectly via `Jiki()` factory parameters).

**Why Build a Custom Client?**

Implementing `IMCPClient` (or `IToolClient` for basic needs) yourself is an **advanced** task, typically only necessary in specific situations where `JikiClient` is unsuitable, such as:

*   **Integrating Non-MCP Systems:** Connecting Jiki to a backend that uses a completely different communication protocol (e.g., a custom REST API, gRPC service) and cannot be exposed via an MCP server.
*   **Specialized Communication Logic:** Requiring highly custom logic for connection management, authentication, error handling, retries, or caching that goes beyond the capabilities or configuration options of `fastmcp.Client`.
*   **Mocking for Testing:** Creating mock or stub clients for unit or integration testing the orchestrator without needing a live backend.
*   **Performance-Critical Scenarios:** In rare cases where the overhead of `fastmcp.Client` might be prohibitive, requiring a bare-metal implementation (though `fastmcp` itself is designed to be efficient).

**How to Build a Custom Client (Conceptual Steps):**

1.  **Define a Class:** Create a Python class that explicitly inherits from `jiki.tool_client.IMCPClient` (or `IToolClient`).
2.  **Implement Methods:** Implement *all* the `async` methods defined by the chosen interface(s). This involves writing the code to handle the underlying communication (e.g., making HTTP requests, calling library functions, interacting with a mock state).
3.  **Handle State:** Manage any necessary connection state, authentication tokens, etc., within your class instance.
4.  **Return Correct Types:** Ensure each method returns data in the format expected by the interface definition (e.g., `discover_tools` returns a list of dictionaries representing tool schemas).
5.  **Integrate:** Pass an instance of your custom client class to the `JikiOrchestrator` during its initialization.

##### Example Skeleton (Conceptual)

```python
from jiki.tool_client import IMCPClient
from typing import List, Dict, Any

# Implementing a custom client (Conceptual - requires actual logic)
class MyNonMCPClient(IMCPClient):
    def __init__(self, api_endpoint: str):
        self.endpoint = api_endpoint
        # Add necessary state like authentication tokens, session objects etc.

    async def discover_tools(self) -> List[Dict[str, Any]]:
        # Logic to fetch tool definitions from the custom backend (e.g., via REST)
        # and translate them into the expected MCP-like schema format.
        print(f"Custom client discovering tools from {self.endpoint}...")
        # ... implementation ...
        return [{"tool_name": "custom_action", "description": "Performs a custom action", "arguments": {}, "required": []}]

    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        # Logic to call the specific tool/action on the custom backend
        # (e.g., make a POST request) and return the result as a string.
        print(f"Custom client executing '{tool_name}' on {self.endpoint}...")
        # ... implementation ...
        return f"Result from custom action '{tool_name}'"

    async def list_resources(self) -> List[Dict[str, Any]]:
        # Logic for listing resources, if applicable to the custom backend.
        print(f"Custom client listing resources from {self.endpoint}...")
        # ... implementation ...
        return [] # Or return actual resources if backend supports them

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        # Logic for reading a resource, if applicable.
        print(f"Custom client reading resource '{uri}' from {self.endpoint}...")
        # ... implementation ...
        return [] # Or return actual content

    async def list_roots(self) -> List[Dict[str, Any]]:
        # If the custom backend has a concept similar to roots, implement here.
        print(f"Custom client listing roots...")
        # ... implementation ...
        return []

    async def send_roots_list_changed(self) -> None:
        # If the custom backend needs notifications about context changes, implement here.
        print(f"Custom client handling roots changed...")
        # ... implementation ...
        pass

# Usage:
# custom_client = MyNonMCPClient("http://my-custom-api.com")
# orchestrator = JikiOrchestrator(client=custom_client, ...) # Assuming direct Orchestrator init
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

Sampling parameters allow fine-grained control over how the underlying Language Model (LLM) generates text during interactions. They influence the creativity, determinism, length, and stopping conditions of the responses.

**Note:** This `SamplerConfig` controls the parameters for Language Model calls made *directly by the Jiki orchestrator* when processing user input and generating responses. It does not configure how Jiki might handle the separate Model Context Protocol feature where an *MCP server* requests an LLM completion from the client (via `sampling/createMessage`, see [https://modelcontextprotocol.io/docs/concepts/sampling](https://modelcontextprotocol.io/docs/concepts/sampling)).

Jiki provides the `jiki.sampling.SamplerConfig` dataclass to specify these settings:

*   `temperature` (float, default 1.0): Controls randomness. Lower values (e.g., 0.1) make the output more focused and deterministic, while higher values increase diversity and creativity.
*   `top_p` (float, default 1.0): Nucleus sampling. Restricts generation to tokens comprising the top 'p' probability mass. Lower values (e.g., 0.8) further restrict the LLM's choices, often leading to more factual or less surprising text.
*   `max_tokens` (Optional[int], default None): Sets a hard limit on the maximum number of tokens to be generated in a single response.
*   `stop` (Optional[List[str]], default None): A list of text sequences. If the LLM generates any of these sequences, generation stops immediately.

To apply custom sampling settings, you instantiate `SamplerConfig` with your desired values and pass this instance to the main `Jiki()` factory function using the `sampler_config` argument. The orchestrator will then use these parameters when invoking the LLM.

#### Usage Example

```python
from jiki import Jiki, SamplerConfig

# Define custom sampling settings (e.g., low temperature for less randomness)
custom_sampler = SamplerConfig(temperature=0.2, max_tokens=100)

# Pass the config to the Jiki factory
orchestrator = Jiki(
    sampler_config=custom_sampler,
    # Other necessary parameters like mcp_script_path or tools...
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Subsequent calls will use the specified sampling parameters
result = orchestrator.process("Explain the concept of temperature in LLMs briefly.")
print(result)
```

::: jiki.sampling.SamplerConfig
    options:
      show_root_heading: false # Focus on explanation above
      show_source: false
      heading_level: 4 # Subordinate to Sampling Configuration

::: jiki.sampling.ISamplerConfig
    options:
      show_root_heading: false # Interface details, less prominent
      show_source: false
      heading_level: 4
      show_bases: true

### Prompt Building

#### Prompt Builder Pattern and Customization

Prompt builders are essential components that control how Jiki structures and formats the input sent to the language model (LLM). They are responsible for assembling system instructions, tool schemas, resource information, and conversation history into a coherent prompt.

Note: Jiki's `PromptBuilder` is responsible for assembling the overall context sent to the LLM on the *client-side*. This is distinct from the concept of server-side 'Prompts' defined in the Model Context Protocol (often via `@mcp.prompt` in FastMCP servers, see [https://gofastmcp.com/servers/prompts](https://gofastmcp.com/servers/prompts)), which are reusable message templates that an MCP server can generate upon request from a client. The `PromptBuilder` integrates the results of tool calls and the conversation history, potentially including messages generated by server-side prompts if the client requested them.

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

# Example demonstrating conditional prompt logic (Conceptual)

class DynamicPromptBuilder(IPromptBuilder):
    def __init__(self):
        # Builders might store state if needed, though how it's populated
        # depends on how the Orchestrator uses the builder instance.
        self.conversation_mode = "general" 

    def create_available_tools_block(self, tools_config):
        # Standard tool block generation (implementation omitted)
        # ...
        return "<!-- Tools Block -->\n"

    def create_available_resources_block(self, resources_config):
        # Standard resource block generation (implementation omitted)
        # ...
        return "<!-- Resources Block -->\n"

    def build_initial_prompt(self, user_input, tools_config, resources_config=None, history=None):
        # NOTE: Assumes 'history' (list of messages) is passed or accessible.
        # This detail is not explicitly confirmed in the current reference.
        
        system_message_content = "You are a helpful assistant.\n"
        
        # --- Dynamic Logic Example ---
        # Check user input or history for keywords to change system prompt
        if "write code" in user_input.lower():
            system_message_content += "Focus on providing accurate and efficient code solutions.\n"
            self.conversation_mode = "coding" # Example of changing state
        elif history and any("customer support" in msg.get("content", "").lower() for msg in history if msg["role"] == "user"):
             system_message_content += "Adopt a polite and helpful customer support persona.\n"
             self.conversation_mode = "support"
        else:
            self.conversation_mode = "general"
        # --- End Dynamic Logic ---

        tools_block = self.create_available_tools_block(tools_config)
        resources_block = self.create_available_resources_block(resources_config)

        # Combine parts into the initial system prompt message dictionary
        system_prompt = {
            "role": "system",
            "content": f"{system_message_content}\n{tools_block}\n{resources_block}"
        }
        
        # The orchestrator would then typically append the history (if any) 
        # and the latest user_input message after this system prompt.
        # This method *itself* usually just returns the system prompt part.
        return system_prompt 

# Usage with orchestrator:
# dynamic_builder = DynamicPromptBuilder()
# orchestrator = Jiki(
#     prompt_builder=dynamic_builder,
#     # other parameters...
# )

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

The Model Context Protocol (MCP) includes the concept of "Roots", which allows a client application (like Jiki) to inform the MCP server about its current contextual boundaries or accessible resources. The server can leverage this information to tailor its behavior. (See [MCP Docs on Roots](https://modelcontextprotocol.io/docs/concepts/architecture#roots)).

While MCP Roots relate to informing the *server* about context, Jiki also needs a mechanism to save and restore the *client-side* conversation state (message history, recent tool calls) for persistence across sessions or requests. Jiki abstracts this client-side state management through the `IConversationRootManager` interface.

**Integration:** An implementation of `IConversationRootManager` can be provided to the `JikiOrchestrator` via the optional `conversation_root_manager` argument in its constructor (`__init__`).

**Functionality:**
*   Implementations of this interface are responsible for defining *what* client-side state needs saving and loading.
*   The interface requires implementing `snapshot()` to serialize the relevant state into a dictionary and `resume()` to restore the state from such a dictionary.

**Default Behavior:** If no custom `conversation_root_manager` is provided to the orchestrator, the orchestrator instance *itself* acts as the default manager. Its built-in `snapshot()` and `resume()` methods handle saving and loading the internal message list (`_messages`) and the list of tool calls from the last turn (`_last_tool_calls`).

**Usage:** The `snapshot()` and `resume()` methods (whether default or custom) are intended to be called *externally* by the application using the orchestrator instance. For example, a web application might call `snapshot()` after processing a request to save the state to a database and `resume()` at the start of the next request to load it. They are *not* automatically called by the orchestrator during its internal processing loop.

**Distinction from MCP Roots:** While a custom `IConversationRootManager` *could* potentially include data relevant to MCP Roots within its snapshot, the interface's primary role in Jiki's structure is client-side conversation state persistence. Communicating MCP Roots to the server is typically a responsibility of the `IMCPClient` implementation.

::: jiki.roots.conversation_root_manager.IConversationRootManager
    options:
      show_root_heading: false
      show_source: false
      heading_level: 4 # Keep heading level as previously adjusted
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

Jiki provides several utility functions to assist with common tasks involved in processing LLM interactions, managing context, and preparing output.

### `clean_output`

This function is designed to post-process the raw text generated by the LLM before it is presented to the end-user. It removes internal Jiki/MCP tags (such as `<mcp_tool_call>`, `<mcp_tool_result>`, `<mcp_available_tools>`, and `<Assistant_Thought>`) that are used during the interaction logic but are not meant for final display. It also normalizes whitespace by trimming leading/trailing spaces and collapsing multiple consecutive newlines into double newlines for better readability.

::: jiki.utils.cleaning.clean_output
    options:
      show_root_heading: false # Focus on the explanation above
      show_source: false
      heading_level: 4

### `trim_context`

LLMs have finite context windows. This utility helps manage the conversation history to ensure it fits within a specified token limit (`max_tokens`). It operates directly (in-place) on the list of message dictionaries. Its strategy is to always preserve the first message (typically the system prompt) and then remove older messages (starting from the second message) one by one until the total token count, as measured by the provided `num_tokens` function (often `jiki.utils.token.count_tokens`), is below the `max_tokens` threshold. It guarantees that at least two messages (the system prompt and the most recent message) remain.

::: jiki.utils.context.trim_context
    options:
      show_root_heading: false # Focus on the explanation above
      show_source: false
      heading_level: 4

### `count_tokens`

Accurately estimating the number of tokens used by the conversation history is crucial for context management. This function calculates the token count for a given list of messages, specific to a particular model (`model_name`). It leverages the `tiktoken` library when available for precise counting (especially for OpenAI models), including per-message overhead. If `tiktoken` is not installed or the model is unknown to it, it falls back to a simple character-based heuristic (approximately 4 characters per token). The output of this function is typically used as the input to the `trim_context` utility's `num_tokens` argument.

::: jiki.utils.token.count_tokens
    options:
      show_root_heading: false # Focus on the explanation above
      show_source: false
      heading_level: 4

## Complete Module Reference

This reference document has detailed the core components, interfaces, and configuration options available in the Jiki framework. For specifics on individual classes and functions, please refer to the relevant sections above. For a comprehensive view of all modules and their contents, exploring the source code directly is recommended. 