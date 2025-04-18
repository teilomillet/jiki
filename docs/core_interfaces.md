# Core Interfaces in Jiki

Jiki is designed around a few simple, pluggable abstractions. You can swap in your own implementations without touching the orchestrator core.

## IToolClient

Defines how Jiki discovers and calls external tools.

```python
class IToolClient(Protocol):
    async def discover_tools(self) -> List[Dict[str, Any]]:
        ...

    async def execute_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        ...
```

*Implemented by* `EnhancedMCPClient` in `jiki/mcp_client.py`.

---

## IMCPClient

Extends `IToolClient` to include resources and roots management (per MCP spec).

```python
class IMCPClient(IToolClient, IResourceManager, Protocol):
    async def list_roots(self) -> List[Dict[str, Any]]: ...
    async def send_roots_list_changed(self) -> None: ...
```

*Used for* tool discovery/invocation, resource listing/reading, and notifying root changes.

---

## IPromptBuilder

Abstracts prompt construction, so you can customize how tools and resources are exposed.

```python
class IPromptBuilder(Protocol):
    def create_available_tools_block(
        self, tools_config: List[Dict[str, Any]]
    ) -> str: ...

    def create_available_resources_block(
        self, resources_config: List[Dict[str, Any]]
    ) -> str: ...

    def build_initial_prompt(
        self,
        user_input: str,
        tools_config: List[Dict[str, Any]],
        resources_config: Optional[List[Dict[str, Any]]] = None,
    ) -> str: ...
```

*Default implementation* lives in `jiki/prompts/DefaultPromptBuilder`.

---

## ISamplerConfig

Controls LLM sampling parameters (temperature, top‑p, etc.).

```python
class ISamplerConfig(Protocol):
    temperature: float
    top_p: float
    max_tokens: Optional[int]
    stop: Optional[List[str]]

    def to_dict(self) -> Dict[str, Any]: ...
```

*Concrete type* is `SamplerConfig` in `jiki/sampling.py`.

---

## IResourceManager & IRootManager

- **IResourceManager** (in `jiki/resources`)
  - `list_resources()` and `read_resource(uri)` per MCP resources spec.

- **IRootManager** (in `jiki/roots`)
  - `list_roots()` and `send_roots_list_changed()` per MCP roots spec.


With these interfaces, the core orchestrator never hardcodes transport, tool‑call, or prompt details—making it easy to extend or replace any piece without rewriting Jiki itself. 

---

## How They Work Together

`JikiOrchestrator` ties everything in a simple pipeline:

1. **Prompt Construction**: `IPromptBuilder` builds the system prompt (tools, resources, user query).
2. **Token Streaming**: `LiteLLMModel` streams tokens through `generate_and_intercept`, catching `<mcp_tool_call>` blocks.
3. **Parsing & Validation**: `parse_tool_call_content` parses the JSON call, and `validate_tool_call` checks against the declared schema.
4. **Tool Invocation**: `IMCPClient` executes the tool call (MCP Protocol) and returns the result.
5. **Injection & Continuation**: The result is injected back into the conversation, and streaming continues until the answer is complete.

This flow ensures each piece—prompt, model, parsing, validation, transport—is swappable, keeping the core orchestrator lean.

---

## Extending Jiki: Plug & Play

All core behaviors are defined via protocols, so you can customize exactly what you need.

### 1. Custom Prompt Builder

```python
from jiki.prompts.prompt_builder import DefaultPromptBuilder
from jiki import JikiOrchestrator
from jiki.models.litellm import LiteLLMModel
from jiki.mcp_client import EnhancedMCPClient

class FancyPromptBuilder(DefaultPromptBuilder):
    def build_initial_prompt(self, user_input, tools_config, resources_config=None):
        header = "### 🎩 Welcome to Fancy Jiki!\n"
        return header + super().build_initial_prompt(user_input, tools_config, resources_config)

orch = JikiOrchestrator(
    model=LiteLLMModel("gpt-4"),
    mcp_client=EnhancedMCPClient(transport_type="sse", script_path="http://localhost:8000/mcp"),
    tools_config=[...],
    prompt_builder=FancyPromptBuilder()
)
```

### 2. Custom Sampler Configuration

```python
from jiki import create_jiki
from jiki.sampling import ISamplerConfig

class MySampler(ISamplerConfig):
    temperature = 0.2
    top_p = 0.9
    max_tokens = 100
    stop = ['']

    def to_dict(self):
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stop": self.stop
        }

jiki = create_jiki(
    model="gpt-4",
    sampler_config=MySampler()
)
```

### 3. Custom Tool Client (e.g., for Tests)

```python
from jiki.tool_client import IToolClient

class StubToolClient(IToolClient):
    async def discover_tools(self):
        return [{"tool_name":"echo","description":"Echoes input","arguments":{"text":{"type":"string"}}}]
    async def execute_tool_call(self, name, args):
        return args.get('text', '')

# Manually instantiate orchestrator with a stub client
from jiki import JikiOrchestrator
from jiki.models.litellm import LiteLLMModel

orch = JikiOrchestrator(
    model=LiteLLMModel("gpt-4"),
    mcp_client=StubToolClient(),
    tools_config=[{"tool_name":"echo","description":"","arguments":{"text":{"type":"string"}}}]
)
```

### 4. Custom Root Manager

```python
from jiki.roots.conversation_root_manager import IConversationRootManager

class DBRootManager(IConversationRootManager):
    def snapshot(self): ...  # save to your DB
    def resume(self, snapshot): ...  # load from your DB

from jiki import create_jiki
jiki = create_jiki(
    conversation_root_manager=DBRootManager()
)
```

> **Real Value Add:**
> This protocol‑driven design means you can swap in new behaviors—prompt formatting, model sampling, tool transport, persistence—without touching Jiki's core. You stay focused on your unique logic instead of plumbing. 