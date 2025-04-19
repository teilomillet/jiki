import abc # Added for abstract base class
import warnings # Added for deprecation warnings
import traceback
import json
from pathlib import Path
from typing import Any, List, Dict, Optional, Union, Callable
import inspect

# Use specific ClientError for tool call errors
from fastmcp import Client
# from fastmcp.client import ClientError # Previous attempt
from fastmcp.client.roots import RootsHandler, RootsList # Type hint for roots
from mcp.types import ( # Import specific types for processing results
    TextContent,
    ImageContent,
    Resource,
    ResourceTemplate,
    Tool,
    TextResourceContents,
    BlobResourceContents
)

from jiki.transports.factory import ITransport, get_transport # Keep for __init__ if needed, but Client infers now
from jiki.tool_client import IMCPClient, IToolClient
from jiki.serialization.helpers import json_serializer_default


# BaseMCPClient is no longer needed as fastmcp.Client provides the API

# --- Jiki Client (Concrete Implementation using fastmcp) ---

# Ensure JikiClient explicitly satisfies the full IMCPClient protocol
# Renamed to JikiClient for simplicity and project identity
# No longer inherits from BaseMCPClient
class JikiClient(IMCPClient):
    """
    The standard, full-featured MCP client for Jiki, built using `fastmcp`.
    (Formerly known as FullMCPClient and EnhancedMCPClient)

    Handles the complete MCP lifecycle using the fastmcp.Client:
    - Transport management (inferred by fastmcp.Client).
    - Initialization handshake (implicit in `async with Client(...)`).
    - Tool discovery (`discover_tools` -> `client.list_tools`).
    - Tool execution (`execute_tool_call` -> `client.call_tool`).
    - Resource listing and reading (`list_resources` -> `client.list_resources`, etc.).
    - Roots listing and change notification (`send_roots_list_changed`).
    - Interaction tracing.

    This is the default client used by `Jiki` and is recommended for most use cases.
    It directly uses the `fastmcp` library.

    Reference: https://gofastmcp.com/clients/client
    """
    def __init__(self,
                 transport_source: Union[str, Path, Any], # Path, URL, or FastMCP instance
                 roots: Optional[Union[RootsList, RootsHandler]] = None):
        """
        Initialize the Jiki MCP client using fastmcp.

        :param transport_source: Source for the transport connection. This can be:
                                 - Path to a server script (.py, .js) for stdio.
                                 - URL (http/s for SSE, ws/s for WebSocket).
                                 - A fastmcp.server.FastMCP instance for in-memory transport.
                                 `fastmcp.Client` will infer the correct transport.
                                 Reference: https://gofastmcp.com/clients/transports
        :param roots: Optional list of root URIs or a callable returning them for the `roots` capability.
                      Reference: https://gofastmcp.com/clients/client#roots
        """
        self.interaction_traces: List[Dict[str, Any]] = []
        self._initialized = False # Flag indicating if initialize() was called (for compatibility)

        # Store transport source and roots handler for use in `async with Client(...)`
        self._transport_source = transport_source
        self.roots_handler = roots # fastmcp.Client accepts this directly

        # Note: The actual transport instance and connection are managed by
        # `fastmcp.Client` within the `async with` blocks of the methods below.

    @staticmethod
    def _process_mcp_result(result_content_list: List[Union[TextContent, ImageContent, Any]]) -> str:
        """
        Processes the raw result list from a fastmcp call (like call_tool) into a single string.
        Handles TextContent and ImageContent specifically. Serializes others to JSON.
        """
        processed_parts = []
        if not isinstance(result_content_list, list):
            # Handle cases where the result might not be a list (though call_tool should return one)
            result_content_list = [result_content_list]

        for item in result_content_list:
            if isinstance(item, TextContent):
                processed_parts.append(item.text or "")
            elif isinstance(item, ImageContent):
                # Represent image content generically for now
                mime_type = getattr(item, 'mimeType', 'image/unknown')
                processed_parts.append(f"[Image Content ({mime_type})]")
            elif item is None:
                continue # Skip None items
            else:
                # Serialize unknown types to JSON
                try:
                    processed_parts.append(json.dumps(item, default=json_serializer_default))
                except TypeError:
                    processed_parts.append(str(item)) # Fallback

        return "\\n".join(processed_parts)


    # --- Implementation of IMCPClient Public Interface ---

    async def initialize(self, *args, **kwargs) -> None:
        """
        Marks the client as initialized (for compatibility with callers).
        The actual MCP handshake happens implicitly when the first
        `async with Client(...)` block is entered in other methods.
        """
        # This method primarily exists for compatibility if callers expect it.
        # The real handshake is handled by fastmcp.Client on connection.
        self._initialized = True
        print("[DEBUG] JikiClient conceptually initialized (handshake handled by fastmcp.Client on first use).")
        # Log conceptual handshake for tracing consistency if needed
        # (though fastmcp might handle this internally)
        init_req_log = {"method": "initialize", "params": {"protocolVersion": "unknown"}, "jsonrpc": "2.0", "id": 0}
        init_json_log = json.dumps(init_req_log, indent=2)
        notif_log = {"method": "initialized", "params": {}, "jsonrpc": "2.0"}
        notif_json_log = json.dumps(notif_log, indent=2)
        self.interaction_traces.append({"handshake": {"initialize_sent": init_json_log}})
        self.interaction_traces.append({"handshake": {"initialized_sent": notif_json_log}})

    def _on_mcp_notification(self, method: str, params: Any):
        """Capture server logging notifications per MCP logging spec."""
        # Per MCP 'utilities/logging/log' notification spec
        if method == "utilities/logging/log":
            # params expected to include {level, timestamp, message}
            self.interaction_traces.append({"log": params})

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover tools using the `client.list_tools()` method."""
        print("[INFO] Discovering tools via fastmcp.Client 'list_tools'...")
        try:
            # Subscribe to server-side logging notifications
            async with Client(self._transport_source, roots=self.roots_handler) as client:
                tool_list_mcp: List[Tool] = await client.list_tools() # Returns List[mcp.types.Tool]

            # Process the result into the expected dictionary format
            tools_config = []
            for tool in tool_list_mcp:
                # Adapt based on mcp.types.Tool structure (assuming attributes like name, description, inputSchema)
                schema = {
                    "tool_name": getattr(tool, 'name', None),
                    "description": getattr(tool, 'description', ''),
                    # Assuming inputSchema has .properties and optional .required
                    "arguments": getattr(tool, 'inputSchema', {}).get('properties', {}),
                    "required": getattr(tool, 'inputSchema', {}).get('required', [])
                }
                if schema["tool_name"]:
                    tools_config.append(schema)
                else:
                    print(f"[WARN] Discovered tool object missing 'name': {tool}")

            print(f"[INFO] Discovered {len(tools_config)} tools.")
            return tools_config

        except ConnectionError as e:
             print(f"[ERROR] Connection failed during tool discovery: {e}")
             raise RuntimeError(f"Failed to connect to MCP server for tool discovery: {e}") from e
        except Exception as e:
            print(f"[ERROR] Failed to discover tools via fastmcp: {e}")
            # Propagate as RuntimeError
            raise RuntimeError(f"Failed to discover tools from MCP server: {e}") from e


    async def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool call using the `client.call_tool` method with tracing."""
        # Format for logging
        tool_call_json = {"tool_name": tool_name, "arguments": arguments}
        formatted_tool_call = json.dumps(tool_call_json, indent=2, default=json_serializer_default)
        mcp_tool_call_log = f"<mcp_tool_call>\\n{formatted_tool_call}\\n</mcp_tool_call>"
        print(f"[DEBUG] Executing MCP tool call via fastmcp.Client: {tool_name} with arguments: {arguments}")
        self.interaction_traces.append({"tool_call": mcp_tool_call_log, "used_mcp": True}) # Log call attempt

        result_str = ""
        error_payload_json = None

        try:
            # Use fastmcp.Client context manager
            async with Client(self._transport_source, roots=self.roots_handler) as client:
                # Call the specific tool method
                raw_result_list: List[Union[TextContent, ImageContent]] = await client.call_tool(
                    name=tool_name,
                    arguments=arguments
                )

            # Process the successful result list using the static method
            result_str = JikiClient._process_mcp_result(raw_result_list)

        # Handle connection or other unexpected errors
        except Exception as e:
            error_message = f"Failed MCP communication for tool '{tool_name}': {e}"
            print(f"[ERROR] {error_message}\\n{traceback.format_exc()}")
            code = -32000 # Generic communication error
            error_payload = {"error": {"code": code, "message": error_message}}
            error_payload_json = json.dumps(error_payload)

        # Format result/error for logging and return
        if error_payload_json:
            mcp_tool_result_log = f"<mcp_tool_result>\\n{error_payload_json}\\n</mcp_tool_result>"
            # Find the previously logged call and add the error result
            for trace in reversed(self.interaction_traces):
                 if "tool_call" in trace and trace["tool_call"] == mcp_tool_call_log:
                      trace["tool_result"] = mcp_tool_result_log
                      trace["error"] = error_payload["error"]["message"]
                      trace["error_code"] = error_payload["error"]["code"]
                      break
            return error_payload_json # Return JSON-RPC error payload
        else:
            mcp_tool_result_log = f"<mcp_tool_result>\\n{result_str}\\n</mcp_tool_result>"
            # Find the previously logged call and add the success result
            for trace in reversed(self.interaction_traces):
                 if "tool_call" in trace and trace["tool_call"] == mcp_tool_call_log:
                      trace["tool_result"] = mcp_tool_result_log
                      break
            return result_str


    async def list_resources(self) -> List[Dict[str, Any]]:
        """List resources using `client.list_resources`."""
        print("[INFO] Listing resources via fastmcp.Client 'list_resources'...")
        try:
            async with Client(self._transport_source, roots=self.roots_handler) as client:
                resource_list_mcp: List[Resource] = await client.list_resources()

            # Process into dict format
            resources = []
            for r in resource_list_mcp:
                resources.append({
                    'uri': str(getattr(r, 'uri', '')) if getattr(r, 'uri', None) is not None else None,
                    'name': str(getattr(r, 'name', '')) if getattr(r, 'name', None) is not None else None,
                    'description': str(getattr(r, 'description', '')) if getattr(r, 'description', None) is not None else None,
                    'mimeType': str(getattr(r, 'mimeType', '')) if getattr(r, 'mimeType', None) is not None else None,
                })
            return resources
        except ConnectionError as e:
             print(f"[ERROR] Connection failed during resource listing: {e}")
             raise RuntimeError(f"Failed to connect to MCP server for resource listing: {e}") from e
        except Exception as e:
            print(f"[ERROR] Failed to list resources: {e}")
            return [] # Return empty list on failure as per previous logic


    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """Read resource using `client.read_resource`."""
        print(f"[INFO] Reading resource via fastmcp.Client 'read_resource': {uri}")
        try:
            async with Client(self._transport_source, roots=self.roots_handler) as client:
                # Returns List[TextResourceContents | BlobResourceContents]
                content_list_mcp: List[Union[TextResourceContents, BlobResourceContents]] = await client.read_resource(uri=uri)

            # Process into dict format
            resource_contents = []
            for c in content_list_mcp:
                 if isinstance(c, TextResourceContents):
                     resource_contents.append({
                           'uri': getattr(c, 'uri', uri),
                           'mimeType': getattr(c, 'mimeType', 'text/plain'),
                           'text': getattr(c, 'text', None),
                     })
                 elif isinstance(c, BlobResourceContents):
                     # Represent blob generically for now
                     resource_contents.append({
                           'uri': getattr(c, 'uri', uri),
                           'mimeType': getattr(c, 'mimeType', 'application/octet-stream'),
                           'text': f"[Blob Content ({getattr(c, 'mimeType', 'unknown')})]",
                     })
            return resource_contents
        except ConnectionError as e:
             print(f"[ERROR] Connection failed during resource reading ({uri}): {e}")
             raise RuntimeError(f"Failed to connect to MCP server for resource reading: {e}") from e
        except Exception as e:
            print(f"[ERROR] Failed to read resource {uri}: {e}")
            return [] # Return empty list on failure

    async def list_roots(self) -> List[Dict[str, Any]]:
        """Return the list of roots configured for this client.

        The MCP specification defines *roots/list* as a **client capability** –
        therefore FastMCP servers (and the `fastmcp.Client` library) do not expose
        a dedicated RPC for listing roots.  Instead, the client communicates its
        available roots to the server during the handshake via the
        `roots`/`set_roots` capability.

        This helper surfaces that locally‑configured information so that higher‑
        level application code (examples, orchestrators, etc.) can still query
        the active root list in a uniform way without having to keep an external
        reference.

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries with the keys ``uri`` and ``name``.  If the
            root objects contain additional attributes those are ignored for now
            to keep the structure simple and implementation‑agnostic.
        """

        roots: List[Dict[str, Any]] = []

        root_source = self.roots_handler

        # Nothing configured → just return empty list
        if root_source is None:
            return roots

        try:
            # Case 1: Static list (e.g. List[str] or List[mcp.types.Root])
            if isinstance(root_source, (list, tuple)):
                iterable = root_source

            # Case 2: Callable (fastmcp RootsHandler) – can be sync or async
            elif callable(root_source):
                result = root_source()
                if inspect.iscoroutine(result):
                    result = await result  # type: ignore[func-returns-value]
                iterable = result  # type: ignore[assignment]
            else:
                iterable = []

            # Normalise elements into simple dicts
            for item in iterable:
                uri = None
                name = ""

                # Handle mcp.types.Root or similar objects
                if hasattr(item, "uri"):
                    uri = getattr(item, "uri")
                # Primitive string → assume it's the URI directly
                elif isinstance(item, str):
                    uri = item
                # Fallback – best‑effort stringification
                else:
                    uri = str(item)

                # Optional name attribute
                if hasattr(item, "name"):
                    name = str(getattr(item, "name"))

                roots.append({"uri": str(uri), "name": name})

        except Exception as exc:
            # Swallow the error but log so that callers are not broken by a bad
            # roots handler implementation.
            print(f"[WARN] Failed to resolve roots via JikiClient.list_roots: {exc}")

        return roots

    async def send_roots_list_changed(self) -> None:
        """Notify server of roots list change via `client.send_roots_list_changed`."""
        print("[INFO] Sending roots list changed notification via fastmcp.Client...")
        try:
            async with Client(self._transport_source, roots=self.roots_handler) as client:
                await client.send_roots_list_changed()
            self.interaction_traces.append({'notification': 'roots/list_changed'})
        except ConnectionError as e:
             print(f"[ERROR] Connection failed sending roots changed notification: {e}")
             # Decide if this should raise or just log
        except Exception as e:
            print(f"[ERROR] Failed to send roots list changed notification: {e}")

    def get_interaction_traces(self) -> List[Dict[str, Any]]:
        """
        Return all logged interaction traces for debugging and analysis.
        """
        return self.interaction_traces

# --- Deprecation Warnings & Aliases ---

warnings.filterwarnings("default", category=DeprecationWarning)

# Simple Aliases for backward compatibility with warnings
def _warn_and_init(cls, new_name):
    original_init = cls.__init__
    def warned_init(self, *args, **kwargs):
        warnings.warn(
            f"{cls.__name__} is deprecated and will be removed in a future version. Use {new_name} instead.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        original_init(self, *args, **kwargs)
    return warned_init

# BaseMCPClient removed, so MCPClient alias is no longer meaningful/correct. Remove it.
# class MCPClient(BaseMCPClient):
#      __doc__ = BaseMCPClient.__doc__ # Copy docstring
#      __init__ = _warn_and_init(BaseMCPClient, "BaseMCPClient") # This would fail

# Define EnhancedMCPClient as an alias for JikiClient with a warning
class EnhancedMCPClient(JikiClient): # Inherit from the NEW name JikiClient
     __doc__ = JikiClient.__doc__ # Copy docstring from NEW name
     # Update the warning message to point to the NEW name
     __init__ = _warn_and_init(JikiClient, "JikiClient")