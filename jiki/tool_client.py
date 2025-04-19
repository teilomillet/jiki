from typing import Protocol, List, Dict, Any
from jiki.resources.resource_manager import IResourceManager


class IToolClient(Protocol):
    """
    Protocol defining the standard interface for discovering and executing tools via MCP.

    This interface abstracts the core functionalities required by the Jiki orchestrator
    to interact with an external tool server:
    1. Discovering what tools are available and their schemas.
    2. Executing a specific tool with given arguments.

    By depending on `IToolClient`, the orchestrator can work with any implementation
    that fulfills this contract, decoupling it from specific client implementations
    like `JikiClient`.

    Benefits:
    - **Modularity:** Allows different tool client strategies or backends to be plugged in.
    - **Testability:** Enables using mock or stub tool clients during testing.
    - **Clear Contract:** Explicitly defines the essential interactions for tool handling.

    Implementation:
    - The primary implementation provided by Jiki is `JikiClient`
      (see `jiki/mcp_client.py`), which handles the full MCP handshake and protocol.
    - The methods defined here (`discover_tools`, `execute_tool_call`) represent the
      minimal subset required by the orchestrator for basic tool use.
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
    Protocol defining the comprehensive interface for a full-featured MCP client within Jiki.

    This interface combines several key MCP capabilities into a single contract:
    - Tool Discovery & Execution (inherited from `IToolClient`)
    - Resource Listing & Reading (inherited from `IResourceManager`)
    - Roots Listing & Change Notification (defined here)

    By depending on `IMCPClient`, components like `JikiOrchestrator` can leverage
    the full spectrum of standard MCP client-side interactions without being tied
    to a specific implementation.

    Benefits:
    - **Unified Interface:** Provides a single point of interaction for all standard
      MCP client operations needed by the orchestrator.
    - **Complete Abstraction:** Fully decouples the orchestrator from the specifics
      of the underlying client library (like `fastmcp`) and transport mechanism.
    - **Extensibility:** Allows for alternative full MCP client implementations.

    Implementation:
    - The primary implementation provided by Jiki is `JikiClient`
      (see `jiki/mcp_client.py`), which integrates `fastmcp.Client` with
      additional logic for handshakes, tracing, and protocol adherence.
    - This protocol represents the expected interface for the client passed to
      `JikiOrchestrator` during its initialization.
    """
    ...
    # Also support root listing and notifications
    async def list_roots(self) -> List[Dict[str, Any]]: ...
    async def send_roots_list_changed(self) -> None: ... 