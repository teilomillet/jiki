from typing import List, Dict, Any, Optional


def record_conversation_event(
    history: List[Dict[str, Any]],
    role: str,
    content: str,
    logger: Optional[Any],
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Append a conversation event to the local history list and delegate 
    to the logger (if provided) with optional metadata.
    """
    event = {"role": role, "content": content}
    if metadata:
        event["metadata"] = metadata 
        
    if logger:
        logger.log_event(event)
    elif metadata:
        print(f"[WARN] Logger not provided, cannot log event with metadata: {metadata}")

    if not metadata:
         history.append(event) 