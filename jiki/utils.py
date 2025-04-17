"""
Utility functions for Jiki

This module contains pure functions that can be used throughout the Jiki codebase.
These functions have no side effects and don't depend on external state.
"""

import re
import json
from typing import Dict, Any, Tuple, Optional, List


def repair_json(json_str: str) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """
    Attempts to parse and repair malformed JSON strings.
    
    Args:
        json_str: The JSON string to parse and potentially repair
        
    Returns:
        Tuple containing:
        - The parsed JSON object as a dictionary
        - The parsing method used ('direct', 'extracted', 'repaired', 'failed', 'no_json_found')
        - The error message if parsing failed, None otherwise
    """
    # First attempt: Try to parse the entire content as JSON
    try:
        result = json.loads(json_str)
        return result, "direct", None
    except json.JSONDecodeError as e:
        parsing_error = str(e)
        # Second attempt: Look for JSON object boundaries
        json_start = json_str.find('{')
        json_end = json_str.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_content = json_str[json_start:json_end + 1]
            try:
                result = json.loads(json_content)
                return result, "extracted", None
            except json.JSONDecodeError as e2:
                # Third attempt: Try to fix common JSON errors
                try:
                    # Replace single quotes with double quotes (common LLM mistake)
                    fixed_content = json_content.replace("'", '"')
                    # Fix trailing commas in objects (another common mistake)
                    fixed_content = re.sub(r',\s*}', '}', fixed_content)
                    # Fix missing quotes around keys (another common mistake)
                    fixed_content = re.sub(r'(\{|\,)\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', fixed_content)
                    result = json.loads(fixed_content)
                    return result, "repaired", parsing_error
                except json.JSONDecodeError as e3:
                    return {}, "failed", str(e3)
        else:
            return {}, "no_json_found", parsing_error


def validate_tool_arguments(
    arguments: Dict[str, Any], 
    expected_args: Dict[str, Dict[str, Any]], 
    required_args: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Validates tool arguments against a schema.
    
    Args:
        arguments: The arguments to validate
        expected_args: Schema of expected arguments
        required_args: List of required argument names
        
    Returns:
        Tuple containing:
        - List of missing required arguments
        - List of type mismatch descriptions
    """
    # Check for missing required arguments
    missing_args = [k for k in required_args if k not in arguments]
    
    # Check for type mismatches in provided arguments
    type_mismatches = []
    for arg_name, arg_value in arguments.items():
        if arg_name in expected_args:
            expected_type = expected_args[arg_name].get("type")
            if expected_type:
                # Basic type checking
                if expected_type == "integer" and not isinstance(arg_value, int):
                    type_mismatches.append(f"{arg_name} (expected integer, got {type(arg_value).__name__})")
                elif expected_type == "number" and not isinstance(arg_value, (int, float)):
                    type_mismatches.append(f"{arg_name} (expected number, got {type(arg_value).__name__})")
                elif expected_type == "string" and not isinstance(arg_value, str):
                    type_mismatches.append(f"{arg_name} (expected string, got {type(arg_value).__name__})")
                elif expected_type == "boolean" and not isinstance(arg_value, bool):
                    type_mismatches.append(f"{arg_name} (expected boolean, got {type(arg_value).__name__})")
    
    return missing_args, type_mismatches


def categorize_error(error: Exception) -> Tuple[str, str]:
    """
    Categorizes an exception for better error reporting.
    
    Args:
        error: The exception to categorize
        
    Returns:
        Tuple containing:
        - Error category code
        - User-friendly error message
    """
    error_type = type(error).__name__
    
    if "ConnectionRefused" in error_type or "ConnectionError" in error_type:
        error_category = "CONNECTION"
        friendly_message = f"Could not connect to the tool server. The server may be down or unreachable."
    elif "Timeout" in error_type:
        error_category = "TIMEOUT"
        friendly_message = f"The tool execution timed out. The operation may have taken too long to complete."
    elif "ValueError" in error_type:
        error_category = "VALUE"
        friendly_message = f"Invalid value provided to the tool: {str(error)}"
    elif "KeyError" in error_type:
        error_category = "KEY"
        friendly_message = f"Missing key in tool arguments: {str(error)}"
    elif "TypeError" in error_type:
        error_category = "TYPE"
        friendly_message = f"Type error in tool execution: {str(error)}"
    else:
        error_category = "GENERAL"
        friendly_message = f"An error occurred during tool execution: {str(error)}"
    
    return error_category, friendly_message


def format_argument_descriptions(
    expected_args: Dict[str, Dict[str, Any]], 
    required_args: List[str]
) -> List[str]:
    """
    Formats argument descriptions for error messages.
    
    Args:
        expected_args: Schema of expected arguments
        required_args: List of required argument names
        
    Returns:
        List of formatted argument descriptions
    """
    arg_descriptions = []
    for arg_name, arg_schema in expected_args.items():
        arg_type = arg_schema.get("type", "any")
        arg_desc = arg_schema.get("description", "")
        required = "required" if arg_name in required_args else "optional"
        arg_descriptions.append(f"  - {arg_name} ({arg_type}, {required}): {arg_desc}")
    
    return arg_descriptions


def clean_output(text: str, patterns: List[re.Pattern]) -> str:
    """
    Cleans the output by removing specified patterns and normalizing whitespace.
    
    Args:
        text: The text to clean
        patterns: List of regex patterns to remove
        
    Returns:
        Cleaned text
    """
    result = text
    for pattern in patterns:
        result = pattern.sub("", result)
        
    # Trim whitespace and normalize newlines
    whitespace_pattern = re.compile(r"\n{3,}")
    result = whitespace_pattern.sub("\n\n", result.strip())
    
    return result