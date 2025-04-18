from typing import Protocol, List, Dict, Any


class IResourceManager(Protocol):
    """
    Protocol for listing and reading MCP resources from a server.

    Specifications: https://modelcontextprotocol.io/docs/concepts/resources
    """
    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        Retrieve all available resources as a list of metadata dicts.

        Each dict includes keys: 'uri', 'name', 'description', 'mimeType'.
        """
        ...

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """
        Read content for a given resource URI. Returns a list of content blocks.

        Each block dict includes keys: 'uri', 'mimeType', 'text'.
        """
        ... 