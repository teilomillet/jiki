import json
from typing import Tuple, Optional, Dict, Any, List, Union
from jsonschema import validate, exceptions as jsonschema_exceptions


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
    Validate the tool_name exists and the provided arguments conform to the tool's JSON schema.
    Leverages the jsonschema library for robust validation of types, required fields,
    formats, and other schema constraints (e.g., minimum, maximum, enum).

    Args:
        tool_name: The name of the tool being called.
        arguments: The arguments provided for the tool call.
        tools_config: Either a list of tool schemas or a pre-processed dict
                      mapping tool names to their schemas. The schema for arguments
                      (tool_schema["arguments"]) should be a valid JSON schema object.

    Returns:
        Tuple[Optional[Dict[str, Any]], Optional[str]]: 
            (tool_schema, None) if validation is successful.
            (None, error_message) if validation fails.
    """
    if isinstance(tools_config, dict):
        tool_schema = tools_config.get(tool_name)
    else: # tools_config is a List[Dict[str, Any]]
        tool_schema = next((t for t in tools_config if t.get("tool_name") == tool_name), None)

    if not tool_schema:
        return None, f"ERROR: Tool '{tool_name}' not found."

    # The schema for the arguments themselves is expected under the "arguments" key of the tool_schema.
    # This argument_schema should be a valid JSON schema.
    argument_json_schema = tool_schema.get("arguments")

    if argument_json_schema is None:
        # If no "arguments" schema is defined, but arguments were provided, it's an error (unless empty args are fine).
        # If arguments are empty and no schema, it's fine.
        if arguments: 
            return None, f"ERROR: Tool '{tool_name}' does not define an argument schema but arguments were provided: {list(arguments.keys())}"
        return tool_schema, None # No schema, no arguments, so it's valid.

    if not isinstance(argument_json_schema, dict):
        # This check is important because jsonschema.validate expects a dict schema.
        return None, f"ERROR: Tool '{tool_name}' has an invalid argument schema (not a dictionary)."

    try:
        # The `validate` function from jsonschema will raise an exception if validation fails.
        validate(instance=arguments, schema=argument_json_schema)
        return tool_schema, None  # Validation successful
    except jsonschema_exceptions.ValidationError as e:
        # Provide a more user-friendly error message from the validation exception.
        # e.message often contains the specific validation failure.
        # e.path can show where in the data the error occurred, e.g., deque(['argument_name'])
        # e.validator and e.validator_value show which schema rule failed.
        error_path = list(e.path) if e.path else []
        path_str = ".".join(map(str, error_path)) if error_path else "arguments"
        
        # Constructing a concise error message
        # For simple cases, e.message is often enough. For more complex schemas, we might want to customize.
        # Example: "ERROR: Tool 'my_tool' argument 'count' failed validation: 101 is greater than the maximum of 100"
        # For now, use a generic format including the path and the message.
        return None, f"ERROR: Tool '{tool_name}' argument validation failed at '{path_str}': {e.message}"
    except Exception as e:
        # Catch any other unexpected errors during validation itself
        return None, f"ERROR: An unexpected error occurred during validation for tool '{tool_name}': {str(e)}" 