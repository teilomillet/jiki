from typing import Protocol, Dict, Any


class IConversationRootManager(Protocol):
    """
    Protocol for snapshotting conversation roots and resuming from saved contexts.

    Specifications: https://modelcontextprotocol.io/docs/concepts/architecture#rootmanager
    """
    def snapshot(self) -> Dict[str, Any]:
        """
        Capture the current conversation state as a snapshot dict.
        """
        ...

    def resume(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore conversation state from a snapshot dict.
        """
        ... 