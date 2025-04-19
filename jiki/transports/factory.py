from typing import Protocol, Any, Dict, Optional
from fastmcp.client.transports import PythonStdioTransport, SSETransport


class ITransport(Protocol):
    """
    Protocol defining the common interface for MCP client transport mechanisms.

    This protocol aims to abstract the specific method of communication (e.g.,
    stdio, SSE, WebSocket, in-memory) used to connect to an MCP server.
    By type-hinting dependencies with `ITransport`, components like
    `JikiClient` can work with any transport implementation that adheres
    to this contract.

    Benefits:
    - **Pluggability:** Allows swapping transport implementations (e.g., replacing
      the default `fastmcp` transports with custom ones) without changing the
      core client logic.
    - **Type Safety:** Enables static analysis tools (like MyPy) to verify that
      transport implementations provide the required methods and that client
      code uses them correctly, catching errors before runtime.
    - **Clear Contract:** Explicitly documents the methods and properties a
      transport must provide, improving maintainability and understanding.

    Current Status:
    - The factory function `get_transport` currently returns concrete instances
      from `fastmcp.client.transports` (`PythonStdioTransport`, `SSETransport`).
    - The code relies on Python's runtime duck typing, as the methods below are
      not yet explicitly defined in this protocol definition.
    - TODO: Explicitly define the required async methods (e.g., `connect`,
      `send`, `receive`, `close`) based on `fastmcp`'s actual transport
      interface to enable full static analysis benefits.
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