"""
Jiki - A flexible LLM orchestration framework with built-in tool calling capabilities.
"""
import asyncio
import sys
from typing import Optional, Union, List, Dict, Any

# Core components
from .orchestrator import JikiOrchestrator
from .mcp_client import JikiClient # Standard MCP client using fastmcp
from .tool_client import IMCPClient # Protocol for MCP client interaction

# Model Wrappers
from .models.litellm import LiteLLMModel
from .models.verl_compat import VerlCompatibleModel # Added for verl/HF models

# Utilities and Supporting Modules
from .logging import TraceLogger
from .tools.config import load_tools_config
from .tools.tool import Tool # Representation of a tool schema
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
    'VerlCompatibleModel',
    'JikiClient',
    'IMCPClient',
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
    # Model selection parameters - Loader is now inferred
    litellm_model_name: Optional[str] = "anthropic/claude-3-sonnet-20240229", # Default if HF params not given
    hf_model_path: Optional[str] = None, # Path for Hugging Face model (implies verl loader)
    hf_tokenizer_path: Optional[str] = None, # Optional tokenizer path (used with hf_model_path)
    model_arch: Optional[str] = None, # Architecture for verl registry (used with hf_model_path)
    hf_model_kwargs: Optional[Dict[str, Any]] = None, # Kwargs for HF from_pretrained
    
    # Tool parameters
    tools: Optional[Union[str, List[Dict[str, Any]]]] = None,
    auto_discover_tools: bool = False,
    
    # MCP Client parameters
    mcp_mode: str = "stdio", 
    mcp_script_path: Optional[str] = None,
    mcp_url: Optional[str] = None,
    
    # Other parameters
    trace: bool = True, 
    trace_dir: Optional[str] = "interaction_traces",
    conversation_root_manager: Optional[IConversationRootManager] = None,
    prompt_builder: Optional[Any] = None, # TODO: Resolve type hint for IPromptBuilder
    sampler_config: Optional[ISamplerConfig] = None,
) -> JikiOrchestrator:
    """
    Factory function to create and configure a JikiOrchestrator instance.

    This factory infers the model loading mechanism:
    - If `hf_model_path` and `model_arch` are provided, it uses `VerlCompatibleModel` 
      to load a local Hugging Face model compatible with the `verl` library.
    - Otherwise, it uses `LiteLLMModel` with `litellm_model_name`.

    Args:
        litellm_model_name: Model name for LiteLLM (used if HF params are not provided). 
                           Default: "anthropic/claude-3-sonnet-20240229".
        hf_model_path: Path to Hugging Face model weights. If provided, triggers `verl` loader.
        hf_tokenizer_path: Path to Hugging Face tokenizer (optional, defaults to hf_model_path).
        model_arch: Model architecture for verl registry (required if hf_model_path is provided).
        hf_model_kwargs: Optional kwargs for HuggingFace `from_pretrained`.
        tools: Tool configuration (path to JSON, list of dicts, or None).
        auto_discover_tools: If True, discover tools from the MCP endpoint.
        mcp_mode: Transport mode for MCP client ('stdio' or 'sse').
        mcp_script_path: Path to the script for stdio MCP transport.
        mcp_url: URL for the SSE MCP endpoint.
        trace: Enable/disable interaction tracing.
        trace_dir: Directory to save trace logs.
        conversation_root_manager: Optional custom manager for conversation state.
        prompt_builder: Optional custom prompt builder.
        sampler_config: Optional custom sampler configuration.

    Returns:
        An initialized JikiOrchestrator instance.

    Raises:
        ValueError: If configuration is ambiguous or invalid.
        ImportError: If required packages for the inferred model loader are missing.
        RuntimeError: If model loading or tool discovery fails.
    """
    # Initialize logger first
    logger = TraceLogger(log_dir=trace_dir) if trace else None

    # --- Determine and Initialize Model Wrapper --- 
    model_wrapper: Any = None
    use_verl_loader = bool(hf_model_path and model_arch)
    use_litellm_loader = not use_verl_loader

    print(f"[Jiki Factory] Inferring model loader...")
    if use_verl_loader:
        # Error if litellm_model_name was also provided non-defaultly, indicating ambiguity
        if litellm_model_name != "anthropic/claude-3-sonnet-20240229": # Check against default
             print(f"[WARN] Both Hugging Face parameters (hf_model_path, model_arch) and a non-default 'litellm_model_name' ({litellm_model_name}) were provided. Using verl loader based on HF parameters.")
             # raise ValueError("Provide either Hugging Face parameters (hf_model_path, model_arch) for 'verl' loader OR 'litellm_model_name' for 'litellm' loader, not both.")
        
        print(f"[Jiki Factory] Using VerlCompatibleModel.")
        try:
            model_wrapper = VerlCompatibleModel(
                model_arch=model_arch, # type: ignore # Checked non-None by use_verl_loader
                model_path=hf_model_path, # type: ignore # Checked non-None by use_verl_loader
                tokenizer_path=hf_tokenizer_path, 
                load_value_head=False, # Default, could be parameter later
                sampler_config=sampler_config,
                model_kwargs=hf_model_kwargs or {}
            )
            print(f"[Jiki Factory] Initialized VerlCompatibleModel for arch '{model_arch}' from {hf_model_path}")
        except ImportError as e:
             raise ImportError(f"Failed to init VerlCompatibleModel. Ensure 'verl', 'transformers', and 'torch' are installed: {e}")
        except (ValueError, RuntimeError) as e:
             raise RuntimeError(f"Failed to load model/tokenizer via VerlCompatibleModel: {e}")

    elif use_litellm_loader:
         # Error if hf parameters were partially provided
         if hf_model_path or model_arch:
             raise ValueError("If using 'litellm' loader (default), do not provide 'hf_model_path' or 'model_arch'. Specify model via 'litellm_model_name'.")
         if not litellm_model_name:
             raise ValueError("'litellm_model_name' must be provided if Hugging Face parameters (hf_model_path, model_arch) are not set.")
         
         print(f"[Jiki Factory] Using LiteLLMModel.")
         model_wrapper = LiteLLMModel(model_name=litellm_model_name, sampler_config=sampler_config)
         print(f"[Jiki Factory] Initialized LiteLLMModel for model '{litellm_model_name}'")
    else:
         # This case should theoretically not be reached due to how booleans are set
         raise RuntimeError("Internal error: Could not determine model loader type.")

    # --- Configure MCP client --- 
    connection_info = {}
    transport_source = None 
    if mcp_mode == "stdio":
        transport_source = mcp_script_path
        if not transport_source and (auto_discover_tools or tools):
            default_script = "servers/calculator_server.py"
            logger.warning(f"mcp_script_path not provided for stdio mode. Defaulting to {default_script}")
            transport_source = default_script
        connection_info = {"type": "stdio", "script_path": transport_source}
    elif mcp_mode == "sse":
        if not mcp_url:
            raise ValueError("mcp_url must be provided for SSE mode")
        transport_source = mcp_url
        connection_info = {"type": "sse", "url": transport_source}
    else:
        raise ValueError(f"Unsupported mcp_mode: {mcp_mode}")

    # JikiClient needs a valid transport_source if tools/discovery is used.
    if transport_source is None and (auto_discover_tools or tools):
         raise ValueError("MCP connection info (mcp_script_path or mcp_url) is required if tools or auto-discovery are used.")
         
    mcp_client = JikiClient(transport_source=transport_source)

    # --- Tool Configuration Loading --- 
    actual_tools_config = []
    if auto_discover_tools:
        print("[INFO] Auto-discovering tools...")
        try:
            # Prefer running async functions from an async context if possible.
            # If Jiki() is called from sync code, we need asyncio.run or similar.
            try:
                 loop = asyncio.get_running_loop()
                 actual_tools_config = loop.run_until_complete(mcp_client.discover_tools())
            except RuntimeError: # No running event loop
                 actual_tools_config = asyncio.run(mcp_client.discover_tools())
                 
            print(f"[INFO] Discovered {len(actual_tools_config)} tools.")
        except Exception as e:
            print(f"[ERROR] Failed to auto-discover tools: {e}", file=sys.stderr)
            raise RuntimeError(f"Failed during tool discovery: {e}") from e # Propagate error
    elif isinstance(tools, str):
        actual_tools_config = load_tools_config(tools)
    elif isinstance(tools, list):
        actual_tools_config = tools
    elif tools is None:
        actual_tools_config = [] # Explicitly empty list if None
    else:
        raise TypeError("'tools' must be a file path (str), list of dicts, or None")
        
    if not actual_tools_config and not auto_discover_tools:
        print("[WARN] No tools configured or discovered.", file=sys.stderr)

    # --- Create orchestrator instance --- 
    orchestrator = JikiOrchestrator(
        model=model_wrapper, # Pass the chosen model wrapper instance
        mcp_client=mcp_client,
        tools_config=actual_tools_config,
        logger=logger,
        prompt_builder=prompt_builder,
        conversation_root_manager=conversation_root_manager
    )

    # Attach helper methods like run_ui, export_traces
    _attach_helper_methods(orchestrator, logger) 

    return orchestrator