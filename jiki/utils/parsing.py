import re
from typing import Optional

# Precompiled regex patterns for extraction
PAT_TOOL_CALL = re.compile(r"(<mcp_tool_call>)(.*?)(</mcp_tool_call>)", re.DOTALL)
PAT_THOUGHT = re.compile(r"<Assistant_Thought>(.*?)</Assistant_Thought>", re.DOTALL)

def extract_tool_call(text: str) -> Optional[str]:
    """
    Extract the raw JSON-like content inside the first <mcp_tool_call>...</mcp_tool_call> block, if present.
    Returns the inner content or None if no complete block is found.
    """
    match = PAT_TOOL_CALL.search(text)
    if match:
        content = match.group(2)
        closing_tag = match.group(3)
        # Ensure tags match (basic check)
        if closing_tag == f"</{match.group(1)[1:-1]}>":
            return content
    return None


def extract_thought(text: str) -> Optional[str]:
    """
    Extract content from the first <Assistant_Thought>...</Assistant_Thought> block, if present.
    Returns the inner thought text or None if no block is found.
    """
    match = PAT_THOUGHT.search(text)
    if match:
        return match.group(1).strip()
    return None 