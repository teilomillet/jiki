from typing import List, Dict, Any, Optional


def record_conversation_event(
    history: List[Dict[str, Any]],
    role: str,
    content: str,
    logger: Optional[Any]
) -> None:
    """
    Append a conversation event to the local history list and delegate to the logger if provided.
    """
    event = {"role": role, "content": content}
    history.append(event)
    if logger:
        logger.log_event(event) 