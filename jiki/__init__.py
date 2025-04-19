"""
Jiki - A flexible LLM orchestration framework with built-in tool calling capabilities.
"""
import asyncio
import sys
from typing import Optional, Union, List, Dict, Any

from .orchestrator import JikiOrchestrator
from .models.litellm import LiteLLMModel
from .mcp_client import JikiClient, EnhancedMCPClient
from .logging import TraceLogger
from .tools.config import load_tools_config
from .tools.tool import Tool
from .models.response import DetailedResponse, ToolCall
from .serialization.helpers import _attach_helper_methods
from .sampling import ISamplerConfig, SamplerConfig
from .roots.conversation_root_manager import IConversationRootManager
from .roots.root_manager import IRootManager

# Make the interactive loop function importable if needed elsewhere
# For now, it's defined in cli.py, so we'll import it within run_ui
# from .cli import _run_interactive_loop # Potential future import

__all__ = [
    'JikiOrchestrator',
    'LiteLLMModel',
    'JikiClient',
    'EnhancedMCPClient',
    'TraceLogger',
    'load_tools_config',
    'Jiki',
    'Tool',
    'DetailedResponse',
    'ToolCall',
    'IConversationRootManager',
    'IRootManager',
    'ISamplerConfig',
    'SamplerConfig',
]

def Jiki(
    model: str = "anthropic/claude-3-sonnet-20240229",
    tools: Optional[Union[str, List[Dict[str, Any]]]] = None,
    auto_discover_tools: bool = False,
    mcp_mode: str = "stdio", # or "sse"
    mcp_script_path: Optional[str] = None,
    mcp_url: Optional[str] = None,
    trace: bool = True, 
    trace_dir: Optional[str] = "interaction_traces",
    conversation_root_manager: Optional[IConversationRootManager] = None,
    prompt_builder: Optional[Any] = None, # TODO: Type hint IPromptBuilder once circular imports resolved
    sampler_config: Optional[ISamplerConfig] = None
) -> JikiOrchestrator:
    """
    Factory function to create and configure a JikiOrchestrator instance.

    This is the main entry point for easily setting up Jiki.
    It initializes the necessary components like the model wrapper, 
    MCP client, tools configuration, and logger based on the provided arguments.

    Args:
        model: Name of the language model to use (via LiteLLM).
        tools: Tool configuration. Can be:
               - Path to a JSON file defining tools.
               - A list of tool definition dictionaries.
               - None (if using auto-discovery).
        auto_discover_tools: If True, attempts to discover tools from the MCP endpoint.
                             Requires `mcp_script_path` or `mcp_url`.
        mcp_mode: Transport mode for MCP client ('stdio' or 'sse').
        mcp_script_path: Path to the script for stdio MCP transport.
        mcp_url: URL for the Server-Sent Events (SSE) MCP endpoint.
        trace: Enable/disable interaction tracing.
        trace_dir: Directory to save trace logs.
        conversation_root_manager: Optional custom manager for conversation state.
        prompt_builder: Optional custom prompt builder.
        sampler_config: Optional custom sampler configuration.

    Returns:
        An initialized JikiOrchestrator instance.

    Raises:
        ValueError: If configuration is invalid (e.g., auto-discovery without endpoint).
    """
    # Initialize logger first
    logger = TraceLogger(log_dir=trace_dir) if trace else None

    # Configure MCP client
    connection_info = {}
    if mcp_mode == "stdio":
        if not mcp_script_path:
            # Default to example server if none provided and auto-discovery is on
            if auto_discover_tools:
                default_script = "servers/calculator_server.py"
                print(f"[WARN] mcp_script_path not provided for stdio mode with auto-discovery. Defaulting to {default_script}", file=sys.stderr)
                mcp_script_path = default_script
            else:
                # If not auto-discovering, we might not need a script path if no tools are expected to be called.
                # However, it's safer to require it if tools *might* be defined or discovered later.
                # For now, allow proceeding but maybe log a warning if tools are also not provided.
                if not tools:
                     print("[WARN] mcp_script_path not provided for stdio mode, and no tools defined. Tool calls will fail.", file=sys.stderr)
        connection_info = {"type": "stdio", "script_path": mcp_script_path}
    elif mcp_mode == "sse":
        if not mcp_url:
            raise ValueError("mcp_url must be provided for SSE mode")
        connection_info = {"type": "sse", "url": mcp_url}
    else:
        raise ValueError(f"Unsupported mcp_mode: {mcp_mode}")

    # Use JikiClient as the default, full-featured client
    # Provide the script path or URL as the transport source
    transport_source = connection_info.get("script_path") or connection_info.get("url")
    mcp_client = JikiClient(transport_source)

    # --- Tool Configuration Loading ---
    actual_tools_config = []
    if auto_discover_tools:
        if not mcp_script_path and not mcp_url:
            raise ValueError("mcp_script_path or mcp_url required for auto_discover_tools")
        print("[INFO] Auto-discovering tools...")
        # Run discovery asynchronously
        try:
            # Ensure client is initialized before discovery
            asyncio.run(mcp_client.initialize()) 
            actual_tools_config = asyncio.run(mcp_client.discover_tools())
            print(f"[INFO] Discovered {len(actual_tools_config)} tools.")
        except Exception as e:
            print(f"[ERROR] Failed to auto-discover tools: {e}", file=sys.stderr)
            # Decide if we should raise or continue without tools
            raise # Re-raise for now, as auto-discovery failure is likely critical
    elif isinstance(tools, str):
        # Load from file path
        actual_tools_config = load_tools_config(tools)
    elif isinstance(tools, list):
        # Assume it's already a list of dicts
        actual_tools_config = tools
    elif tools is None:
        # No tools provided or discovered
        actual_tools_config = []
    else:
        raise TypeError("'tools' must be a file path (str), list of dicts, or None")
        
    if not actual_tools_config:
        print("[WARN] No tools configured or discovered.", file=sys.stderr)

    # Initialize model wrapper
    model_wrapper = LiteLLMModel(model_name=model, sampler_config=sampler_config)

    # Create orchestrator instance
    orchestrator = JikiOrchestrator(
        model=model_wrapper,
        mcp_client=mcp_client,
        tools_config=actual_tools_config,
        logger=logger,
        prompt_builder=prompt_builder,
        conversation_root_manager=conversation_root_manager
    )

    # Attach helper methods like run_ui, export_traces
    _attach_helper_methods(orchestrator, logger) 

    return orchestrator