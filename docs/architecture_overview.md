# Jiki: Architecture Overview

This document provides a high-level overview of Jiki's internal architecture, focusing on the flow of information during a typical interaction.

## Core Components

1.  **`Jiki()` Factory (in `jiki/__init__.py`)**: The primary user entry point. Creates and configures the `JikiOrchestrator`, `TraceLogger`, `JikiClient`, and `LiteLLMModel` with sensible defaults.
2.  **`JikiOrchestrator` (in `jiki/orchestrator.py`)**: The central coordinator. Manages conversation history, builds prompts, interacts with the LLM, intercepts tool calls, and dispatches them to the `IMCPClient`.
3.  **`IMCPClient` Protocol (in `jiki/tool_client.py`)**: Defines the interface for communicating with an MCP tool server (discovery, execution, resources, roots).
    *   **`JikiClient` (in `jiki/mcp_client.py`)**: The default concrete implementation of `IMCPClient`, using `fastmcp` for communication.
    *   **`BaseMCPClient` (in `jiki/mcp_client.py`)**: Abstract base class for creating custom MCP client implementations.
4.  **`LiteLLMModel` (in `jiki/models/litellm.py`)**: Wrapper around LiteLLM, providing a consistent interface for interacting with various LLM providers (streaming, function/tool calling interception).
5.  **`IPromptBuilder` Protocol (in `jiki/prompts/prompt_builder.py`)**: Defines how system prompts (including tool schemas) are constructed.
    *   **`DefaultPromptBuilder`**: Standard implementation.
6.  **`TraceLogger` (in `jiki/logging.py`)**: Handles logging of interaction events and complete traces.
7.  **Utilities (in `jiki/utils/`)**: Helper functions for parsing, validation, context management, etc.

## Interaction Flow (Single Turn)

Let's trace a user query like "What is 5 * 7?" assuming the calculator tool is available via an MCP server.

1.  **User Input**: The user provides the query to `orchestrator.process("What is 5 * 7?")` (where `orchestrator` was likely created by `Jiki()`).
2.  **Prompt Construction**: `JikiOrchestrator` uses its `IPromptBuilder` to construct the prompt sent to the LLM. This includes:
    *   System instructions.
    *   Available tool schemas (obtained earlier from `IMCPClient.discover_tools()`).
    *   Current conversation history (trimmed to fit context window).
    *   The latest user query.
3.  **LLM Call**: `JikiOrchestrator` calls `LiteLLMModel.generate_and_intercept()`, passing the constructed prompt and a callback to handle tool calls.
4.  **LLM Reasoning & Tool Call Emission**: The LLM processes the prompt. Recognizing the need for calculation, it streams back text including a tool call block:
    ```xml
    Okay, I can calculate that. <mcp_tool_call tool_name="calculator">{"expression": "5 * 7"}</mcp_tool_call>
    ```
5.  **Tool Call Interception**: `generate_and_intercept()` detects the `<mcp_tool_call>` tag. It pauses streaming back to the orchestrator and invokes the callback provided in step 3.
6.  **Parsing & Validation**: Inside the callback (within `JikiOrchestrator`), the content between the tags is parsed (`parse_tool_call_content`) and validated (`validate_tool_call`) against the known schema for the `calculator` tool.
7.  **Tool Execution**: `JikiOrchestrator` calls `IMCPClient.execute_tool_call(tool_name="calculator", arguments={"expression": "5 * 7"})`.
    *   `JikiClient` (the default implementation) sends the corresponding JSON-RPC request (`tools/call`) to the MCP server via `fastmcp`.
    *   The MCP server (e.g., `calculator_server.py`) executes the tool function.
    *   The server sends the result (`35`) back via JSON-RPC.
    *   `JikiClient` receives the result and returns it to the orchestrator.
8.  **Result Injection**: The orchestrator formats the tool result (e.g., as an XML block `<mcp_tool_result tool_name="calculator">35</mcp_tool_result>`) and adds it to the conversation history/prompt context.
9.  **LLM Continues**: `generate_and_intercept()` resumes streaming, now providing the updated context (including the tool result) back to the LLM.
10. **Final Response Generation**: The LLM uses the tool result to formulate the final answer (e.g., "5 * 7 is 35.") and streams it back.
11. **Output Cleaning**: The final streamed response is cleaned (`clean_output`) to remove any remaining partial tags or artifacts.
12. **Return Result**: The orchestrator returns the final cleaned response to the user.
13. **Logging**: Throughout this process, if tracing is enabled (`Jiki(trace=True)`), `TraceLogger` records events (user input, prompt, tool call, tool result, final response) and the complete interaction trace.

## Key Design Principles

- **Protocol-Driven**: Core components interact via defined interfaces (`IMCPClient`, `IPromptBuilder`), allowing easy extension or replacement.
- **Abstraction**: High-level functions like `Jiki()` and `JikiOrchestrator.process()` hide the complexity of MCP communication, prompt engineering, and tool call handling.
- **Composability**: Components like loggers, clients, and prompt builders can be mixed and matched (especially when constructing `JikiOrchestrator` manually).
- **Leverage Existing Standards**: Uses MCP for tool interaction and LiteLLM for broad model support.

# Architecture Overview

This document fulfills Phase 1 (items 1-3) of our refactor plan by providing:

1. **Module Inventory**: A table listing each module, its path, responsibility, and key dependencies.
2. **Cross-Cutting Concerns**: Identification of logging/tracing, serialization, and error-handling patterns.
3. **Existing Workflows**: An overview of tool discovery, execution flow, prompt generation, and resource access.

---

## 1. Module Inventory

| Module                     | Path                                | Responsibility                                      | Dependencies                          |
|----------------------------|-------------------------------------|-----------------------------------------------------|---------------------------------------|
| JikiOrchestrator           | `jiki/orchestrator.py`              | Core engine handling context, tool calls, streaming | `IPromptBuilder`, `IMCPClient`, utils |
| JikiClient                 | `jiki/mcp_client.py`                | Full MCP client (discovery, invoke, resources, etc.)| `BaseMCPClient`, `fastmcp`, logging, serialization |
| BaseMCPClient              | `jiki/mcp_client.py`                | Abstract base for MCP clients (RPC structure)       | `abc`, JSON                           |
| IToolClient, IMCPClient    | `jiki/tool_client.py`               | Protocols for tool/resource client interfaces       | `IResourceManager`                    |
| DefaultPromptBuilder       | `jiki/prompts/prompt_builder.py`    | Build prompts for tools, resources, and user input  | None                                  |
| IResourceManager           | `jiki/resources/resource_manager.py`| Protocol for listing/reading MCP resources          | None                                  |
| ITransport, factory        | `jiki/transports/factory.py`        | Transport interface and factory for stdio/SSE       | `fastmcp.client.transports`           |
| SamplerConfig, ISamplerConfig | `jiki/sampling.py`             | LLM sampling parameters (temperature, top_p, etc.)  | None                                  |
| Logging utilities          | `jiki/logging.py`, `jiki/utils/logging.py` | Structured events and complete traces           | `os`, `datetime`, `json`              |
| Serialization helpers      | `jiki/serialization/helpers.py`     | JSON serializer default and helper method attachers | `json`, `datetime`, Pydantic hooks    |
| CLI frontends              | `jiki/cli.py`, `tools.json`         | Command-line entrypoints and argument parsing       | `argparse`, `os`, `json`              |
| Utilities                  | `jiki/utils/`                       | Context trimming, parsing, streaming, token counting| Various; see individual modules       |
| Models                     | `jiki/models/`                      | LLM model wrappers and response types               | Pydantic, LiteLLM                     |

---

## 2. Cross-Cutting Concerns

### Logging & Tracing
- **`TraceLogger`** (`jiki/logging.py`): records events via `log_event` and full traces with `log_complete_trace`.
- **`record_conversation_event`** (`jiki/utils/logging.py`): invoked by orchestrator to append history and dispatch to logger.

### Serialization
- **`json_serializer_default`** (`jiki/serialization/helpers.py`): handles dates, bytes, Pydantic models, and fallback to `repr()` for unknown types.
- Tools/results serialization helper in `BaseMCPClient._process_mcp_result`: Used by `JikiClient` to process results.

### Error Handling
- **Orchestrator** (`jiki/orchestrator.py`): catches parse/validation/tool call errors, records `<mcp_tool_result>` blocks.
- **`JikiClient`**: wraps RPC calls (`_call_rpc`), handshake, discovery, invocation in try/except, raising `RuntimeError` for callers.
- **CLI** (`jiki/cli.py`): catches and reports `ValueError`, `FileNotFoundError`, JSON parse errors, and uncaught exceptions with clean exit codes.


---

## 3. Existing Workflows

### 3.1 Tool Discovery
- **Implementation**: `JikiClient.discover_tools()` performs MCP initialize handshake and uses `_call_rpc('tools/list')`, converting schemas.
- **Invocation**: `Jiki(auto_discover_tools=True)` creates a `JikiClient` which runs `discover_tools()` and supplies `tools_config` to orchestrator.

### 3.2 Execution Flow
1. **User Input**: `JikiOrchestrator.process_user_input()` constructs messages, optionally including resources.
2. **Streaming**: uses `generate_and_intercept` (`jiki/utils/streaming.py`) to stream LLM tokens, intercepting `<mcp_tool_call>` blocks.
3. **Tool Call Handling**: `_handle_tool_call()` parses JSON call, validates via `validate_tool_call`, invokes `IMCPClient.execute_tool_call`, and injects `<mcp_tool_result>`.
4. **Continuation**: streaming resumes until the model emits the full answer.

### 3.3 Prompt Generation
- **Prompt Builder**: `DefaultPromptBuilder.build_initial_prompt()` (in `jiki/prompts/prompt_builder.py`) composes system prompt with instructions, `<mcp_available_tools>`, `<mcp_available_resources>` and user query.
- **Available Tools Block**: `create_available_tools_block()` formats tool schemas for the LLM.

### 3.4 Resource Access
- **Listing**: `JikiClient.list_resources()` calls `_call_rpc('resources/list')`.
- **Reading**: `JikiClient.read_resource(uri)` calls `_call_rpc('resources/read')`.
- **Usage**: Orchestrator includes resource list (obtained via `IMCPClient` interface, fulfilled by `JikiClient`) into the first system prompt.

---

This overview aligns with our refactor plan's Phase 1 deliverables, establishing a clear map of the codebase and its cross-cutting patterns. 