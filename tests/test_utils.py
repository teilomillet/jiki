"""
Tests for the utility functions in jiki.utils
"""
import pytest
import re
from jiki.utils import (
    repair_json, 
    validate_tool_arguments, 
    categorize_error, 
    format_argument_descriptions,
    clean_output
)


class TestRepairJson:
    def test_valid_json(self):
        json_str = '{"tool_name": "add", "arguments": {"a": 5, "b": 3}}'
        result, method, error = repair_json(json_str)
        assert method == "direct"
        assert error is None
        assert result == {"tool_name": "add", "arguments": {"a": 5, "b": 3}}
    
    def test_json_with_surrounding_text(self):
        json_str = 'Some text before {"tool_name": "add", "arguments": {"a": 5, "b": 3}} and after'
        result, method, error = repair_json(json_str)
        assert method == "extracted"
        assert error is None
        assert result == {"tool_name": "add", "arguments": {"a": 5, "b": 3}}
    
    def test_json_with_single_quotes(self):
        json_str = "{'tool_name': 'add', 'arguments': {'a': 5, 'b': 3}}"
        result, method, error = repair_json(json_str)
        assert method == "repaired"
        assert error is not None
        assert result == {"tool_name": "add", "arguments": {"a": 5, "b": 3}}
    
    def test_json_with_trailing_comma(self):
        json_str = '{"tool_name": "add", "arguments": {"a": 5, "b": 3,}}'
        result, method, error = repair_json(json_str)
        assert method == "repaired"
        assert error is not None
        assert result == {"tool_name": "add", "arguments": {"a": 5, "b": 3}}
    
    def test_invalid_json(self):
        json_str = '{"tool_name": "add", arguments: {"a": 5, "b": 3}'
        result, method, error = repair_json(json_str)
        assert method == "failed"
        assert error is not None
        assert result == {}
    
    def test_no_json(self):
        json_str = "This is not JSON at all"
        result, method, error = repair_json(json_str)
        assert method == "no_json_found"
        assert error is not None
        assert result == {}


class TestValidateToolArguments:
    def test_valid_arguments(self):
        arguments = {"a": 5, "b": 3}
        expected_args = {
            "a": {"type": "integer", "description": "First number"},
            "b": {"type": "integer", "description": "Second number"}
        }
        required_args = ["a", "b"]
        
        missing, mismatches = validate_tool_arguments(arguments, expected_args, required_args)
        assert missing == []
        assert mismatches == []
    
    def test_missing_arguments(self):
        arguments = {"a": 5}
        expected_args = {
            "a": {"type": "integer", "description": "First number"},
            "b": {"type": "integer", "description": "Second number"}
        }
        required_args = ["a", "b"]
        
        missing, mismatches = validate_tool_arguments(arguments, expected_args, required_args)
        assert missing == ["b"]
        assert mismatches == []
    
    def test_type_mismatches(self):
        arguments = {"a": "5", "b": 3}
        expected_args = {
            "a": {"type": "integer", "description": "First number"},
            "b": {"type": "integer", "description": "Second number"}
        }
        required_args = ["a", "b"]
        
        missing, mismatches = validate_tool_arguments(arguments, expected_args, required_args)
        assert missing == []
        assert len(mismatches) == 1
        assert "a (expected integer, got str)" in mismatches[0]


class TestCategorizeError:
    def test_value_error(self):
        error = ValueError("Invalid value")
        category, message = categorize_error(error)
        assert category == "VALUE"
        assert "Invalid value" in message
    
    def test_key_error(self):
        error = KeyError("missing_key")
        category, message = categorize_error(error)
        assert category == "KEY"
        assert "missing_key" in message
    
    def test_type_error(self):
        error = TypeError("Wrong type")
        category, message = categorize_error(error)
        assert category == "TYPE"
        assert "Wrong type" in message
    
    def test_general_error(self):
        error = Exception("Generic error")
        category, message = categorize_error(error)
        assert category == "GENERAL"
        assert "Generic error" in message


class TestFormatArgumentDescriptions:
    def test_format_arguments(self):
        expected_args = {
            "a": {"type": "integer", "description": "First number"},
            "b": {"type": "integer", "description": "Second number"}
        }
        required_args = ["a"]
        
        descriptions = format_argument_descriptions(expected_args, required_args)
        assert len(descriptions) == 2
        assert "a (integer, required)" in descriptions[0]
        assert "b (integer, optional)" in descriptions[1]


class TestCleanOutput:
    def test_clean_output(self):
        text = "<tag>Remove this</tag> but keep this <another>remove this too</another>"
        patterns = [
            re.compile(r"<tag>.*?</tag>", re.DOTALL),
            re.compile(r"<another>.*?</another>", re.DOTALL)
        ]
        
        result = clean_output(text, patterns)
        assert result == "but keep this"
    
    def test_normalize_whitespace(self):
        text = "Line 1\n\n\n\nLine 2"
        patterns = []
        
        result = clean_output(text, patterns)
        assert result == "Line 1\n\nLine 2"