"""
Jiki - A flexible LLM orchestration framework with built-in tool calling capabilities.
"""
import asyncio
import sys

from .orchestrator import JikiOrchestrator
from .models.litellm import LiteLLMModel
from .mcp_client import MCPClient, EnhancedMCPClient
from .logging import TraceLogger
from .tools.config import load_tools_config
from .tools.tool import Tool
from .models.response import DetailedResponse, ToolCall
from .utils.helpers import _attach_helper_methods
from .sampling import ISamplerConfig, SamplerConfig
from .conversation_root_manager import IConversationRootManager
from .root_manager import IRootManager

# Make the interactive loop function importable if needed elsewhere
# For now, it's defined in cli.py, so we'll import it within run_ui
# from .cli import _run_interactive_loop # Potential future import

__all__ = [
    'JikiOrchestrator',
    'LiteLLMModel',
    'MCPClient',
    'EnhancedMCPClient',
    'TraceLogger',
    'load_tools_config',
    'create_jiki',
    'Tool',
    'DetailedResponse',
    'ToolCall',
    'IConversationRootManager',
    'IRootManager',
]

def create_jiki(
    model: str = "anthropic/claude-3-7-sonnet-latest",
    tools=None,
    mcp_mode: str = "stdio",
    mcp_script_path: str = None,
    trace: bool = True,
    trace_dir: str = None,
    auto_discover_tools: bool = False,
    sampler_config: ISamplerConfig = None,
    roots: list[str] | None = None,  # Optional file:// URIs for MCP roots
    conversation_root_manager: IConversationRootManager = None,
) -> JikiOrchestrator:
    """
    Create a pre-configured Jiki orchestrator with a streamlined interface.
    
    Args:
        model (str): The model name to use
        tools (Union[str, List[Union[str, Tool, dict]]]): Tool configuration - can be a file path,
                                                        a list of tool names, a list of Tool objects,
                                                        or a list of tool config dicts. Ignored if auto_discover_tools=True.
        mcp_mode (str): MCP transport mode ("stdio" or "sse")
        mcp_script_path (str): Path to MCP server script (or URL for SSE). Required if auto_discover_tools=True.
        trace (bool): Whether to enable interaction tracing
        trace_dir (str): Directory to save traces (None for memory only)
        auto_discover_tools (bool): If True, discover tools directly from the MCP server
                                    via `mcp_client.discover_tools()` instead of using the `tools` argument. Defaults to False.
        sampler_config (ISamplerConfig): Optional sampler configuration for the model
        roots (list[str] | None): Optional file:// URIs for MCP roots
        conversation_root_manager (IConversationRootManager): Optional conversation root manager

    Returns:
        JikiOrchestrator: Configured orchestrator instance
        
    Raises:
        ValueError: If auto_discover_tools is True but mcp_script_path (or equivalent connection info) is not provided.
        ValueError: If both tools and auto_discover_tools=True are provided.
        RuntimeError: If tool discovery fails.
    """
    # Parameter validation
    if auto_discover_tools and tools is not None:
        raise ValueError("Cannot provide 'tools' argument when 'auto_discover_tools' is True.")
    if auto_discover_tools and not mcp_script_path:
         # Check mcp_mode as well? SSE might imply a default URL? For now, require explicit path/URL.
         raise ValueError("'mcp_script_path' (or connection URL for SSE) must be provided when 'auto_discover_tools' is True.")

    # Create the model with optional sampling configuration
    model_instance = LiteLLMModel(model, sampler_config)
    
    # Create the logger if enabled
    logger = None
    if trace:
        # Pass trace_dir to TraceLogger constructor
        logger = TraceLogger(log_dir=trace_dir) if trace_dir else TraceLogger()
    
    # Create the MCP client
    # Assuming EnhancedMCPClient is still the desired client here
    mcp_client = EnhancedMCPClient(
        transport_type=mcp_mode,
        script_path=mcp_script_path,
        roots=roots
    )
    
    # Process tools configuration
    tools_config = []
    if auto_discover_tools:
        # Discover tools from MCP server
        try:
            # Run discovery asynchronously
            tools_config = asyncio.run(mcp_client.discover_tools())
        except RuntimeError as e:
             print(f"[ERROR] Auto-discovery of tools failed: {e}", file=sys.stderr)
             raise # Re-raise the error to halt execution
        except Exception as e:
             # Catch any other unexpected errors during discovery
             print(f"[ERROR] Unexpected error during tool auto-discovery: {e}", file=sys.stderr)
             import traceback
             traceback.print_exc()
             raise RuntimeError(f"Unexpected error during tool auto-discovery: {e}") from e
             
    elif tools is not None:
        # Load/process tools from the 'tools' argument as before
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
                    # Handle tool name (look up in default tools?) - This part might need rethinking or removal if auto-discovery is the primary path
                    # For now, keep existing logic for non-auto-discovery case.
                    # Consider if default tools make sense anymore. Perhaps deprecate?
                    # default_tool = _get_default_tool(tool_item) # Assuming _get_default_tool exists
                    # if default_tool:
                    #     tools_config.append(default_tool)
                    # else:
                    raise ValueError("Providing tool names as strings is not supported when not using auto-discovery. Provide full schema dict or Tool object, or use a config file.")
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
        else:
             raise TypeError(f"Unsupported type for 'tools' argument: {type(tools)}. Expected file path (str) or list.")
    # else: tools is None and not auto_discover_tools -> tools_config remains [] (no tools)

    # Create orchestrator
    orchestrator = JikiOrchestrator(model_instance, mcp_client, tools_config, logger=logger)
    
    # Attach helper methods using the imported function
    _attach_helper_methods(orchestrator, logger)
    
    # Attach conversation root manager or default to orchestrator itself
    orchestrator.root_manager = conversation_root_manager or orchestrator
    
    return orchestrator