# Jiki API Reference

This API reference documents the key components of Jiki's architecture. It's organized by functional areas to help you understand how the different pieces fit together.

## Core Components

This section covers the central components of Jiki that form the backbone of the orchestration framework.

### Factory Function

::: jiki.Jiki
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

The factory function is the primary entry point for most users. It simplifies creating a properly configured orchestrator with sensible defaults.

#### The Jiki() Factory Pattern

The `Jiki()` function follows the factory pattern, creating and configuring all necessary components behind the scenes:

1. **Initialization Flow**:
   - Sets up a `TraceLogger` if tracing is enabled
   - Configures the appropriate MCP transport (stdio or SSE)
   - Creates a `JikiClient` instance for tool/resource management
   - Discovers or loads tool configurations
   - Initializes a language model wrapper (via LiteLLM)
   - Creates and returns a fully configured `JikiOrchestrator`

2. **Key Parameters**:
   - `model`: LLM identifier (e.g., "anthropic/claude-3-sonnet-20240229")
   - `tools`: Tool configurations as JSON file path or list
   - `auto_discover_tools`: Boolean to automatically discover tools
   - `mcp_mode`: Transport type ("stdio" or "sse")
   - `mcp_script_path`: Path to MCP server script (for stdio)
   - `mcp_url`: URL of MCP server (for SSE/HTTP)
   - `trace`: Enable/disable interaction tracing
   - `trace_dir`: Directory for trace logs
   - `conversation_root_manager`: Custom state manager
   - `prompt_builder`: Custom prompt builder
   - `sampler_config`: Custom sampling parameters

3. **Usage Examples**:

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

### Orchestrator

::: jiki.orchestrator.JikiOrchestrator
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

The orchestrator is the central component that coordinates LLM interactions, tool calls, and conversation management. It:

1. Builds prompts for the LLM with tool schemas
2. Intercepts tool calls emitted by the LLM
3. Validates and executes tool calls via the MCP client
4. Injects results back into the conversation
5. Maintains conversation context

#### JikiOrchestrator Architecture

The `JikiOrchestrator` serves as the central coordination engine, managing the complete lifecycle of a tool-augmented conversation:

1. **Component Management**:
   - Wraps a language model (via the `model` parameter)
   - Maintains a reference to the MCP client
   - Manages tool configurations and schemas
   - Controls prompt generation through a `PromptBuilder`
   - Handles logging and tracing via a `TraceLogger`

2. **Conversation Flow**:
   - Constructs initial system prompts with tool/resource information
   - Processes user inputs within an ongoing conversation
   - Streams tokens from the LLM, watching for tool call blocks
   - Intercepts tool calls, validates them, and executes via the MCP client
   - Injects tool results back into the context
   - Manages token budgets through context trimming

3. **State Management**:
   - Maintains conversation history in LiteLLM/OpenAI format
   - Supports conversation snapshotting and resuming
   - Tracks tool calls and traces for the current conversation turn

4. **Key Methods**:
   - `process()`: Handle a single query and return a string result
   - `process_detailed()`: Return structured information about tool calls
   - `process_user_input()`: Async underlying implementation
   - `create_available_tools_block()`: Format tool schemas for prompts
   - `snapshot()` / `resume()`: Save/restore conversation state

5. **Usage Example**:

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

### Detailed Response

::: jiki.models.response.DetailedResponse
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.models.response.ToolCall
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

The detailed response objects provide structured information about LLM interactions, including tool calls and execution traces.

#### Working with Detailed Responses

The `DetailedResponse` and `ToolCall` classes enable programmatic access to interaction data:

1. **DetailedResponse Structure**:
   - `result`: The complete text response from the LLM
   - `tool_calls`: List of tool calls made during processing
   - `traces`: Raw interaction traces if tracing was enabled

2. **ToolCall Structure**:
   - `tool_name`: Name of the called tool
   - `arguments`: Dictionary of arguments passed to the tool
   - `result`: The response returned by the tool

3. **Common Use Cases**:
   - Analyzing which tools were used for debugging
   - Extracting structured data from tool results
   - Building UIs that visualize tool execution
   - Creating test cases for tool integration

4. **Usage Example**:

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

## MCP Client Components

These components handle communication with Model Context Protocol (MCP) tool servers.

### Jiki Client

::: jiki.mcp_client.JikiClient
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

The JikiClient is the standard implementation for communicating with MCP tool servers. It handles:

1. Tool discovery
2. Tool execution
3. Resource listing and reading
4. Roots management
5. Interaction tracing

#### JikiClient Architecture

The `JikiClient` serves as the bridge between Jiki and MCP-compatible tool servers, implementing all aspects of the Model Context Protocol:

1. **Transport Management**:
   - Uses `fastmcp.Client` to establish communication
   - Supports multiple transport types (stdio, SSE, WebSocket)
   - Handles connection lifecycle within async contexts

2. **Tool Operations**:
   - `discover_tools()`: Lists available tools from the server
   - `execute_tool_call()`: Invokes tools with arguments
   - Processes and formats tool results for the orchestrator

3. **Resource Operations**:
   - `list_resources()`: Retrieves available resources
   - `read_resource()`: Fetches specific resource content

4. **Roots Management**:
   - `list_roots()`: Gets current root URIs for conversation state
   - `send_roots_list_changed()`: Notifies server of state changes

5. **Tracing**:
   - Captures all MCP interactions for debugging
   - Records server-side logging notifications
   - Provides access to traces via `get_interaction_traces()`

6. **Legacy Support**:
   - Maintains backwards compatibility through `EnhancedMCPClient`
   - Handles graceful deprecation warnings

7. **Usage Example**:

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

### Client Interfaces

::: jiki.tool_client.IMCPClient
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.tool_client.IToolClient
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

These interfaces define the contract that MCP client implementations must fulfill. They're useful if you want to create custom clients for special scenarios.

#### Client Interfaces Hierarchy

The client interfaces establish a clear contract for tool integration:

1. **Interface Hierarchy**:
   - `IToolClient`: Base interface for basic tool operations
   - `IMCPClient`: Extended interface adding MCP-specific capabilities

2. **Extension Points**:
   - Create custom clients for specialized integrations
   - Implement mock clients for testing
   - Build adapters for non-MCP tool systems

3. **Implementation Requirements**:
   - Tool clients must implement tool discovery and execution
   - MCP clients add resource and roots management
   - All operations are async for non-blocking performance

4. **Usage Example**:

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

SamplerConfig controls how the LLM generates responses by adjusting parameters like temperature and top_p.

### Prompt Building

::: jiki.prompts.prompt_builder.IPromptBuilder
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.prompts.prompt_builder.DefaultPromptBuilder
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

Prompt builders control how system instructions, tool schemas, and other context are formatted for the LLM.

#### Prompt Builder Pattern

The prompt builder components control how Jiki formats instructions and tool information for the LLM:

1. **Interface Contract**:
   - `create_available_tools_block()`: Format tool schemas
   - `create_available_resources_block()`: Format resource information
   - `build_initial_prompt()`: Construct the complete system prompt

2. **Default Implementation**:
   - `DefaultPromptBuilder` provides standard MCP-compatible formatting
   - Uses utility functions to generate properly formatted blocks
   - Follows Model Context Protocol specifications

3. **Customization Scenarios**:
   - Change the system instructions for different use cases
   - Modify tool schema presentation for specific LLMs
   - Add custom context or examples to the prompt

4. **Usage Example**:

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

### Conversation State Management

::: jiki.roots.conversation_root_manager.IConversationRootManager
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

Conversation root managers enable saving and resuming conversation state, which is useful for persistent interactions across sessions.

## Tools and Resources

These components handle tool and resource definitions.

### Tool Configuration

::: jiki.tools.tool.Tool
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: jiki.tools.config.load_tools_config
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

Tools are defined using schemas that specify their name, description, parameters, and other metadata.

### Resource Management

::: jiki.resources.resource_manager.IResourceManager
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

Resources represent data assets that can be accessed by the LLM during interaction, such as documentation, templates, or external information.

## Logging and Debugging

Components for tracing and debugging Jiki interactions.

### Trace Logger

::: jiki.logging.TraceLogger
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

The trace logger records detailed information about interactions, including LLM prompts, tool calls, and results.

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

For a comprehensive reference of all Jiki modules and classes, use the links below.

### jiki

::: jiki
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.orchestrator

::: jiki.orchestrator
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.mcp_client

::: jiki.mcp_client
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.models

::: jiki.models
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.tools

::: jiki.tools
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.prompts

::: jiki.prompts
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.resources

::: jiki.resources
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.roots

::: jiki.roots
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.sampling

::: jiki.sampling
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.logging

::: jiki.logging
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3

### jiki.utils

::: jiki.utils
    options:
      members: false
      show_root_heading: true
      show_source: false
      heading_level: 3 