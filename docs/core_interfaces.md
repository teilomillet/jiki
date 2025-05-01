# Core Interfaces in Jiki

<!-- This file explains the key Python Protocols (interfaces) that define Jiki's architecture. -->
<!-- It focuses on *why* these interfaces exist and *what* responsibility each one has. -->

Jiki is built with flexibility and extensibility in mind. Instead of tightly coupling components together, it relies on a set of core **interfaces** (defined using Python's `typing.Protocol`). These interfaces act as contracts, specifying *what* a component should do without dictating *how* it should do it.

This design offers several key advantages:
- **Pluggability:** You can easily swap out Jiki's default components (like the tool client or prompt builder) with your own custom implementations, as long as they adhere to the required interface.
- **Testability:** Interfaces make it simple to use mock or stub implementations during testing, isolating the component you want to test from its dependencies.
- **Maintainability:** Clear contracts make the responsibilities of each component explicit, making the codebase easier to understand and maintain.

The [`JikiOrchestrator`](#how-they-work-together-in-the-orchestrator) sits at the center, coordinating interactions by relying on implementations of these core interfaces.

---

## Communicating with Tools & Servers (MCP Client)

<!-- This section covers the interface responsible for all communication with external MCP tool servers. -->

To interact with external tools and access resources provided by MCP-compliant servers, the `JikiOrchestrator` uses a component that fulfills the [`IMCPClient`](#imcpclient-1) interface. This is the primary contract for all communication flowing between the orchestrator and the outside world via the Model Context Protocol.

The `IMCPClient` interface bundles several capabilities defined by the MCP standard:

1.  **Tool Handling:** Discovering available tools and executing tool calls. This basic functionality is defined by the [`IToolClient`](#itoolclient) interface.
2.  **Resource Handling:** Listing available data resources and reading their content. This is defined by the [`IResourceManager`](#iresourcemanager) interface.
3.  **Root Handling:** Managing MCP "Roots," which inform the server about the client's context. This involves listing the client's current roots and notifying the server if they change.

By depending on the comprehensive `IMCPClient` interface, the orchestrator can manage tools, resources, and roots without needing to know the specific details of the communication library (like `fastmcp`) or the transport mechanism (like stdio or SSE) being used underneath.

### `IToolClient`

This defines the absolute minimum required for tool interaction.

```python
# Located in: jiki/tool_client.py
from typing import Protocol, List, Dict, Any

class IToolClient(Protocol):
    async def discover_tools(self) -> List[Dict[str, Any]]:
        # Returns a list of tool schemas
        ...

    async def execute_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        # Executes the named tool and returns its string result
        ...
```

### `IResourceManager`

This defines the contract for accessing MCP resources.

```python
# Located in: jiki/resources/resource_manager.py
from typing import Protocol, List, Dict, Any

class IResourceManager(Protocol):
    async def list_resources(self) -> List[Dict[str, Any]]:
        # Returns a list of resource metadata dictionaries
        ...

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        # Reads content for a resource URI, returning content blocks
        ...
```

### `IMCPClient`

This is the **main interface** used by `JikiOrchestrator`. It combines [`IToolClient`](#itoolclient) and [`IResourceManager`](#iresourcemanager) and adds methods for MCP roots management.

```python
# Located in: jiki/tool_client.py
from jiki.resources.resource_manager import IResourceManager
from jiki.tool_client import IToolClient # Explicit import for clarity
from typing import Protocol, List, Dict, Any

# Inherits methods from IToolClient and IResourceManager
class IMCPClient(IToolClient, IResourceManager, Protocol):
    # Methods specifically for MCP Roots context management
    async def list_roots(self) -> List[Dict[str, Any]]:
        # Gets the list of current root URIs/metadata
        ...
    async def send_roots_list_changed(self) -> None:
        # Notifies the server that the client's roots have changed
        ...
```

-   **Standard Implementation:** `jiki.mcp_client.JikiClient` is the default class that implements `IMCPClient`. It uses the `fastmcp` library internally.
-   **Note on `IRootManager`:** While an `IRootManager` protocol exists (`jiki/roots/root_manager.py`) defining `list_roots` and `send_roots_list_changed`, the `IMCPClient` itself defines these methods directly. `JikiOrchestrator` interacts with its `IMCPClient` instance for these operations. The separate `IRootManager` protocol primarily serves as an internal organizational structure, potentially useful for alternative `IMCPClient` implementations, rather than being directly used by the orchestrator itself.

---

## Formatting LLM Input (Prompt Builder)

<!-- This section explains the interface for controlling how prompts are constructed. -->

How instructions, tool information, resource details, and conversation history are presented to the LLM significantly impacts its performance. The [`IPromptBuilder`](#ipromptbuilder-1) interface abstracts this responsibility.

The orchestrator uses an `IPromptBuilder` implementation to:
-   Create the formatted block describing available tools (`<mcp_available_tools>`).
-   Create the formatted block describing available resources (`<mcp_available_resources>`).
-   Assemble the initial system prompt, combining instructions, user input, and the tool/resource blocks.

By providing a custom implementation of `IPromptBuilder`, you can tailor the exact text and structure sent to the LLM, perhaps optimizing for specific models or adding domain-specific instructions.

### `IPromptBuilder`

```python
# Located in: jiki/prompts/prompt_builder.py
from typing import Protocol, List, Dict, Any, Optional

class IPromptBuilder(Protocol):
    def create_available_tools_block(
        self, tools_config: List[Dict[str, Any]]
    ) -> str:
        # Generates the XML-like block listing tools for the LLM
        ...

    def create_available_resources_block(
        self, resources_config: List[Dict[str, Any]]
    ) -> str:
        # Generates the XML-like block listing resources for the LLM
        ...

    def build_initial_prompt(
        self,
        user_input: str,
        tools_config: List[Dict[str, Any]],
        resources_config: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # Constructs the complete initial prompt string sent to the LLM
        ...
```

-   **Default Implementation:** `jiki.prompts.prompt_builder.DefaultPromptBuilder` provides standard MCP-compliant formatting.

---

## Controlling LLM Output (Sampler Configuration)

<!-- This section covers the interface for LLM generation parameters. -->

The way an LLM generates text can be controlled via sampling parameters like temperature, top-p, maximum tokens, and stop sequences. The [`ISamplerConfig`](#isamplerconfig-1) interface defines a standard way to specify these parameters.

An object implementing `ISamplerConfig` is used by the LLM wrapper (e.g., `LiteLLMModel`) when making calls to the underlying language model API.

### `ISamplerConfig`

```python
# Located in: jiki/sampling.py
from typing import Protocol, Optional, List, Dict, Any

class ISamplerConfig(Protocol):
    temperature: float
    top_p: float
    max_tokens: Optional[int]
    stop: Optional[List[str]]

    def to_dict(self) -> Dict[str, Any]:
        # Converts the config into a dictionary suitable for LLM API calls
        ...
```

-   **Concrete Type:** `jiki.sampling.SamplerConfig` is a dataclass implementation provided by Jiki.

---

## Managing Conversation State (Conversation Root Manager)

<!-- This section explains the interface for saving and loading the conversation history. -->

While MCP Roots (`IMCPClient.list_roots`) deal with informing the *server* about the client's context, applications often need to persist the *client-side* conversation state (like the message history) across sessions or requests. The [`IConversationRootManager`](#iconversationrootmanager-1) interface defines the *structure* for this persistence.

**Important:** The `JikiOrchestrator` instance *itself* provides the default implementation of `snapshot()` and `resume()`. The application logic is responsible for:
1. Calling `orchestrator.snapshot()` to get the current state dictionary.
2. Saving this dictionary (e.g., to a file, database).
3. Later, loading the dictionary from storage.
4. Creating a *new* `JikiOrchestrator` instance.
5. Calling `new_orchestrator.resume(loaded_snapshot)` to restore the state *into* the new orchestrator.

The `IConversationRootManager` protocol primarily serves as a type hint and defines the expected dictionary format for the snapshot. While you *can* provide a separate object implementing this protocol to the orchestrator's `__init__`, the orchestrator does not actively call methods on this external object during its normal operation. Its main purpose is to define the contract fulfilled by the orchestrator's own `snapshot`/`resume` methods.

### `IConversationRootManager`

```python
# Located in: jiki/roots/conversation_root_manager.py
from typing import Protocol, Dict, Any

class IConversationRootManager(Protocol):
    def snapshot(self) -> Dict[str, Any]:
        # Captures the current client-side state into a serializable dictionary.
        # Expected keys: "messages", "conversation_history", "last_tool_calls"
        ...

    def resume(self, snapshot: Dict[str, Any]) -> None:
        # Called *by the application* on the orchestrator instance
        # to restore its client-side state from a dictionary.
        ...
```

-   **Key Distinction:** This interface defines the *format* for client-side conversation state persistence. The actual saving/loading logic resides within the application code interacting with the orchestrator's `snapshot()` and `resume()` methods. This is separate from the MCP roots mechanism used for server communication via [`IMCPClient`](#imcpclient-1).

---

## How They Work Together in the Orchestrator

The `JikiOrchestrator` uses these interfaces to manage the interaction flow:

1.  **Initial Prompt:** When processing the first user input, the orchestrator calls `IMCPClient.list_resources()` to get available resources. It then uses `IPromptBuilder.build_initial_prompt()` to create the system prompt, passing the user input, tool schemas, and resource list.
2.  **LLM Interaction:** The orchestrator passes the message list (including the system prompt) to the LLM wrapper (like `LiteLLMModel`), which uses the `ISamplerConfig` parameters for the generation call.
3.  **Tool Call Handling:** If the LLM response contains a tool call signal (`<mcp_tool_call>`), the orchestrator intercepts it, parses the details, validates them against the known tool schemas, and then calls `IMCPClient.execute_tool_call()`.
4.  **Result Injection:** The result string returned by `IMCPClient.execute_tool_call()` is formatted (`<mcp_tool_result>`) and added back to the message list.
5.  **Continuation:** The process repeats, sending the updated message list (including the tool result) back to the LLM until a final response is generated.
6.  **State Management:** Throughout the process, the message history is maintained internally. The application can call `orchestrator.snapshot()` to retrieve this history (and other state) and later call `orchestrator.resume()` on a new instance to load it. This interaction uses the structure defined by [`IConversationRootManager`](#iconversationrootmanager-1).

This reliance on interfaces ensures that the core orchestration logic remains decoupled from the specific implementations of communication, prompt formatting, sampling, and state persistence.

---

## Extending Jiki: Plug & Play

<!-- This section provides concrete examples of implementing these interfaces for customization. -->
<!-- It remains largely unchanged from the original document. -->

All core behaviors are defined via protocols, so you can customize exactly what you need.

### 1. Custom Prompt Builder

```python
# Assume: from jiki.prompts.prompt_builder import DefaultPromptBuilder, IPromptBuilder
# Assume: from jiki.orchestrator import JikiOrchestrator
# Assume necessary model and client imports are present

class FancyPromptBuilder(DefaultPromptBuilder):
    # Override only the method you need to change
    def build_initial_prompt(self, user_input, tools_config, resources_config=None):
        # Example: Add a custom header
        header = "### 🎩 Welcome to Fancy Jiki!\\n"
        # Call the original method for the standard structure
        base_prompt = super().build_initial_prompt(user_input, tools_config, resources_config)
        return header + base_prompt

# --- Orchestrator setup ---
# model = LiteLLMModel(...)
# client = JikiClient(...)
# tools = [...]
# orch = JikiOrchestrator(
#     model=model,
#     mcp_client=client,
#     tools_config=tools,
#     prompt_builder=FancyPromptBuilder() # Pass instance implementing IPromptBuilder
# )
```

### 2. Custom Sampler Configuration

```python
# Assume: from jiki import Jiki # Use the main factory for convenience
# Assume: from jiki.sampling import ISamplerConfig, SamplerConfig
# Assume: from typing import Dict, Any, Optional, List

# Define a class implementing the ISamplerConfig protocol
class MySampler(ISamplerConfig):
    # Set desired sampling attributes
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: Optional[int] = 100
    stop: Optional[List[str]] = ['\\n\\n'] # Example stop sequence

    # Implement the required to_dict method
    def to_dict(self) -> Dict[str, Any]:
        params = {"temperature": self.temperature, "top_p": self.top_p}
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.stop is not None:
            params["stop"] = self.stop
        return params

# --- Jiki factory setup ---
# jiki_instance = Jiki(
#     model="gpt-4", # Or your preferred model
#     sampler_config=MySampler(), # Pass instance implementing ISamplerConfig
#     mcp_script_path="servers/calculator_server.py",
#     auto_discover_tools=True
# )
```

### 3. Custom Tool Client (e.g., for Tests)

```python
# Assume: from jiki.tool_client import IMCPClient
# Assume: from jiki.resources.resource_manager import IResourceManager
# Assume: from typing import List, Dict, Any, Optional

# Create a stub that fulfills the IMCPClient contract
class StubMCPClient(IMCPClient):
    async def discover_tools(self) -> List[Dict[str, Any]]:
        print("[StubMCPClient] Discovering tools...")
        # Example tool schema
        return [{"tool_name":"echo","description":"Echoes input","arguments":{"text":{"type":"string"}}, "required": ["text"]}]

    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        print(f"[StubMCPClient] Executing tool: {tool_name}")
        if tool_name == "echo":
            return arguments.get('text', '<missing text>')
        return f"ERROR: Unknown tool '{tool_name}'"

    # --- Implement IResourceManager methods ---
    async def list_resources(self) -> List[Dict[str, Any]]:
        print("[StubMCPClient] Listing resources...")
        return [] # No resources in this stub

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        print(f"[StubMCPClient] Reading resource: {uri}")
        raise NotImplementedError("Stub cannot read resources")

    # --- Implement IMCPClient root methods ---
    async def list_roots(self) -> List[Dict[str, Any]]:
        print("[StubMCPClient] Listing roots...")
        return []

    async def send_roots_list_changed(self) -> None:
        print("[StubMCPClient] Sending roots changed notification...")
        pass # No-op

# --- Orchestrator setup ---
# Assume: from jiki.orchestrator import JikiOrchestrator
# Assume: from jiki.models.litellm import LiteLLMModel
# model = LiteLLMModel("gpt-4")
# Tools config must match what the stub discovers
# stub_tools_config = StubMCPClient().discover_tools() # Call async method appropriately
# orch = JikiOrchestrator(
#     model=model,
#     mcp_client=StubMCPClient(), # Use the stub instance implementing IMCPClient
#     tools_config=stub_tools_config # Provide matching config
# )
```

### 4. Custom Conversation Root Manager (Illustrative Example)

This example shows a class fulfilling the `IConversationRootManager` protocol. Remember, the orchestrator *itself* implements `snapshot` and `resume`. Your application code interacts with the orchestrator's methods; this protocol defines the *structure* of the data returned by `snapshot` and expected by `resume`.

```python
# Assume: from jiki.roots.conversation_root_manager import IConversationRootManager
# Assume: from typing import Any, Dict
# Assume: from jiki import Jiki
# Assume: import json # Example using JSON for serialization

# Example illustrating the protocol implementation (NOT a functional persistence layer)
class MyConversationStateStructure(IConversationRootManager):
    # This class primarily serves to illustrate the protocol's methods.
    # In a real application, you wouldn't typically pass an instance of
    # this class to the Jiki orchestrator. Instead, you'd call
    # orchestrator.snapshot() and orchestrator.resume() directly.

    def snapshot(self) -> Dict[str, Any]:
        # This method signature matches the protocol.
        # The orchestrator's actual snapshot() method generates the dictionary.
        # Example structure it returns:
        # return {
        #     "messages": [...],
        #     "conversation_history": [...], # Often same as messages
        #     "last_tool_calls": [...]
        # }
        raise NotImplementedError("Call orchestrator.snapshot() instead.")

    def resume(self, snapshot: Dict[str, Any]) -> None:
        # This method signature matches the protocol.
        # The orchestrator's actual resume() method takes the dictionary
        # and updates its internal state.
        raise NotImplementedError("Call orchestrator.resume(snapshot) instead.")

# --- Application Logic Example ---
# jiki_instance = Jiki(...) # Initialize Jiki

# --> Interaction 1 <--
# result1 = jiki_instance.process("First user message")
# current_state = jiki_instance.snapshot() # Get state from orchestrator

# # Application saves the state (e.g., to a file)
# try:
#     with open("conversation_state.json", "w") as f:
#         json.dump(current_state, f)
# except IOError as e:
#     print(f"Error saving state: {e}")

# --> Interaction 2 (Later, possibly in a new process) <--
# loaded_state = None
# try:
#     with open("conversation_state.json", "r") as f:
#         loaded_state = json.load(f)
# except (IOError, json.JSONDecodeError) as e:
#     print(f"Error loading state: {e}")

# if loaded_state:
#     # Create a NEW orchestrator instance
#     new_jiki_instance = Jiki(...) # Use same config as before
#     # Restore state INTO the new orchestrator
#     new_jiki_instance.resume(loaded_state)
#     # Continue conversation
#     result2 = new_jiki_instance.process("Second user message, continuing context")
# else:
#     # Start fresh if state couldn't be loaded
#     new_jiki_instance = Jiki(...)
#     result2 = new_jiki_instance.process("Second user message, starting fresh")

```

> **Real Value Add:**
> This protocol‑driven design means you can swap in new behaviors—prompt formatting, model sampling, tool transport—without touching Jiki's core. You stay focused on your unique logic instead of plumbing. The state management structure defined by [`IConversationRootManager`](#iconversationrootmanager-1) ensures consistency when your application persists and restores conversation context using the orchestrator's built-in `snapshot` and `resume` capabilities. 