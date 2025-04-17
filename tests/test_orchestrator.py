"""
Tests for the JikiOrchestrator class
"""
import pytest
import json
import re
from unittest.mock import MagicMock, AsyncMock, patch
from jiki.orchestrator import JikiOrchestrator
from jiki.models.response import ToolCall


class TestJikiOrchestrator:
    def test_init(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test that the orchestrator initializes correctly"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        assert orchestrator.model == mock_model
        assert orchestrator.mcp_client == mock_mcp_client
        assert orchestrator.tools_config == sample_tools_config
        assert orchestrator.conversation_history == []
        assert orchestrator._last_tool_calls == []
        assert orchestrator._messages == []
        
        # Check that regex patterns are pre-compiled
        assert isinstance(orchestrator._tool_call_pattern, re.Pattern)
        assert isinstance(orchestrator._thought_pattern, re.Pattern)
        assert all(isinstance(p, re.Pattern) for p in orchestrator._clean_patterns)
    
    def test_create_available_tools_block(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test that the available tools block is created correctly"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        tools_block = orchestrator.create_available_tools_block()
        
        assert tools_block.startswith("<mcp_available_tools>")
        assert tools_block.endswith("</mcp_available_tools>")
        
        # Extract the JSON content
        json_content = tools_block.replace("<mcp_available_tools>\n", "").replace("\n</mcp_available_tools>", "")
        parsed_tools = json.loads(json_content)
        
        assert parsed_tools == sample_tools_config
    
    def test_build_initial_prompt(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test that the initial prompt is built correctly"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        prompt = orchestrator.build_initial_prompt("Hello, world!")
        
        assert "INSTRUCTIONS:" in prompt
        assert "User: Hello, world!" in prompt
        assert "<mcp_available_tools>" in prompt
    
    def test_clean_output(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test that the output is cleaned correctly"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        text = "Normal text <mcp_tool_call>Remove this</mcp_tool_call> more text <mcp_tool_result>Remove this too</mcp_tool_result>"
        cleaned = orchestrator._clean_output(text)
        
        # There might be extra spaces where tags were removed
        assert cleaned.replace("  ", " ") == "Normal text more text"
        
        # Test with multiple newlines
        text = "Line 1\n\n\n\nLine 2"
        cleaned = orchestrator._clean_output(text)
        
        assert cleaned == "Line 1\n\nLine 2"
    
    @pytest.mark.asyncio
    async def test_extract_tool_call_if_present(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test that tool calls are extracted correctly"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        # Test with a valid tool call
        text = "Some text <mcp_tool_call>{'tool_name': 'add', 'arguments': {'a': 5, 'b': 3}}</mcp_tool_call> more text"
        result = orchestrator._extract_tool_call_if_present(text)
        
        assert result == "{'tool_name': 'add', 'arguments': {'a': 5, 'b': 3}}"
        
        # Test with no tool call
        text = "Some text without a tool call"
        result = orchestrator._extract_tool_call_if_present(text)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_valid(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a valid tool call"""
        mock_mcp_client.execute_tool_call = AsyncMock(return_value="Tool result")
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"tool_name": "add", "arguments": {"a": 5, "b": 3}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert result == "Tool result"
        mock_mcp_client.execute_tool_call.assert_called_once_with("add", {"a": 5, "b": 3})
        assert len(orchestrator._last_tool_calls) == 1
        assert isinstance(orchestrator._last_tool_calls[0], ToolCall)
        assert orchestrator._last_tool_calls[0].tool == "add"
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_invalid_json(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling an invalid JSON tool call"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = 'This is not JSON'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR" in result
        assert "Invalid tool call" in result
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_missing_tool_name(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a tool call with missing tool name"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"arguments": {"a": 5, "b": 3}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR" in result
        assert "Missing or invalid 'tool_name'" in result
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a tool call with an unknown tool name"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"tool_name": "unknown", "arguments": {"a": 5, "b": 3}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR" in result
        assert "Tool 'unknown' not found" in result
        assert "Available tools are: add, search" in result
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_missing_arguments(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a tool call with missing required arguments"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"tool_name": "add", "arguments": {"a": 5}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR" in result
        assert "Invalid arguments for tool 'add'" in result
        assert "Missing required arguments: b" in result
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_type_mismatch(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a tool call with type mismatches"""
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"tool_name": "add", "arguments": {"a": "5", "b": 3}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR" in result
        assert "Invalid arguments for tool 'add'" in result
        assert "Type mismatches" in result
    
    @pytest.mark.asyncio
    async def test_handle_tool_call_execution_error(self, mock_model, mock_mcp_client, sample_tools_config):
        """Test handling a tool call that raises an error during execution"""
        mock_mcp_client.execute_tool_call = AsyncMock(side_effect=ValueError("Test error"))
        orchestrator = JikiOrchestrator(mock_model, mock_mcp_client, sample_tools_config)
        
        call_content = '{"tool_name": "add", "arguments": {"a": 5, "b": 3}}'
        result = await orchestrator._handle_tool_call(call_content, [])
        
        assert "ERROR (VALUE)" in result
        assert "Failed to execute tool 'add'" in result
        assert "Test error" in result