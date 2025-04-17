from typing import Callable, List, Dict


def trim_context(
    messages: List[Dict[str, str]],
    num_tokens: Callable[[List[Dict[str, str]]], int],
    max_tokens: int
) -> None:
    """
    Trim the conversation context in-place to ensure it fits within max_tokens.
    Always preserve the first system message and keep at least two messages.
    """
    # Remove the second message repeatedly until token count is within limit
    while num_tokens(messages) > max_tokens and len(messages) > 2:
        messages.pop(1) 