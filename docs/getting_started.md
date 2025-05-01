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

Jiki uses LiteLLM to connect to various LLM providers. The default is Anthropic's Claude, but you can use OpenAI, Gemini, or others:

```bash
# For Anthropic Claude (default)
export ANTHROPIC_API_KEY=your_key_here

# Or for OpenAI
export OPENAI_API_KEY=your_key_here

# Or for Google Gemini
export GOOGLE_API_KEY=your_key_here
```

## Step 3: Run Your First Jiki Command

Let's start with a simple command to verify everything works:

### Using the CLI

```bash
# Clone the Jiki repository if you don't have it already
git clone https://github.com/your-organization/jiki.git
cd jiki

# Run the interactive CLI using the calculator example
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```

**Expected Output:**
```
[INFO] Starting interactive session...
[INFO] Using default model and discovering tools from servers/calculator_server.py...
[INFO] Tools discovered: add, subtract, multiply, divide
>> 
```

Now try asking a question:
```
>> What is 25 * 16?
```

**Expected Output:**
```
To calculate 25 * 16, I'll use the multiply tool.

25 * 16 = 400
```

Exit the session with Ctrl+D, Ctrl+C, or by typing `exit`.

## Step 4: Create Your First Jiki Script

Let's create a simple Python script to use Jiki programmatically:

1. Create a file named `first_jiki.py` with the following content:

```python
from jiki import Jiki

# Create an orchestrator with auto-discovery
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Process a query
result = orchestrator.process("What is 15 * 8?")
print(f"Result: {result}")
```

2. Run the script:

```bash
python first_jiki.py
```

**Expected Output:**
```
Result: To calculate 15 * 8, I'll use the multiply tool.

15 * 8 = 120
```

## Step 5: Get Detailed Results

Enhance your script to get detailed information about tool calls:

```python
from jiki import Jiki
import json

# Create an orchestrator
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    trace=True  # Enable tracing
)

# Get detailed response
detailed = orchestrator.process_detailed("What is 75 / 3?")

# Access the string result
print(f"Result: {detailed.result}")

# Access tool calls
print("\nTool Calls:")
for call in detailed.tool_calls:
    print(f"Tool: {call.tool_name}")
    print(f"Arguments: {json.dumps(call.arguments)}")
    print(f"Result: {call.result}")

# Export traces for debugging
orchestrator.export_traces("my_first_traces.jsonl")
print("\nTraces exported to my_first_traces.jsonl")
```

**Expected Output:**
```
Result: To calculate 75 / 3, I'll use the divide tool.

75 / 3 = 25

Tool Calls:
Tool: divide
Arguments: {"a": 75, "b": 3}
Result: 25.0

Traces exported to my_first_traces.jsonl
```

## Step 6: Create an Interactive App

Let's build a simple interactive command-line app:

```python
from jiki import Jiki
import sys

def main():
    # Create orchestrator
    print("Initializing Jiki...")
    orchestrator = Jiki(
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        trace=True
    )
    
    # Interactive loop
    print("\nJiki Calculator App")
    print("Type math questions or 'exit' to quit")
    print("------------------------------------------------")
    
    while True:
        try:
            # Get user input
            query = input("\n>> ")
            if query.lower() in ["exit", "quit"]:
                break
                
            # Process query
            result = orchestrator.process(query)
            print(result)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
    
    print("\nExiting. Traces saved to interaction_traces/")

if __name__ == "__main__":
    main()
```

Run this interactive app:

```bash
python interactive_calculator.py
```

## Step 7: Using Custom Tools

If you have your own tool definitions, you can use them instead of auto-discovery:

1. Create a file named `my_tools.json` with the following content:

```json
[
  {
    "name": "calculator",
    "description": "A simple calculator that can evaluate math expressions",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "The math expression to evaluate"
        }
      },
      "required": ["expression"]
    }
  }
]
```

2. Create a script named `custom_tools_example.py`:

```python
from jiki import Jiki

# Create an orchestrator with custom tools
orchestrator = Jiki(
    tools="my_tools.json",  # Use our custom tools file
    auto_discover_tools=False,  # Disable auto-discovery
    mcp_script_path="servers/calculator_server.py"
)

# Process a query
result = orchestrator.process("Calculate 42 + 17")
print(f"Result: {result}")
```

3. Run the script:

```bash
python custom_tools_example.py
```

## Step 8: Using HTTP Transport

If your tool server is running as a web service, you can connect via HTTP:

1. Start the server with SSE transport (in a separate terminal):

```bash
fastmcp run servers/calculator_server.py --transport sse --port 8000
```

2. Create a script named `http_example.py`:

```python
from jiki import Jiki

# Create an orchestrator using HTTP transport
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_mode="sse",  # Server-Sent Events transport
    mcp_url="http://localhost:8000"  # URL to the server
)

# Process a query
result = orchestrator.process("What is 125 / 5?")
print(f"Result: {result}")
```

3. Run the script:

```bash
python http_example.py
```

## Next Steps

Now that you're familiar with the basics, you can:

- Try more examples by running the [example scripts](../examples/) included with Jiki
- Explore the [CLI Reference](cli_reference.md) for advanced command-line options
- Check out the [Code Examples](code_examples.md) for more detailed usage patterns
- Learn about [core concepts](core_interfaces.md) if you want to extend Jiki

If you're ready to build something more complex, see our [tutorials](../tutorials/) for specific use cases. 