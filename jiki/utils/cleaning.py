import re
from typing import List

# Precompiled patterns for cleaning
CLEAN_PATTERNS: List[re.Pattern] = [
    re.compile(r"<mcp_tool_call>.*?</mcp_tool_call>", re.DOTALL),
    re.compile(r"<mcp_tool_result>.*?</mcp_tool_result>", re.DOTALL),
    re.compile(r"<mcp_available_tools>.*?</mcp_available_tools>", re.DOTALL),
    re.compile(r"<Assistant_Thought>.*?</Assistant_Thought>", re.DOTALL),
]
# Precompiled newline collapse
NEWLINE_COLLAPSE = re.compile(r"\n{3,}")

def clean_output(text: str) -> str:
    """
    Remove MCP-related tags and normalize whitespace for final assistant display.
    """
    result = text
    for pat in CLEAN_PATTERNS:
        result = pat.sub("", result)
    # Trim and collapse multiple newlines
    return NEWLINE_COLLAPSE.sub("\n\n", result.strip()) 