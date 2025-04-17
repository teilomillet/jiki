from fastmcp import Client
from typing import Any, List, Dict
import traceback

class MCPClient:
    def __init__(self, connection: str):
        """
        :param connection: Connection string or transport for MCP server (e.g., 'python servers/calculator_server.py' or 'http://localhost:8000/mcp')
        """
        self.connection = connection

    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """
        Call a tool on the connected MCP server and return the result as a string.
        """
        async with Client(self.connection) as client:
            result = await client.call_tool(tool_name, arguments)
            
            # Handle different response formats
            if hasattr(result, 'content'):
                # Object with content attribute
                return result.content[0].text if result.content else ""
            elif isinstance(result, list):
                # List response format
                return result[0].text if result and hasattr(result[0], 'text') else str(result)
            else:
                # Fallback for any other format
                return str(result)


# MCP wrapper to handle errors and ensure proper MCP formatting 
class EnhancedMCPClient:
    """Enhanced MCP client that ensures proper XML tagging and error handling"""
    
    def __init__(self, transport_type="stdio", script_path=None):
        """
        Initialize the enhanced MCP client with configurable transport
        
        :param transport_type: Type of transport to use ("stdio" or "sse")
        :param script_path: Path to the MCP server script or URL for SSE
        """
        self.transport_type = transport_type
        self.script_path = script_path or "servers/calculator_server.py"
        self.interaction_traces = []
        
        # Create the primary MCP client
        if transport_type == "stdio":
            from fastmcp.client.transports import PythonStdioTransport
            self.mcp_client = MCPClient(PythonStdioTransport(self.script_path))
        elif transport_type == "sse":
            from fastmcp.client.transports import SSETransport
            sse_url = script_path or "http://localhost:6277/mcp"
            self.mcp_client = MCPClient(SSETransport(sse_url))
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
        
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Connect to the MCP server and retrieve the list of available tool schemas.
        
        Returns:
            List[Dict[str, Any]]: A list of tool schema dictionaries.
            
        Raises:
            RuntimeError: If the connection or tool discovery fails.
        """
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
        """
        # Format the tool call into proper MCP format for logging
        tool_call_json = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        import json
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
            
            # Create an error message
            error_msg = f"ERROR: Tool execution failed - {str(e)}"
            mcp_tool_result = f"<mcp_tool_result>\n{error_msg}\n</mcp_tool_result>"
            
            # Log error trace
            self.interaction_traces.append({
                "tool_call": mcp_tool_call,
                "tool_result": mcp_tool_result,
                "used_mcp": True,
                "error": str(e)
            })
            
            # Return the error message so the model can handle it
            return error_msg
    
    def get_interaction_traces(self):
        """Return all logged interaction traces for training data generation."""
        return self.interaction_traces 