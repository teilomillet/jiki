from fastmcp import Client
from jiki.transports.factory import ITransport, get_transport  # Transport interface and factory
from jiki.tool_client import IToolClient
from typing import Any, List, Dict
import traceback
import json
from jiki.utils.helpers import json_serializer_default

class MCPClient:
    """
    Low-level MCP client for direct tool invocation over a given transport.

    Example:
        # Using stdio transport to a local Python server
        from fastmcp.client.transports import PythonStdioTransport
        client = MCPClient(PythonStdioTransport('servers/calculator_server.py'))
        result = await client.execute_tool_call('add', {'a': 2, 'b': 3})
    """
    def __init__(self, connection: str):
        """
        :param connection: Connection string or transport for MCP server (e.g., 'python servers/calculator_server.py' or 'http://localhost:8000/mcp')
        """
        self.connection = connection

    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """
        Call a tool on the connected MCP server and return the result as a string.
        Complex results (lists, dicts) are serialized as JSON using a custom encoder.
        """
        async with Client(self.connection) as client:
            result = await client.call_tool(tool_name, arguments)
            
            # Handle different response formats
            processed_result: Any
            if hasattr(result, 'content'):
                # If multiple content blocks, concatenate all text blocks
                if result.content:
                    processed_result = ''.join(block.text for block in result.content)
                else:
                    processed_result = None
            else:
                # Use the raw result if it's not a fastmcp ToolResult object
                processed_result = result

            # Serialize non-string results to JSON for clarity
            if isinstance(processed_result, str):
                return processed_result # Return strings directly
            elif processed_result is None:
                return "" # Return empty string for None result
            else:
                try:
                    # Serialize lists, dicts, bools, numbers, etc. to JSON
                    # Use the custom default function here!
                    return json.dumps(processed_result, default=json_serializer_default)
                except TypeError as e:
                    # This fallback should now be much rarer
                    print(f"[WARN] Could not JSON-serialize result type {type(processed_result)} even with custom serializer, falling back to str(): {e}")
                    return str(processed_result)


# MCP wrapper to handle errors and ensure proper MCP formatting 
class EnhancedMCPClient(IToolClient):
    """
    Enhanced MCP client that ensures proper XML tagging and error handling.

    Example usage:
        import asyncio
        from jiki.mcp_client import EnhancedMCPClient

        async def demo():
            client = EnhancedMCPClient(
                transport_type="stdio",
                script_path="servers/calculator_server.py"
            )
            tools = await client.discover_tools()
            result = await client.execute_tool_call("add", {"a": 1, "b": 2})
            resources = await client.list_resources()
            contents = await client.read_resource("file:///path/to/data.txt")
            traces = client.get_interaction_traces()
            print(tools, result, resources, contents, traces)

        asyncio.run(demo())
    """
    def __init__(self, transport_type: str = "stdio", script_path: str = None, transport: ITransport = None):
        """
        Initialize the enhanced MCP client with configurable transport
        
        :param transport_type: Type of transport to use ("stdio" or "sse")
        :param script_path: Path to the MCP server script or URL for SSE
        :param transport: Optional pre-created ITransport instance to inject.

        Example:
            client = EnhancedMCPClient(
                transport_type="sse",
                script_path="http://localhost:8000/mcp"
            )
        """
        self.transport_type = transport_type
        self.script_path = script_path or "servers/calculator_server.py"
        self.interaction_traces: List[Dict[str, Any]] = []
        
        # Allow injecting a custom transport instance directly, otherwise use factory
        if transport is not None:
            selected_transport = transport
        else:
            selected_transport = get_transport(transport_type, script_path)
        # Create the primary MCP client
        self.mcp_client = MCPClient(selected_transport)
        
        # Track whether handshake has been performed
        self._initialized = False

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Connect to the MCP server and retrieve the list of available tool schemas.
        
        Returns:
            List[Dict[str, Any]]: List of tool schema dicts.

        Example:
            tools = await client.discover_tools()
        """
        # Perform initialization handshake once
        if not self._initialized:
            await self.initialize()
        print("[INFO] Attempting to discover tools from MCP server...")
        # We need to use the underlying transport configuration from the MCPClient
        # that EnhancedMCPClient wraps. Let's access it directly.
        transport = self.mcp_client.connection # Access the transport/connection string
        
        try:
            # Create a standard fastmcp Client using the same transport
            async with Client(transport) as client:
                # List available tools using the standard client method
                tool_list = await client.list_tools()
                
                # The tool_list likely contains Tool objects (or similar structures from fastmcp)
                # We need to convert them into the dictionary format expected by JikiOrchestrator.
                # Assuming tool_list is a list of objects with attributes like name, description, inputSchema.
                # The exact structure depends on fastmcp's return type for list_tools.
                # Let's assume a simple structure for now. We might need to adjust based on fastmcp specifics.
                
                tools_config = []
                for tool in tool_list:
                    # Basic conversion - might need refinement based on actual Tool object structure
                    schema = {
                        "tool_name": getattr(tool, 'name', None),
                        "description": getattr(tool, 'description', ''),
                        "arguments": getattr(tool, 'inputSchema', {}).get('properties', {}) 
                        # TODO: Handle 'required' fields if available in inputSchema
                        # TODO: Deeper validation of the schema structure might be needed
                    }
                    if schema["tool_name"]:
                         # Add required field if present in the original schema
                         if 'required' in getattr(tool, 'inputSchema', {}):
                              schema['required'] = getattr(tool, 'inputSchema', {})['required']
                         tools_config.append(schema)
                    else:
                         print(f"[WARN] Discovered tool object missing 'name': {tool}")

                print(f"[INFO] Discovered {len(tools_config)} tools.")
                return tools_config

        except ConnectionRefusedError as e:
            print(f"[ERROR] Connection refused when trying to discover tools: {e}")
            raise RuntimeError(f"MCP Server connection refused at {transport}") from e
        except Exception as e:
            # Catch other potential errors (e.g., server not running, protocol errors)
            print(f"[ERROR] Failed to discover tools from MCP server: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to discover tools from MCP server: {e}") from e

    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool call using MCP with proper formatting and error handling

        :param tool_name: Name of the tool to invoke.
        :param arguments: Dict of arguments for the tool.
        :return: String result or JSON error payload.

        Example:
            result = await client.execute_tool_call(
                "weather", {"city": "Paris"}
            )
        """
        # Ensure initialization handshake has run
        if not self._initialized:
            await self.initialize()
        # Format the tool call into proper MCP format for logging
        tool_call_json = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        formatted_tool_call = json.dumps(tool_call_json, indent=2)
        mcp_tool_call = f"<mcp_tool_call>\n{formatted_tool_call}\n</mcp_tool_call>"
        
        try:
            print(f"[DEBUG] Executing MCP tool call: {tool_name} with arguments: {arguments}")
            
            # Execute the tool call via MCP infrastructure
            result = await self.mcp_client.execute_tool_call(tool_name, arguments)
            
            # Format as MCP tool result
            mcp_tool_result = f"<mcp_tool_result>\n{result}\n</mcp_tool_result>"
            
            # Log successful trace
            self.interaction_traces.append({
                "tool_call": mcp_tool_call,
                "tool_result": mcp_tool_result,
                "used_mcp": True
            })
            
            return result
            
        except Exception as e:
            # Log the error details
            error_details = traceback.format_exc()
            print(f"[ERROR] MCP tool call failed: {e}\n{error_details}")

            # Determine JSON-RPC error code (use e.code if available, otherwise InternalError)
            code = getattr(e, 'code', -32603)
            # Build JSON-RPC error object
            error_payload = {"error": {"code": code, "message": str(e)}}
            error_json = json.dumps(error_payload)
            mcp_tool_result = f"<mcp_tool_result>\n{error_json}\n</mcp_tool_result>"

            # Log error trace with code
            self.interaction_traces.append({
                "tool_call": mcp_tool_call,
                "tool_result": mcp_tool_result,
                "used_mcp": True,
                "error": str(e),
                "error_code": code
            })
            
            # Return structured JSON-RPC error payload
            return error_json

    def get_interaction_traces(self):
        """
        Return all logged interaction traces for debugging and analysis.

        :return: List of trace dicts containing calls, results, and handshake info.
        """
        return self.interaction_traces 

    async def initialize(self, protocol_version: str = "2025-03-26",
                          capabilities: Dict[str, Any] = None,
                          client_info: Dict[str, str] = None) -> None:
        """
        Perform MCP initialize/initialized handshake, exposing its JSON-RPC payloads in logs and traces.

        :param protocol_version: Protocol version identifier.
        :param capabilities: Additional capabilities to negotiate.
        :param client_info: Client metadata dict with 'name' and 'version'.
        """
        # Default capabilities
        default_caps = {
            "tools": {"listChanged": False},
            "resources": {"listChanged": False},
            "prompts": {"listChanged": False},
            "sampling": {},
            "roots": {"listChanged": False},
        }
        if capabilities:
            default_caps.update(capabilities)
        # Default client info
        info = client_info or {"name": "jiki", "version": "0.1.0"}
        # Build initialize request
        init_req = {
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": default_caps,
                "clientInfo": info
            },
            "jsonrpc": "2.0",
            "id": 0
        }
        init_json = json.dumps(init_req, indent=2)
        mcp_init_call = f"<mcp_initialize>\n{init_json}\n</mcp_initialize>"
        print(f"[DEBUG] Sending MCP initialize call: {mcp_init_call}")
        self.interaction_traces.append({"handshake": {"initialize": init_json}})
        # Build initialized notification
        notif = {"method": "initialized", "params": {}, "jsonrpc": "2.0"}
        notif_json = json.dumps(notif, indent=2)
        mcp_notif = f"<mcp_initialized>\n{notif_json}\n</mcp_initialized>"
        print(f"[DEBUG] Sending MCP initialized notification: {mcp_notif}")
        self.interaction_traces.append({"handshake": {"initialized": notif_json}})
        self._initialized = True 

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from MCP server."""
        if not self._initialized:
            await self.initialize()
        transport = self.mcp_client.connection
        try:
            async with Client(transport) as client:
                resources_result = await client.list_resources()
            raw_list = getattr(resources_result, 'resources', resources_result)
            resources: List[Dict[str, Any]] = []
            for r in raw_list:
                resources.append({
                    'uri': getattr(r, 'uri', None),
                    'name': getattr(r, 'name', None),
                    'description': getattr(r, 'description', None),
                    'mimeType': getattr(r, 'mimeType', None),
                })
            return resources
        except Exception as e:
            print(f"[ERROR] Failed to list resources: {e}")
            return []

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """Read resource content from MCP server."""
        if not self._initialized:
            await self.initialize()
        transport = self.mcp_client.connection
        try:
            async with Client(transport) as client:
                read_result = await client.read_resource(uri)
            contents = getattr(read_result, 'contents', None)
            if contents is None:
                contents = [read_result]
            resource_contents: List[Dict[str, Any]] = []
            for c in contents:
                resource_contents.append({
                    'uri': getattr(c, 'uri', None),
                    'mimeType': getattr(c, 'mimeType', None),
                    'text': getattr(c, 'text', None),
                })
            return resource_contents
        except Exception as e:
            print(f"[ERROR] Failed to read resource {uri}: {e}")
            return [] 