# Jiki Code Examples

This page provides a collection of complete, runnable Python scripts that demonstrate how to use Jiki. The examples are organized progressively from basic to advanced.

## Basic Examples

### Simple Query Processing

This basic example shows how to create a Jiki orchestrator and process a single query using the calculator tool server.

```python
#!/usr/bin/env python3
"""
Basic Jiki Example: Simple Query Processing
------------------------------------------
This example demonstrates:
1. Creating a basic Jiki orchestrator
2. Processing a single query
3. Printing the result
"""

from jiki import Jiki

# Create a Jiki orchestrator with auto-discovery
# The calculator_server.py script contains tools for basic arithmetic
orchestrator = Jiki(
    auto_discover_tools=True,  # Discover tools from the MCP server
    mcp_script_path="servers/calculator_server.py",  # Path to the MCP server script
    mcp_mode="stdio"  # Use stdio transport (default)
)

# Process a query that requires calculation
result = orchestrator.process("What is 25 * 16?")

# Print the result
print(f"Result: {result}")

# Expected output:
# Result: To calculate 25 * 16, I'll use the multiply tool.
#
# 25 * 16 = 400
```

### Interactive CLI

This example shows how to create an interactive CLI session programmatically.

```python
#!/usr/bin/env python3
"""
Basic Jiki Example: Interactive CLI
----------------------------------
This example demonstrates:
1. Creating a Jiki orchestrator with auto-discovery
2. Launching the built-in interactive CLI
"""

from jiki import Jiki

# Create a Jiki orchestrator with auto-discovery and tracing
orchestrator = Jiki(
    auto_discover_tools=True,  # Discover tools from the MCP server
    mcp_script_path="servers/calculator_server.py",  # Path to the MCP server script
    trace=True  # Enable tracing for the session
)

# Launch the interactive CLI
print("Starting interactive Jiki session. Type 'exit' to quit.")
orchestrator.run_ui(frontend='cli')
print("Session ended.")

# The run_ui method will:
# 1. Start an interactive session
# 2. Prompt the user for input with ">>"
# 3. Process each query and display the result
# 4. Exit when the user inputs "exit" or presses Ctrl+D
# 5. Automatically save traces when the session ends
```

### Multiple Queries in Sequence

This example demonstrates processing multiple queries in sequence within the same session.

```python
#!/usr/bin/env python3
"""
Basic Jiki Example: Multiple Queries in Sequence
----------------------------------------------
This example demonstrates:
1. Processing multiple queries in sequence
2. Maintaining conversation context between queries
"""

from jiki import Jiki

# Create a Jiki orchestrator
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Process first query
print("Query 1: What is 10 + 5?")
result1 = orchestrator.process("What is 10 + 5?")
print(f"Result 1: {result1}")

# Process second query, which can reference the first one
print("\nQuery 2: And if we multiply that by 3?")
result2 = orchestrator.process("And if we multiply that by 3?")
print(f"Result 2: {result2}")

# Process third query
print("\nQuery 3: What's the square root of 144?")
result3 = orchestrator.process("What's the square root of 144?")
print(f"Result 3: {result3}")

# Expected output:
# Query 1: What is 10 + 5?
# Result 1: To calculate 10 + 5, I'll use the add tool.
#
# 10 + 5 = 15
#
# Query 2: And if we multiply that by 3?
# Result 2: To calculate 15 * 3, I'll use the multiply tool.
#
# 15 * 3 = 45
#
# Query 3: What's the square root of 144?
# Result 3: I need to find the square root of 144...
```

## Intermediate Examples

### Detailed Response Processing

This example shows how to get detailed information about the processing of a query, including tool calls and traces.

```python
#!/usr/bin/env python3
"""
Intermediate Example: Detailed Response Processing
------------------------------------------------
This example demonstrates:
1. Using process_detailed() to get structured data about tool calls
2. Analyzing the detailed response object
3. Working with tool call data
"""

from jiki import Jiki
import json

# Create Jiki orchestrator with tracing enabled
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    trace=True  # Enable tracing to capture tool calls and other events
)

# Process a query using process_detailed() instead of process()
# This returns a DetailedResponse object rather than just a string
print("Processing query: What is 42 / 6?")
detailed_response = orchestrator.process_detailed("What is 42 / 6?")

# Access the final result (same as what process() would return)
print(f"\nResult string: {detailed_response.result}")

# Access structured data about tool calls
print("\nTool calls:")
for i, call in enumerate(detailed_response.tool_calls):
    print(f"  Tool call #{i+1}:")
    print(f"    Tool name: {call.tool_name}")
    print(f"    Arguments: {json.dumps(call.arguments)}")
    print(f"    Result: {call.result}")

# Access traces (if available)
if detailed_response.traces:
    print("\nTrace events:")
    for i, trace in enumerate(detailed_response.traces):
        print(f"  Event #{i+1}: {trace['type']}")

# Export traces to a file
orchestrator.export_traces("detailed_example_traces.jsonl")
print("\nTraces exported to detailed_example_traces.jsonl")

# Expected output will include:
# - The final text response
# - Structured information about the divide tool call
# - Trace events if tracing was enabled
```

### Custom Tools Configuration

This example demonstrates using custom tool definitions instead of auto-discovery.

```python
#!/usr/bin/env python3
"""
Intermediate Example: Custom Tools Configuration
----------------------------------------------
This example demonstrates:
1. Using custom tool definitions from a JSON file
2. Disabling auto-discovery
3. Working with predefined tools
"""

from jiki import Jiki
import json
import os

# First, let's create a custom tools definition file if it doesn't exist
tools_file = "custom_tools.json"
if not os.path.exists(tools_file):
    custom_tools = [
        {
            "name": "calculator",
            "description": "A simple calculator tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    ]
    with open(tools_file, "w") as f:
        json.dump(custom_tools, f, indent=2)
    print(f"Created custom tools file: {tools_file}")

# Create Jiki orchestrator with custom tools
orchestrator = Jiki(
    tools=tools_file,  # Use tools defined in the JSON file
    auto_discover_tools=False,  # Disable auto-discovery
    mcp_script_path="servers/calculator_server.py"
)

# Process a query using the custom tools
result = orchestrator.process("Can you calculate 15 * 8?")
print(f"Result: {result}")

# Clean up the temporary file
if os.path.exists(tools_file):
    os.remove(tools_file)
    print(f"Removed temporary file: {tools_file}")

# Expected output:
# Created custom tools file: custom_tools.json
# Result: To calculate 15 * 8, I'll use the calculator tool...
# Removed temporary file: custom_tools.json
```

### HTTP Transport (SSE)

This example demonstrates connecting to an MCP server via HTTP using Server-Sent Events (SSE).

```python
#!/usr/bin/env python3
"""
Intermediate Example: HTTP Transport (SSE)
----------------------------------------
This example demonstrates:
1. Connecting to an MCP server via HTTP using SSE transport
2. Working with remote tool servers
3. Handling connection errors gracefully

Note: This example requires a running MCP server with SSE transport.
You can start one using: fastmcp run servers/calculator_server.py --transport sse --port 8000
"""

from jiki import Jiki
import sys
import time
import subprocess
import os
import signal
import atexit

# Function to start the MCP server in the background
def start_server():
    try:
        # Check if FastMCP is installed
        subprocess.run(["fastmcp", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Start the server
        print("Starting MCP server with SSE transport on port 8000...")
        server_process = subprocess.Popen(
            ["fastmcp", "run", "servers/calculator_server.py", "--transport", "sse", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Register cleanup function
        atexit.register(lambda: os.kill(server_process.pid, signal.SIGTERM) if server_process.poll() is None else None)
        
        # Wait for server to start
        time.sleep(2)
        return server_process
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: FastMCP not installed or calculator_server.py not found.")
        print("Install FastMCP: pip install fastmcp")
        print("Or start the server manually: fastmcp run servers/calculator_server.py --transport sse --port 8000")
        return None

# Start the server
server_process = start_server()

# Create Jiki orchestrator with SSE transport
try:
    orchestrator = Jiki(
        auto_discover_tools=True,
        mcp_mode="sse",  # Use SSE transport instead of stdio
        mcp_url="http://localhost:8000"  # URL of the MCP server
    )
    
    # Process a query
    print("Processing query using SSE transport...")
    result = orchestrator.process("What is 75 / 3?")
    print(f"Result: {result}")
    
except Exception as e:
    print(f"Error connecting to MCP server: {e}")
    print("Make sure the server is running with: fastmcp run servers/calculator_server.py --transport sse --port 8000")
    sys.exit(1)

# Clean up
if server_process and server_process.poll() is None:
    print("Stopping MCP server...")
    os.kill(server_process.pid, signal.SIGTERM)
    server_process.wait()

print("Example completed successfully.")

# Expected output:
# Starting MCP server with SSE transport on port 8000...
# Processing query using SSE transport...
# Result: To calculate 75 / 3, I'll use the divide tool.
#
# 75 / 3 = 25
# Stopping MCP server...
# Example completed successfully.
```

## Advanced Examples

### Custom Sampling Configuration

This example demonstrates customizing LLM sampling parameters to control response generation.

```python
#!/usr/bin/env python3
"""
Advanced Example: Custom Sampling Configuration
---------------------------------------------
This example demonstrates:
1. Creating and using a SamplerConfig to control LLM behavior
2. Adjusting temperature, max tokens, and other parameters
3. Comparing the effects of different sampling parameters
"""

from jiki import Jiki, SamplerConfig

# Create a default Jiki orchestrator
default_orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Create a Jiki orchestrator with custom sampling parameters
# - Lower temperature (0.1) for more deterministic responses
# - Limited max_tokens (50) for shorter responses
custom_sampler = SamplerConfig(
    temperature=0.1,  # Lower temperature = more deterministic
    top_p=0.9,        # Top probability threshold
    max_tokens=50,    # Maximum response length
    # Other parameters could include:
    # frequency_penalty=0.0,
    # presence_penalty=0.0
)

custom_orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    sampler_config=custom_sampler  # Use our custom sampling configuration
)

# A creative query that could have varied responses
query = "Tell me a short story about a calculator."

# Process with default settings
print("==== Response with Default Sampling ====")
default_result = default_orchestrator.process(query)
print(default_result)

# Process with custom sampling settings
print("\n==== Response with Custom Sampling (temp=0.1, max_tokens=50) ====")
custom_result = custom_orchestrator.process(query)
print(custom_result)

# Print token counts for comparison
default_tokens = len(default_result.split())
custom_tokens = len(custom_result.split())

print(f"\n==== Comparison ====")
print(f"Default response word count: {default_tokens}")
print(f"Custom response word count: {custom_tokens}")

# Expected output will show:
# - The default response will likely be longer and potentially more creative
# - The custom response will be shorter (due to max_tokens=50) and more focused/deterministic
```

### Conversation State Management

This example demonstrates implementing a conversation state manager to save and resume conversation contexts.

```python
#!/usr/bin/env python3
"""
Advanced Example: Conversation State Management
---------------------------------------------
This example demonstrates:
1. Implementing a custom ConversationRootManager
2. Saving conversation state to a file
3. Resuming a conversation from saved state
"""

from jiki import Jiki
from jiki.roots.conversation_root_manager import IConversationRootManager
import json
import os
from typing import Any, Dict

# Implement a simple file-based conversation state manager
class FileRootManager(IConversationRootManager):
    """Simple file-based implementation of IConversationRootManager"""
    
    def __init__(self, filepath: str = "conversation_state.json"):
        self.filepath = filepath
        self._state = None
    
    def snapshot(self) -> Any:
        """Save the current conversation state to a dictionary"""
        print(f"Snapshotting conversation state...")
        # In a real implementation, this would contain actual conversation data
        self._state = {
            "version": "1.0",
            "timestamp": "2023-07-22T15:30:00Z",
            "conversation_id": "example-conversation",
            "messages": [
                # Would contain actual messages in a real implementation
            ]
        }
        
        # Save to file
        with open(self.filepath, "w") as f:
            json.dump(self._state, f, indent=2)
        
        return self._state
    
    def resume(self, snapshot: Any) -> None:
        """Resume from a saved state"""
        print(f"Resuming conversation from state: {type(snapshot)}")
        self._state = snapshot
        
        # In a real implementation, you would restore the conversation context here
        # This might involve setting message history, etc.

# Demonstration

# Create a file root manager
root_manager = FileRootManager("example_conversation.json")

# First orchestrator instance with root manager
print("Creating first orchestrator instance...")
orchestrator1 = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    conversation_root_manager=root_manager,
    trace=True
)

# Process a query in the first session
print("\nFirst session - Processing query: My favorite number is 42")
orchestrator1.process("My favorite number is 42")

# Save the conversation state
state = root_manager.snapshot()
print(f"Saved conversation state to: {root_manager.filepath}")

# Create a second orchestrator instance
print("\nCreating second orchestrator instance...")
orchestrator2 = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py",
    conversation_root_manager=root_manager,
    trace=True
)

# Resume the conversation
root_manager.resume(state)

# Process a follow-up query that references the previous conversation
print("\nSecond session - Processing query: What is my favorite number times 2?")
result = orchestrator2.process("What is my favorite number times 2?")
print(f"Result: {result}")

# Clean up
if os.path.exists(root_manager.filepath):
    os.remove(root_manager.filepath)
    print(f"\nRemoved state file: {root_manager.filepath}")

# Expected output:
# The second orchestrator should be able to recall that the favorite number is 42
# and calculate 42 * 2 = 84
```

### Direct MCP Client Access

This example demonstrates direct interaction with the MCP client for low-level operations.

```python
#!/usr/bin/env python3
"""
Advanced Example: Direct MCP Client Access
----------------------------------------
This example demonstrates:
1. Accessing the MCP client directly from the orchestrator
2. Listing and reading resources
3. Making direct tool calls without involving the LLM
"""

from jiki import Jiki
import json

# Create a Jiki orchestrator
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Get a reference to the MCP client
mcp_client = orchestrator.mcp_client
print("Obtained direct access to the MCP client")

# List available tools directly
print("\n== Available Tools ==")
tools = mcp_client.list_tools()
for tool in tools:
    print(f"- {tool['name']}: {tool['description']}")
    params = tool.get('parameters', {}).get('properties', {})
    if params:
        print("  Parameters:")
        for param_name, param_info in params.items():
            print(f"  - {param_name}: {param_info.get('type')} ({param_info.get('description', 'No description')})")

# List available resources
print("\n== Available Resources ==")
resources = mcp_client.list_resources()
for resource in resources:
    print(f"- {resource}")

# Read a resource (if any are available)
if resources:
    resource_uri = resources[0]
    print(f"\n== Reading Resource: {resource_uri} ==")
    content = mcp_client.read_resource(resource_uri)
    print(f"Content: {content}")

# Execute a tool call directly
print("\n== Direct Tool Call: multiply ==")
try:
    result = mcp_client.execute_tool_call("multiply", {"a": 12, "b": 5})
    print(f"Result of 12 * 5 = {result}")
except Exception as e:
    print(f"Error executing tool call: {e}")

# Another tool call example
print("\n== Direct Tool Call: add ==")
try:
    result = mcp_client.execute_tool_call("add", {"a": 123, "b": 456})
    print(f"Result of 123 + 456 = {result}")
except Exception as e:
    print(f"Error executing tool call: {e}")

print("\nExample completed successfully")

# Expected output:
# - List of available tools with their descriptions and parameters
# - List of available resources (e.g., config://calculator)
# - Content of the first resource (if any)
# - Result of the direct tool calls (12 * 5 = 60, 123 + 456 = 579)
```

## Complete Application Examples

### Custom Web Chatbot

This example demonstrates how to integrate Jiki into a simple web application using Flask.

```python
#!/usr/bin/env python3
"""
Complete Application Example: Custom Web Chatbot
----------------------------------------------
This example demonstrates:
1. Integrating Jiki with a Flask web application
2. Implementing a JSON API for chat interactions
3. Managing conversation state per user session

Requirements:
- Flask: pip install flask
- Jiki: pip install jiki
- FastMCP: pip install fastmcp
"""

from flask import Flask, request, jsonify, session
from jiki import Jiki, SamplerConfig
import uuid
import threading
import subprocess
import time
import os
import signal
import atexit

app = Flask(__name__)
app.secret_key = "jiki-demo-secret-key"  # For session management

# Dictionary to store orchestrator instances for each session
session_orchestrators = {}

# Function to start the MCP server if not already running
def ensure_server_running():
    # Check if server is already running on port 8000
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_running = False
    try:
        sock.connect(('localhost', 8000))
        server_running = True
    except:
        server_running = False
    finally:
        sock.close()
    
    if server_running:
        print("MCP server already running on port 8000")
        return None
    
    # Start the server
    print("Starting MCP server with SSE transport on port 8000...")
    server_process = subprocess.Popen(
        ["fastmcp", "run", "servers/calculator_server.py", "--transport", "sse", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Register cleanup function
    atexit.register(lambda: os.kill(server_process.pid, signal.SIGTERM) if server_process.poll() is None else None)
    
    # Wait for server to start
    time.sleep(2)
    return server_process

# Start the server when the application starts
server_process = ensure_server_running()

# Get or create an orchestrator for the current session
def get_session_orchestrator():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    if session_id not in session_orchestrators:
        # Configure sampling for web responses (more concise)
        sampler = SamplerConfig(
            temperature=0.7,
            max_tokens=500
        )
        
        # Create a new orchestrator for this session
        session_orchestrators[session_id] = Jiki(
            auto_discover_tools=True,
            mcp_mode="sse",
            mcp_url="http://localhost:8000",
            sampler_config=sampler,
            trace=True
        )
    
    return session_orchestrators[session_id]

# Cleanup old sessions periodically
def cleanup_old_sessions():
    # In a real application, you would implement session timeout logic here
    pass

# API endpoint for chat
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    message = data['message']
    try:
        # Get the orchestrator for this session
        orchestrator = get_session_orchestrator()
        
        # Process the message
        if data.get('detailed', False):
            # Return detailed response with tool calls
            response = orchestrator.process_detailed(message)
            return jsonify({
                'result': response.result,
                'tool_calls': [
                    {
                        'tool_name': call.tool_name,
                        'arguments': call.arguments,
                        'result': call.result
                    } for call in response.tool_calls
                ]
            })
        else:
            # Return simple response
            result = orchestrator.process(message)
            return jsonify({'result': result})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve a simple HTML interface
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jiki Chat</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            #chat-container { border: 1px solid #ddd; height: 400px; padding: 10px; overflow-y: auto; margin-bottom: 10px; }
            #input-container { display: flex; }
            #message-input { flex-grow: 1; padding: 8px; }
            button { padding: 8px 16px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            .user-message { text-align: right; margin: 5px; }
            .bot-message { text-align: left; margin: 5px; }
            .message { padding: 8px; border-radius: 5px; display: inline-block; max-width: 70%; }
            .user-message .message { background-color: #DCF8C6; }
            .bot-message .message { background-color: #F0F0F0; }
        </style>
    </head>
    <body>
        <h1>Jiki Chat</h1>
        <div id="chat-container"></div>
        <div id="input-container">
            <input type="text" id="message-input" placeholder="Type your message...">
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            function addMessage(text, isUser) {
                const chatContainer = document.getElementById('chat-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = isUser ? 'user-message' : 'bot-message';
                
                const messageSpan = document.createElement('span');
                messageSpan.className = 'message';
                messageSpan.innerText = text;
                
                messageDiv.appendChild(messageSpan);
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function sendMessage() {
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                
                if (message) {
                    addMessage(message, true);
                    input.value = '';
                    
                    // Send to API
                    fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ message: message }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            addMessage('Error: ' + data.error, false);
                        } else {
                            addMessage(data.result, false);
                        }
                    })
                    .catch(error => {
                        addMessage('Error: Could not reach server', false);
                        console.error('Error:', error);
                    });
                }
            }
            
            // Allow Enter key to send message
            document.getElementById('message-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            // Welcome message
            addMessage('Welcome to Jiki Chat! I can help with calculations. Try asking "What is 25 * 16?"', false);
        </script>
    </body>
    </html>
    """

# Run the Flask app
if __name__ == '__main__':
    print("Starting web server on http://localhost:5000")
    app.run(debug=True)
```

## Next Steps

After exploring these examples, you might want to:

1. Check out the [CLI Reference](cli_reference.md) for command-line usage
2. Learn about [Core Interfaces](core_interfaces.md) to extend Jiki
3. Explore the [Architecture Overview](architecture_overview.md) to understand Jiki's design
4. Create your own MCP tool servers using [FastMCP](https://github.com/fastmcp/fastmcp) 