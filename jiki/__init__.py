"""
Jiki - A flexible LLM orchestration framework with built-in tool calling capabilities.
"""

from .orchestrator import JikiOrchestrator
from .models.litellm import LiteLLMModel
from .mcp_client import MCPClient, EnhancedMCPClient
from .logging import TraceLogger
from .tools.config import load_tools_config
from .cli import JikiCLI, run_cli

__all__ = [
    'JikiOrchestrator',
    'LiteLLMModel',
    'MCPClient',
    'EnhancedMCPClient',
    'TraceLogger',
    'load_tools_config',
    'JikiCLI',
    'run_cli',
    'create_orchestrator',
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