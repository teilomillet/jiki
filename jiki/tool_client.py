from typing import Protocol, List, Dict, Any
from jiki.resources.resource_manager import IResourceManager


class IToolClient(Protocol):
    """
    Protocol describing a tool client capable of discovering and invoking MCP tools.
    """
    
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools from the MCP server.
        Returns a list of tool schema dictionaries.
        """
        ...

    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Invoke a tool by name with the provided arguments.
        Returns the tool's raw string result (or JSON-encoded value).
        """
        ...

class IMCPClient(IToolClient, IResourceManager, Protocol):
    """
    Combined protocol for MCP clients supporting both tool discovery/invocation and resource management.
    """
    ...
    # Also support root listing and notifications
    async def list_roots(self) -> List[Dict[str, Any]]: ...
    async def send_roots_list_changed(self) -> None: ... 