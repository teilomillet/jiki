# Quickstart: Getting Started with JikiOrchestrator

Just a few lines of code and you're up and running:

```python
from jiki import create_jiki

# 1. Create the orchestrator with default settings
jiki = create_jiki()

# 2. Ask a simple question synchronously
answer = jiki.process("What is 2 + 3?")
print(answer)  # → 5

# 3. Or request a detailed response with tool call trace
detailed = jiki.process_detailed("Multiply 7 by 6")
print(detailed.result)             # → 42
for call in detailed.tool_calls:
    print(f"Tool: {call.tool}, Args: {call.arguments}, Result: {call.result}")
```

> **Tip:** You can also run `jiki process "Your question"` from the CLI or build your own interface using `jiki.run_ui()`.

---

## Under the Hood: Core Interfaces

Behind this simple API, `JikiOrchestrator` depends only on minimal abstractions:

- **Prompt Builder** (`IPromptBuilder`)
- **MCP Client** (`IMCPClient`)
- **Tool Validation** (`parse_tool_call_content`, `validate_tool_call`)
- **Utilities** (context trimming, token counting, output cleaning)

All streaming, JSON‑tag interception, schema validation, and tool invocation happen behind the scenes so you can focus on your application logic. 