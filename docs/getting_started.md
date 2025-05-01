# Getting Started with Jiki

This guide will walk you through practical steps to get up and running with Jiki quickly.

## Step 1: Installation

Install Jiki using pip or uv:

```bash
# Using pip
pip install jiki

# Or using uv (recommended for faster installation)
uv add jiki
```

## Step 2: Set Up API Key

Jiki uses LiteLLM to connect to various LLM providers. You need to provide an API key for the service you want to use (e.g., Anthropic Claude, OpenAI, Google Gemini).

```bash
# Example for Anthropic Claude
export ANTHROPIC_API_KEY=your_key_here

# Or for OpenAI
export OPENAI_API_KEY=your_key_here

# Or for Google Gemini
export GOOGLE_API_KEY=your_key_here
```

## Step 3: Run Your First Jiki Command

Let's start with a simple command to verify everything works. This uses the Jiki command-line interface (CLI) which wraps the core components.

### Using the CLI

```bash
# Clone the Jiki repository if you don't have it already
# git clone https://github.com/your-organization/jiki.git
# cd jiki # Assuming you are in the root directory of the cloned repo

# Run the interactive CLI using the calculator example
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```

**What's happening here?**
*   `python -m jiki.cli run`: Executes the main Jiki CLI run command.
*   `--auto-discover`: Tells Jiki to automatically ask the tool server for its available tools.
*   `--mcp-script-path servers/calculator_server.py`: Specifies how to communicate with the tool server. In this case, it tells the underlying `JikiClient` to start the Python script `servers/calculator_server.py` as a subprocess and communicate via standard input/output (stdio).

(See the [Architecture Overview](architecture_overview.md) and [Reference](reference.md#jiki-client) for more on the `JikiClient` and communication methods.)

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using default model and discovering tools from servers/calculator_server.py...
[INFO] Tools discovered: add, subtract, multiply, divide
>> 
```

Now try asking a question that requires a tool:
```
>> What is 25 * 16?
```

The CLI will show the LLM's reasoning and the final result after using the `multiply` tool.

**Expected Output (example):**
```
Okay, I can calculate 25 * 16 using the multiply tool.

25 * 16 = 400
```

Exit the session with Ctrl+D, Ctrl+C, or by typing `exit`.

## Step 4: Create Your First Jiki Script

Let's create a simple Python script to use Jiki programmatically:

1. Create a file named `first_jiki.py` with the following content:

```python
from jiki import Jiki

# The Jiki() function is a factory that creates and configures
# the main JikiOrchestrator, the JikiClient for tool communication,
# the LLM model wrapper, and other necessary components.
print("Initializing Jiki...")
orchestrator = Jiki(
    auto_discover_tools=True, # Ask the server for available tools
    mcp_script_path="servers/calculator_server.py" # Connect via stdio
)
print("Initialization complete.")

# Process a query using the orchestrator
print("Processing query...")
result = orchestrator.process("What is 15 * 8?")
print(f"\nResult: {result}")
```

(See the [Architecture Overview](architecture_overview.md) and [Reference](reference.md#factory-function) for more details on the `Jiki()` factory and the `JikiOrchestrator`.)

2. Run the script (make sure you are in the root directory of the Jiki project so it can find `servers/calculator_server.py`):

```bash
python first_jiki.py
```

**Expected Output:**
```
Initializing Jiki...
Initialization complete.
Processing query...

Result: Okay, I can calculate 15 * 8 using the multiply tool.

15 * 8 = 120
```

## Step 5: Get Detailed Results and Traces

Sometimes you need more than just the final answer. You might want to know which tools were called, with what arguments, and what their results were. You can also enable tracing to log the entire interaction flow for debugging.

```python
from jiki import Jiki
import json

# Create an orchestrator with tracing enabled
print("Initializing Jiki with tracing...")
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    trace=True  # This enables the internal TraceLogger
)
print("Initialization complete.")

# Use process_detailed() to get a structured response
print("Processing query for detailed response...")
detailed = orchestrator.process_detailed("What is 75 / 3?")

# The DetailedResponse object contains the final result
# and a list of ToolCall objects.
# (See reference.md#detailed-response for details)
print(f"\nFinal Result: {detailed.result}")

# Access tool calls made during the interaction
print("\nTool Calls:")
if detailed.tool_calls:
    for call in detailed.tool_calls:
        print(f"- Tool: {call.tool_name}")
        print(f"  Arguments: {json.dumps(call.arguments)}") # arguments is a dict
        print(f"  Result: {call.result}") # result is a string
else:
    print("- No tool calls were made.")

# Export the interaction traces captured by the TraceLogger
# (See reference.md#structured-interaction-tracing for details)
trace_file = "my_first_traces.jsonl"
orchestrator.export_traces(trace_file)
print(f"\nTraces exported to {trace_file}")
```

**Expected Output:**
```
Initializing Jiki with tracing...
Initialization complete.
Processing query for detailed response...

Final Result: Okay, I will use the divide tool to calculate 75 / 3.

75 / 3 = 25.0

Tool Calls:
- Tool: divide
  Arguments: {"a": 75, "b": 3}
  Result: 25.0

Traces exported to my_first_traces.jsonl
```
You can inspect the `my_first_traces.jsonl` file to see the detailed interaction log.

## Step 6: Create an Interactive App

Let's build a simple interactive command-line app using the concepts learned so far:

```python
# interactive_calculator.py
from jiki import Jiki
import sys

def main():
    # Create orchestrator (could add trace=True if desired)
    print("Initializing Jiki...")
    try:
        orchestrator = Jiki(
            auto_discover_tools=True,
            mcp_script_path="servers/calculator_server.py"
        )
    except Exception as e:
        print(f"Failed to initialize Jiki: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Interactive loop
    print("\nJiki Calculator App")
    print("Type math questions or 'exit' to quit")
    print("------------------------------------------------")
    
    while True:
        try:
            # Get user input
            query = input("\n>> ")
            if query.lower().strip() in ["exit", "quit"]:
                break
            if not query.strip(): # Handle empty input
                continue
                
            # Process query
            print("Thinking...") # Provide feedback
            result = orchestrator.process(query)
            print(f"\n{result}") # Add newline for better formatting
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}", file=sys.stderr)
    
    print("\nGoodbye!")
    # If tracing was enabled, could call orchestrator.export_traces() here

if __name__ == "__main__":
    main()
```

Run this interactive app:

```bash
python interactive_calculator.py
```

## Step 7: Using Custom Tool Definitions

Instead of relying on auto-discovery, you can provide Jiki with tool definitions directly, often from a JSON file. This is useful if you want to use a specific subset of tools or if the server doesn't support discovery.

1. Create a file named `my_tools.json`. The structure should match the schema expected by Jiki (see `jiki.tools.tool.Tool` in `reference.md#tools-enabling-actions`).

```json
[
  {
    "tool_name": "multiply",
    "description": "Multiplies two numbers.",
    "arguments": {
      "a": { "type": "number", "description": "First number" },
      "b": { "type": "number", "description": "Second number" }
    },
    "required": ["a", "b"]
  },
  {
    "tool_name": "add",
    "description": "Adds two numbers.",
    "arguments": {
      "a": { "type": "number", "description": "First number" },
      "b": { "type": "number", "description": "Second number" }
    },
    "required": ["a", "b"]
  }
]
```
*Note: This example only defines `multiply` and `add`. The `calculator_server.py` actually provides more.* 

2. Create a script named `custom_tools_example.py`:

```python
from jiki import Jiki

# Create an orchestrator loading tools from our file
print("Initializing Jiki with custom tools...")
orchestrator = Jiki(
    tools="my_tools.json",  # Path to the tools file
    auto_discover_tools=False,  # IMPORTANT: Disable auto-discovery
    mcp_script_path="servers/calculator_server.py" # Still need to connect
)
print("Initialization complete. Tools loaded:", 
      [tool.get('tool_name') for tool in orchestrator.tools_config])

# Process a query. The LLM will only know about 'multiply' and 'add'.
print("\nProcessing query...")
result = orchestrator.process("Calculate 42 + 17")
print(f"\nResult: {result}")

print("\nTrying a tool not in our JSON...")
result_subtract = orchestrator.process("Calculate 100 - 5")
print(f"\nResult (subtract): {result_subtract}") # LLM shouldn't use subtract tool
```

3. Run the script:

```bash
python custom_tools_example.py
```
Notice that the LLM successfully uses the `add` tool (which was in `my_tools.json`) but likely tries to answer the subtraction question without using a tool, as `subtract` wasn't provided in the custom definitions.

## Step 8: Using HTTP Transport (SSE)

If your tool server is running as a persistent web service (e.g., using `fastmcp run --transport sse`), you can connect Jiki to it over HTTP using Server-Sent Events (SSE).

1. Start the server with SSE transport (in a separate terminal):

```bash
fastmcp run servers/calculator_server.py --transport sse --port 8000
```

2. Create a script named `http_example.py`:

```python
from jiki import Jiki

# Create an orchestrator using HTTP/SSE transport
print("Initializing Jiki with SSE transport...")
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_mode="sse",  # Use Server-Sent Events transport
    mcp_url="http://localhost:8000"  # URL of the running MCP server
    # mcp_script_path is NOT needed when using mcp_mode="sse"
)
print("Initialization complete.")

# Process a query
print("\nProcessing query...")
result = orchestrator.process("What is 125 / 5?")
print(f"\nResult: {result}")
```
(This configures the underlying `JikiClient` to use `fastmcp`'s `SSETransport`. See `reference.md#mcp-client-transports`.)

3. Run the script (while the server is running in the other terminal):

```bash
python http_example.py
```

## Next Steps

Now that you're familiar with the basics, you can:

- Explore the [**Architecture Overview**](architecture_overview.md) to understand how Jiki components fit together.
- Dive into the [**API Reference**](reference.md) for detailed documentation on classes and functions.
- Learn about the [**Core Interfaces**](core_interfaces.md) if you plan to customize or extend Jiki.
- Check out the [**CLI Reference**](cli_reference.md) for advanced command-line options.
- Experiment with more [**Code Examples**](code_examples.md).
- Try the included [**example scripts**](../examples/) for more usage patterns.

If you're ready to build something more complex, see our [**tutorials**](../tutorials/) for specific use cases. 