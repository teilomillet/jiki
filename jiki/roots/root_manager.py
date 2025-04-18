from typing import Protocol, List, Dict, Any


class IRootManager(Protocol):
    """
    Protocol for listing and notifying changes of MCP roots.

    Specifications: https://modelcontextprotocol.io/docs/concepts/roots
    """
    async def list_roots(self) -> List[Dict[str, Any]]:
        """
        Retrieve all available roots as a list of metadata dicts.

        Each dict includes keys: 'uri', 'name'.
        """
        ...

    async def send_roots_list_changed(self) -> None:
        """
        Notify the MCP server that the list of roots has changed.
        """
        ... 