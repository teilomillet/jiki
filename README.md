# Jiki

![Jiki Logo](logo.png)

Jiki is a Python framework that connects LLMs to tool servers using the Model Context Protocol (MCP), enabling powerful AI applications with just a few lines of code.

## Quick Start

### Installation

```bash
# Using pip
pip install jiki

# Or using uv (recommended)
uv add jiki
``

### Set Up API Key

```bash
# For Anthropic Claude (default), we use LiteLLM so you can use any API key
export ANTHROPIC_API_KEY=your_key_here
```

### Run Interactive Chat

```bash
# Start interactive chat with auto-discovery and the calculator example
python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py
```

Try asking: "What is 25 * 16?" or "Can you calculate 128 / 4?"

### Single Query Mode

```bash
# Process a single query
python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py "What is 42 + 17?"
```

### Simple Python Example

```python
from jiki import Jiki

# Create orchestrator with calculator tools
orchestrator = Jiki(
    auto_discover_tools=True,
    mcp_script_path="servers/calculator_server.py"
)

# Process a query
result = orchestrator.process("What is 15 * 8?")
print(result)  # Output: 120
```

## Common Use Cases

| Use Case | Example Command | Python Example |
|----------|----------------|----------------|
| **Interactive Chat** | `python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py` | `orchestrator.run_ui()` |
| **Single Query** | `python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py "What is 5 + 10?"` | `orchestrator.process("What is 5 + 10?")` |
| **Detailed Response** | `python -m jiki.cli process --auto-discover --mcp-script-path servers/calculator_server.py --detailed --show-tools "What is 7 * 8?"` | `detailed = orchestrator.process_detailed("What is 7 * 8?")` |
| **Custom Tools** | `python -m jiki.cli run --tools tools.json --mcp-script-path servers/calculator_server.py` | `orchestrator = Jiki(tools="tools.json", mcp_script_path="servers/calculator_server.py")` |
| **Custom LLM** | `python -m jiki.cli run --auto-discover --mcp-script-path servers/calculator_server.py --model openai/gpt-4o` | `orchestrator = Jiki(model="openai/gpt-4o", auto_discover_tools=True, ...)` |
| **HTTP Transport** | `python -m jiki.cli run --auto-discover --mcp-mode sse --mcp-url http://localhost:8000` | `orchestrator = Jiki(auto_discover_tools=True, mcp_mode="sse", mcp_url="http://localhost:8000")` |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Missing API Key** | Ensure `ANTHROPIC_API_KEY` (or appropriate provider key) is set in your environment |
| **Tool Discovery Fails** | Check that the server script path is correct and the script is executable |
| **Transport Error** | For HTTP transport, make sure the server is running and the URL is correct |
| **ImportError** | Make sure all dependencies are installed: `pip install jiki[all]` |
| **Calculator Example Missing** | Clone the repo to access example servers: `git clone https://github.com/your-org/jiki.git` |

## Examples in Action

Explore these complete examples (available in the `examples/` directory):

- **Simple CLI**: `python examples/simple_multiturn_cli.py` - Interactive chat with auto-discovery
- **Custom Transport**: `python examples/custom_transport_example.py` - Connect to HTTP-based tool server
- **Detailed Responses**: `python examples/detailed_and_roots_example.py` - Get structured tool call data
- **Advanced Features**: `python examples/advanced_examples.py` - Custom sampling, conversation state

## Next Steps

Start with the use case that best matches your needs:

1. **Simple Tool Integration**
   - Begin with the calculator example
   - Create your own tools with FastMCP
   - See `examples/simple_multiturn_cli.py`

2. **Web Application Integration**
   - Learn HTTP-based transport
   - Structure responses for frontend consumption
   - See `examples/custom_transport_example.py`

3. **Debugging & Analysis**
   - Use detailed responses to inspect tool calls
   - Export and analyze traces
   - See `examples/detailed_and_roots_example.py`

4. **Advanced Customization**
   - Control LLM parameters with SamplerConfig
   - Manage conversation state
   - See `examples/advanced_examples.py`

## Key Capabilities

- **Multiple LLM Backends**: Compatible with OpenAI, Anthropic, Gemini, Mistral, and more via LiteLLM
- **Flexible Tool Integration**: Auto-discovery or manual tool definition
- **Transport Options**: Connect to tools via stdio or HTTP (SSE)
- **Detailed Responses**: Get tool call data and execution traces
- **State Management**: Save and resume conversations
- **Full CLI**: Interactive mode, single queries, and trace export

## Contributing

Contributions are welcome! (TODO: Add contributing guide link)

## License

Jiki is licensed under the Apache 2.0 License.
