import json
from typing import Tuple, Optional, Dict, Any, List, Union


def parse_tool_call_content(call_content: str) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
    """
    Parse the raw text inside <mcp_tool_call> tags into JSON, extract tool_name and arguments.
    Returns (tool_name, arguments, error_message). On parse failure or missing fields, error_message is set.
    """
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = {}

    # Attempt direct JSON parse
    try:
        payload = json.loads(call_content)
    except json.JSONDecodeError:
        # Try trimming to first '{' through last '}'
        start = call_content.find('{')
        end = call_content.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                payload = json.loads(call_content[start:end+1])
            except json.JSONDecodeError:
                return None, {}, "ERROR: Invalid tool call (malformed JSON)."
        else:
            return None, {}, "ERROR: Invalid tool call (malformed JSON)."

    if not isinstance(payload, dict):
        return None, {}, "ERROR: Invalid tool call payload (not an object)."

    tool_name = payload.get("tool_name")
    if not tool_name or not isinstance(tool_name, str):
        return None, {}, "ERROR: Invalid tool call (missing or malformed 'tool_name')."

    raw_args = payload.get("arguments", {})
    if not isinstance(raw_args, dict):
        return tool_name, {}, f"ERROR: Arguments for tool '{tool_name}' must be an object."

    arguments = raw_args
    return tool_name, arguments, None


def validate_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    tools_config: Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate the tool_name exists in tools_config and that required arguments are present.
    Returns (tool_schema, error_message). On validation error, tool_schema is None and error_message is set.
    """
    # Find schema by tool_name, using mapping if available
    if isinstance(tools_config, dict):
        tool_schema = tools_config.get(tool_name)
    else:
        tool_schema = next((t for t in tools_config if t.get("tool_name") == tool_name), None)

    if not tool_schema:
        return None, f"ERROR: Tool '{tool_name}' not found."

    # Check required argument keys
    expected_args = tool_schema.get("arguments", {})
    missing = [key for key in expected_args if key not in arguments]
    if missing:
        return None, f"ERROR: Tool '{tool_name}' missing required arguments: {missing}"

    return tool_schema, None 