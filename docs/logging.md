# Logging in Jiki

Jiki captures both fine‑grained conversation events and full interaction traces, making debugging, auditing, and training data generation easy.

---

## Key Components

### TraceLogger

Located in `jiki/logging.py`, `TraceLogger` records two types of logs:

- **Events**: Individual conversation messages (user, system, assistant, tool calls).
- **Complete Traces**: Full MCP sessions, including JSON‑RPC `initialize`/`initialized` handshakes, tool calls, results, and any notifications.

```python
from jiki.logging import TraceLogger

# Create a logger, saving traces under 'my_traces' directory
logger = TraceLogger(log_dir="my_traces")
```

### record_conversation_event

Utility in `jiki/utils/logging.py` that the orchestrator uses to:

1. Append each message to `orchestrator.conversation_history`.
2. Call `logger.log_event(...)` if a logger is provided.

```python
from jiki.utils.logging import record_conversation_event

# history: List[Dict[str,Any]] maintained by the orchestrator
# logger: optional TraceLogger instance
record_conversation_event(history, role="user", content="Hi!", logger)
```

---

## Automatic Setup via `create_jiki`

The easiest way to enable logging is with the factory function:

```python
from jiki import create_jiki

# Enable tracing and save to './traces'
jiki = create_jiki(trace=True, trace_dir="traces")
```

By default, Jiki will:
- Inject a `TraceLogger` into the orchestrator.
- Log every conversation event and complete interaction.

---

## Retrieving & Saving Logs

### Access Conversation History

```python
# Synchronous or async orchestration
result = jiki.process("Hello!")

# View raw events
for event in jiki.conversation_history:
    print(event)
```

### Export Complete Traces

```python
# Save all complete traces to a JSON file (default .json or .jsonl based on extension)
jiki.export_traces("my_traces.jsonl")
```

- `.export_traces()` uses `TraceLogger.save_all_traces()` under the hood.
- Filenames automatically include timestamps for uniqueness.

---

## Advanced Usage

- **Manual Logging**: Call `logger.log_event(...)` or `logger.log_complete_trace(...)` directly for custom events.
- **Custom Loggers**: Implement the same interface (`log_event`, `log_complete_trace`) and pass into `JikiOrchestrator`.

```python
from jiki.orchestrator import JikiOrchestrator

my_custom_logger = MyLogger()
orch = JikiOrchestrator(model, client, tools, logger=my_custom_logger)
```

With Jiki's structured logging, you get transparent, pluggable, and timestamped traces of every step in your LLM workflows. 