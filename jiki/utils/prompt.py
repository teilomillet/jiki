import json
from typing import List, Dict, Any


def create_available_tools_block(tools_config: List[Dict[str, Any]]) -> str:
    """
    Format a block describing the available tools (e.g., <mcp_available_tools> ... </mcp_available_tools>).
    """
    return f"<mcp_available_tools>\n{json.dumps(tools_config, indent=2)}\n</mcp_available_tools>"


def create_available_resources_block(resources_config: List[Dict[str, Any]]) -> str:
    """
    Format a block describing the available resources (e.g., <mcp_available_resources> ... </mcp_available_resources>).
    """
    return f"<mcp_available_resources>\n{json.dumps(resources_config, indent=2)}\n</mcp_available_resources>"


def build_initial_prompt(
    user_input: str,
    tools_config: List[Dict[str, Any]],
    resources_config: List[Dict[str, Any]] = None
) -> str:
    """
    Build the initial prompt for the LLM, including the user input and available tools.
    """
    block_tools = create_available_tools_block(tools_config)
    # Include resources block if provided
    block_resources = ""
    if resources_config:
        block_resources = create_available_resources_block(resources_config)

    instruction = (
        "INSTRUCTIONS: You are an AI assistant that can use tools to help solve problems. "
        "After using tools to gather information, you should provide a complete, natural language response to the user's question. "
        "If you want to use a tool, you MUST use ONLY the tool names listed in the <mcp_available_tools> block below. "
        "Always emit a <mcp_tool_call>...</mcp_tool_call> block with valid, complete JSON inside. "
        "Before calling a tool, explain your thinking in an <Assistant_Thought>...</Assistant_Thought> block. "
        "Do NOT invent tool names. Do NOT use any tool not listed. "
        "Do NOT emit malformed or incomplete JSON. "
        "After using a tool and receiving its result, continue your reasoning to provide a complete answer to the user's question. "
        "Remember to answer all parts of the user's question completely.\n"
        "\nCORRECT EXAMPLE:\n"
        "<Assistant_Thought>I need to add two numbers. I'll use the add tool.</Assistant_Thought>\n"
        "<mcp_tool_call>\n{\n  \"tool_name\": \"add\", \"arguments\": {\"a\": 3, \"b\": 3}\n}\n</mcp_tool_call>\n"
        "\nINCORRECT EXAMPLES (do NOT do this):\n"
        "<mcp_tool_call>\n{\n  \"tool_name\": \"calculator\", \"arguments\": {\"operation\": \"add\", \"numbers\": [3, 4]}\n}\n</mcp_tool_call>\n"
        "<mcp_tool_call>\n{\n  \"tool_name\": \"add\", \"arguments\": {\"a\": 3, \"b\": 4}\n  // missing closing brace\n</mcp_tool_call>\n"
        "\nAfter using a tool and getting its result, continue to answer the user's original question completely."
    )
    # Combine instruction with user input, tools, and optional resources
    prompt = (
        f"{instruction}\n\n"
        f"User: {user_input}\n\n"
        f"{block_tools}\n\n"
        f"{block_resources}\n\n"
    )
    return prompt 