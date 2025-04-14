from fastmcp import Client
from typing import Any
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