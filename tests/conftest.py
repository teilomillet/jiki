"""
Pytest configuration for Jiki tests
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_model():
    """
    Create a mock LLM model for testing
    """
    model = MagicMock()
    return model


@pytest.fixture
def mock_mcp_client():
    """
    Create a mock MCP client for testing
    """
    client = MagicMock()
    return client


@pytest.fixture
def sample_tools_config():
    """
    Create a sample tools configuration for testing
    """
    return [
        {
            "tool_name": "add",
            "description": "Add two numbers",
            "arguments": {
                "a": {"type": "integer", "description": "First number"},
                "b": {"type": "integer", "description": "Second number"}
            },
            "required": ["a", "b"]
        },
        {
            "tool_name": "search",
            "description": "Search for information",
            "arguments": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Maximum number of results"}
            },
            "required": ["query"]
        }
    ]