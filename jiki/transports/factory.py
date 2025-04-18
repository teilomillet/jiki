from typing import Protocol, Any, Dict, Optional
from fastmcp.client.transports import PythonStdioTransport, SSETransport


class ITransport(Protocol):
    """
    Protocol describing an MCP transport accepted by EnhancedMCPClient.
    """
    ...  # Methods and properties defined by fastmcp transports


def get_transport(transport_type: str, script_path: Optional[str] = None) -> Any:
    """
    Factory to create supported transports by name.

    :param transport_type: 'stdio' or 'sse'
    :param script_path: path to server script for stdio or URL for SSE
    :return: an instance of the requested transport
    """
    transport_map: Dict[str, Any] = {
        'stdio': PythonStdioTransport,
        'sse': SSETransport,
    }
    if transport_type not in transport_map:
        raise ValueError(f"Unsupported transport type: {transport_type}")
    cls = transport_map[transport_type]
    if transport_type == 'stdio':
        if script_path is None:
            raise ValueError("`script_path` must be provided for stdio transport")
        return cls(script_path)
    # For SSE, script_path is the URL (defaulting if not provided)
    return cls(script_path or 'http://localhost:6277/mcp') 