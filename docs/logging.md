# Logging & Tracing in Jiki

Jiki provides structured logging of interactions, which is invaluable for debugging, analysis, and potentially fine-tuning models.

## Overview

The primary mechanism is the `TraceLogger` class, which:
- Captures events like user input, LLM prompts, tool calls, tool results, and final LLM responses.
- Stores these events in memory.
- Can persist the traces to disk in JSON or JSON Lines (`.jsonl`) format.

Each interaction or "turn" typically generates a trace dictionary containing:
- `conversation_id`: A unique ID for the conversation session.
- `turn_id`: A unique ID for the specific turn within the conversation.
- `events`: A list of dictionaries, each representing a step in the turn (e.g., `user_input`, `llm_prompt`, `tool_call`, `tool_result`, `llm_response`).
- `metadata`: Optional additional context.

## Enabling Tracing

Tracing is **enabled by default** when using the `Jiki()` factory function (`trace=True`).

```python
from jiki import Jiki

# Tracing enabled, logs saved to ./interaction_traces/
jiki_instance = Jiki()

# Tracing enabled, logs saved to ./my_custom_traces/
jiki_instance_custom = Jiki(trace=True, trace_dir="my_custom_traces")

# Tracing disabled
jiki_instance_no_trace = Jiki(trace=False)
```

## Accessing Traces Programmatically

If you need to access traces within your application, the `JikiOrchestrator` (returned by `Jiki()`) provides methods via attached helpers:

```python
from jiki import Jiki

# Tracing needs to be enabled for logger to be created
jiki_instance = Jiki(trace=True, trace_dir="traces")

# Process some interactions...
jiki_instance.process("Hello!")
jiki_instance.process("What is 1+1 using the calculator?")

# Get all traces from the current session
all_traces = jiki_instance.get_traces() # Returns List[Dict]

# Export traces to a file (optional, run_ui does this on exit)
# jiki_instance.export_traces("session_log.jsonl") 
```

## Automatic Setup via `Jiki()`

When you use `Jiki(trace=True, ...)`, it automatically creates and configures a `TraceLogger` instance and passes it to the `JikiOrchestrator`. Helper methods like `get_traces()` and `export_traces()` are then attached to the orchestrator instance for convenience.

## Manual Setup (Advanced)

For more control, you can instantiate `TraceLogger` and `JikiOrchestrator` manually:

```python
from jiki.logging import TraceLogger
from jiki.orchestrator import JikiOrchestrator
from jiki.models.litellm import LiteLLMModel
from jiki.mcp_client import JikiClient
from jiki.serialization.helpers import _attach_helper_methods

# 1. Create logger
logger = TraceLogger(trace_dir="manual_traces")

# 2. Create other components (model, MCP client, etc.)
model = LiteLLMModel("anthropic/claude-3-haiku-20240307")
mcp_client = JikiClient(connection_info={"type": "stdio", "script_path": "servers/calculator_server.py"}, logger=logger)

# 3. Create orchestrator, passing the logger
orchestrator = JikiOrchestrator(
    model=model,
    mcp_client=mcp_client,
    tools_config=[...], # Load or define tools manually
    logger=logger
)

# 4. (Optional) Attach helper methods for convenience
_attach_helper_methods(orchestrator, logger)

# Now use the orchestrator
# orchestrator.process("...")
# traces = orchestrator.get_traces() 
# orchestrator.export_traces("manual_run.jsonl")
```

## Trace Format Example (`.jsonl`)

```json
{"conversation_id": "conv_abc", "turn_id": "turn_1", "events": [{"type": "user_input", "content": "What is 5+7?"}, {"type": "llm_prompt", "content": "...", "model": "..."}, {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "5+7"}}, {"type": "tool_result", "tool_name": "calculator", "content": "12"}, {"type": "llm_response", "content": "5 + 7 is 12."}], "metadata": {}}
{"conversation_id": "conv_abc", "turn_id": "turn_2", "events": [...]} 
```

This structured format makes it easy to parse logs and analyze the interaction flow between the user, LLM, and tools. 