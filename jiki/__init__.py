"""
Jiki - A flexible LLM orchestration framework with built-in tool calling capabilities.
"""

from typing import List, Dict, Any, Union
import json
import asyncio
import types

from .orchestrator import JikiOrchestrator
from .models.litellm import LiteLLMModel
from .mcp_client import MCPClient, EnhancedMCPClient
from .logging import TraceLogger
from .tools.config import load_tools_config
from .tools.tool import Tool
from .models.response import DetailedResponse, ToolCall

__all__ = [
    'JikiOrchestrator',
    'LiteLLMModel',
    'MCPClient',
    'EnhancedMCPClient',
    'TraceLogger',
    'load_tools_config',
    'create_orchestrator',
    'create_jiki',
    'Tool',
    'DetailedResponse',
    'ToolCall',
]

def create_orchestrator(
    model_name="anthropic/claude-3-sonnet-20240229",
    tools_config_path="tools.json",
    mcp_mode="stdio",
    mcp_script_path=None,
    enable_logging=True
):
    """
    Create a preconfigured Jiki orchestrator with sensible defaults.
    
    :param model_name: The LiteLLM-supported model name
    :param tools_config_path: Path to the tools configuration JSON file
    :param mcp_mode: MCP transport mode ("stdio" or "sse")
    :param mcp_script_path: Path to MCP server script (or URL for SSE)
    :param enable_logging: Whether to enable logging of interaction traces
    :return: Configured JikiOrchestrator instance and helper components
    """
    # Create the model
    model = LiteLLMModel(model_name)
    
    # Create the logger if enabled
    logger = TraceLogger() if enable_logging else None
    
    # Create the MCP client
    mcp_client = EnhancedMCPClient(
        transport_type=mcp_mode,
        script_path=mcp_script_path
    )
    
    # Load tools configuration
    tools_config = load_tools_config(tools_config_path)
    
    # Create orchestrator
    orchestrator = JikiOrchestrator(model, mcp_client, tools_config, logger=logger)
    
    return {
        "orchestrator": orchestrator,
        "model": model,
        "mcp_client": mcp_client,
        "logger": logger,
        "tools_config": tools_config
    }

def create_jiki(
    model="anthropic/claude-3-7-sonnet-latest",
    tools=None,
    mcp_mode="stdio",
    mcp_script_path=None,
    trace=True,
    trace_dir=None
) -> JikiOrchestrator:
    """
    Create a pre-configured Jiki orchestrator with a streamlined interface.
    
    Args:
        model (str): The model name to use
        tools (Union[str, List[Union[str, Tool, dict]]]): Tool configuration - can be a file path,
                                                        a list of tool names, a list of Tool objects,
                                                        or a list of tool config dicts.
        mcp_mode (str): MCP transport mode ("stdio" or "sse")
        mcp_script_path (str): Path to MCP server script (or URL for SSE)
        trace (bool): Whether to enable interaction tracing
        trace_dir (str): Directory to save traces (None for memory only)
        
    Returns:
        JikiOrchestrator: Configured orchestrator instance
    """
    # Create the model
    model_instance = LiteLLMModel(model)
    
    # Create the logger if enabled
    logger = None
    if trace:
        # Pass trace_dir to TraceLogger constructor
        logger = TraceLogger(log_dir=trace_dir) if trace_dir else TraceLogger()
    
    # Create the MCP client
    # Assuming EnhancedMCPClient is still the desired client here
    mcp_client = EnhancedMCPClient(
        transport_type=mcp_mode,
        script_path=mcp_script_path
    )
    
    # Process tools configuration
    tools_config = []
    if isinstance(tools, str):
        # Load from file path
        try:
            tools_config = load_tools_config(tools)
        except FileNotFoundError:
             raise FileNotFoundError(f"Tools configuration file not found: {tools}")
    elif isinstance(tools, list):
        # Process list of tools
        for tool_item in tools: # Renamed loop variable
            if isinstance(tool_item, str):
                # Handle tool name (look up in default tools)
                default_tool = _get_default_tool(tool_item)
                if default_tool:
                    tools_config.append(default_tool)
                else:
                    # Maybe provide a way to register default tools later
                    raise ValueError(f"Unknown default tool name: {tool_item}") 
            elif isinstance(tool_item, Tool):
                # Convert Tool object to config dict
                tools_config.append(tool_item.to_dict())
            elif isinstance(tool_item, dict):
                # Already in config format, basic validation?
                if "tool_name" in tool_item and "description" in tool_item and "arguments" in tool_item:
                     tools_config.append(tool_item)
                else:
                     raise ValueError(f"Invalid tool dictionary format: {tool_item}")
            else:
                raise TypeError(f"Unsupported type in tools list: {type(tool_item)}")
    elif tools is not None:
         raise TypeError(f"Unsupported type for 'tools' argument: {type(tools)}")
         
    # Create orchestrator
    orchestrator = JikiOrchestrator(model_instance, mcp_client, tools_config, logger=logger)
    
    # Attach helper methods
    _attach_helper_methods(orchestrator, logger)
    
    return orchestrator

def _get_default_tool(tool_name):
    """Retrieve a default tool configuration by name."""
    # Simple example default tools - can be expanded or made configurable
    default_tools = {
        "calculator": {
            "tool_name": "calculator",
            "description": "Perform mathematical calculations on an expression.",
            "arguments": {
                "expression": {"type": "string", "description": "The mathematical expression to evaluate (e.g., '2 + 2 * 5')"}
            }
        },
        "add": {
            "tool_name": "add",
            "description": "Add two numbers together.",
            "arguments": {
                "a": {"type": "integer", "description": "The first number to add.", "required": True},
                "b": {"type": "integer", "description": "The second number to add.", "required": True}
            }
        },
         "subtract": {
            "tool_name": "subtract",
            "description": "Subtract the second number from the first number.",
            "arguments": {
                "a": {"type": "integer", "description": "The number to subtract from.", "required": True},
                "b": {"type": "integer", "description": "The number to subtract.", "required": True}
            }
        },
        "multiply": {
            "tool_name": "multiply",
            "description": "Multiply two numbers together.",
            "arguments": {
                "a": {"type": "integer", "description": "The first number to multiply.", "required": True},
                "b": {"type": "integer", "description": "The second number to multiply.", "required": True}
            }
        },
        "divide": {
            "tool_name": "divide",
            "description": "Divide the first number by the second number.",
            "arguments": {
                "a": {"type": "integer", "description": "The numerator (number to be divided).", "required": True},
                "b": {"type": "integer", "description": "The denominator (number to divide by).", "required": True}
            }
        }
        # Add more default tools here
    }
    return default_tools.get(tool_name)

def _attach_helper_methods(orchestrator, logger):
    """Attach helper methods to the orchestrator instance."""
    
    # Add synchronous wrapper for process_user_input
    # Using self requires binding the method
    def process(self, user_input):
        """Synchronous wrapper for process_user_input."""
        # Ensure event loop management is robust
        try:
            loop = asyncio.get_running_loop()
            # If a loop is running, create a task
            # This might be needed in some environments like notebooks
            # but asyncio.run handles loop creation/closing generally.
            # For simplicity, stick with asyncio.run for now.
            # fut = asyncio.ensure_future(self.process_user_input(user_input))
            # loop.run_until_complete(fut)
            # return fut.result()
            return asyncio.run(self.process_user_input(user_input))
        except RuntimeError: # No running event loop
            return asyncio.run(self.process_user_input(user_input))
    
    # Add method to get detailed response with tool calls
    async def process_detailed_async(self, user_input):
        """Process user input and return a DetailedResponse with result and tool calls."""
        # Ensure _last_tool_calls is reset before processing (already done in updated process_user_input)
        result = await self.process_user_input(user_input)
        
        # Tool calls are now stored in self._last_tool_calls by the updated _handle_tool_call
        tool_calls_list = getattr(self, "_last_tool_calls", [])
        
        traces_list = None
        if logger and hasattr(logger, 'get_current_traces'):
            # Assuming get_current_traces gives traces for the *last* interaction
            # or all traces. The plan implies getting current session traces.
            traces_list = logger.get_current_traces()
            # If get_current_traces returns ALL traces, need filtering logic here
            # For now, assume it returns relevant traces for the last call (or all)
            
        return DetailedResponse(
            result=result,
            tool_calls=tool_calls_list,
            traces=traces_list
        )
    
    # Synchronous version of process_detailed
    def process_detailed(self, user_input):
        """Synchronous wrapper for process_detailed_async."""
        try:
            loop = asyncio.get_running_loop()
            return asyncio.run(self.process_detailed_async(user_input))
        except RuntimeError: # No running event loop
            return asyncio.run(self.process_detailed_async(user_input))
    
    # Export traces method
    def export_traces(self, filepath=None):
        """Export all interaction traces to a file."""
        if not logger or not hasattr(logger, 'save_all_traces'):
            raise RuntimeError("Tracing is not enabled or logger does not support saving traces.")
        
        # filepath=None will use default in save_all_traces
        logger.save_all_traces(filepath)
    
    # Attach methods to orchestrator instance using types.MethodType
    orchestrator.process = types.MethodType(process, orchestrator)
    orchestrator.process_detailed_async = types.MethodType(process_detailed_async, orchestrator)
    orchestrator.process_detailed = types.MethodType(process_detailed, orchestrator)
    orchestrator.export_traces = types.MethodType(export_traces, orchestrator) 