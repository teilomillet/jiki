import asyncio
import types
import sys
from typing import TYPE_CHECKING, Any, Optional
from datetime import date, datetime  # Added imports for JSON serializer fallback

# Use TYPE_CHECKING to avoid circular import issues at runtime if Orchestrator type hints are needed
if TYPE_CHECKING:
    from jiki.orchestrator import JikiOrchestrator
    from jiki.logging import TraceLogger

from jiki.models.response import DetailedResponse

# Add json_serializer_default to handle non-serializable types for json.dumps
def json_serializer_default(o: Any) -> Any:
    """Handles common non-serializable types for json.dumps."""
    if isinstance(o, (datetime, date)):
        return o.isoformat()  # Convert datetimes/dates to ISO string
    elif isinstance(o, set):
        return list(o)  # Convert sets to lists
    elif isinstance(o, bytes):
        try:
            return o.decode('utf-8')  # Try decoding bytes as UTF-8
        except UnicodeDecodeError:
            return repr(o)  # Fallback for non-UTF8 bytes
    # Add checks for common patterns in custom objects
    elif hasattr(o, 'to_dict') and callable(o.to_dict):
        try:
            return o.to_dict()
        except Exception:
            pass
    elif hasattr(o, 'model_dump') and callable(o.model_dump):  # Pydantic V2
        try:
            return o.model_dump()
        except Exception:
            pass
    elif hasattr(o, 'dict') and callable(o.dict):  # Pydantic V1
        try:
            return o.dict()
        except Exception:
            pass
    elif hasattr(o, '__dict__'):
        try:
            return o.__dict__
        except Exception:
            pass
    # Final fallback: return representation
    return repr(o)

def _attach_helper_methods(orchestrator: 'JikiOrchestrator', logger: Optional['TraceLogger']):
    """Attach helper methods (sync wrappers, UI launchers, etc.) to the orchestrator instance."""
    
    # Note: These methods are defined *inside* _attach_helper_methods 
    # so they have access to the 'orchestrator' and 'logger' variables 
    # from the outer scope when they are defined. When attached via 
    # types.MethodType, 'self' will correctly refer to the orchestrator instance.

    # --- Synchronous `process` wrapper ---
    def process(self: 'JikiOrchestrator', user_input: str) -> str:
        """Synchronous wrapper for process_user_input."""
        # asyncio.run handles loop creation/management.
        return asyncio.run(self.process_user_input(user_input))

    # --- Async `process_detailed` ---
    async def process_detailed_async(self: 'JikiOrchestrator', user_input: str) -> DetailedResponse:
        """Process input and return DetailedResponse with result, tool calls, and traces."""
        # Core logic already triggers _reset_last_tool_calls if needed
        result = await self.process_user_input(user_input) 
        
        tool_calls_list = getattr(self, "_last_tool_calls", []) # Get calls recorded during process_user_input
        
        traces_list = None
        if logger and hasattr(logger, 'get_current_traces'):
            traces_list = logger.get_current_traces() # Get traces from the logger

        return DetailedResponse(
            result=result,
            tool_calls=tool_calls_list,
            traces=traces_list
        )

    # --- Synchronous `process_detailed` wrapper ---
    def process_detailed(self: 'JikiOrchestrator', user_input: str) -> DetailedResponse:
        """Synchronous wrapper for process_detailed_async."""
        # asyncio.run handles loop creation/management.
        return asyncio.run(self.process_detailed_async(user_input))

    # --- Trace Export ---
    def export_traces(self: 'JikiOrchestrator', filepath: Optional[str] = None):
        """Export interaction traces recorded by the logger to a file."""
        if not logger or not hasattr(logger, 'save_all_traces'):
            raise RuntimeError("Tracing is not enabled or logger does not support saving traces.")
        logger.save_all_traces(filepath) # filepath=None uses default

    # --- UI Runner ---
    def run_ui(self: 'JikiOrchestrator', frontend: str = 'cli', **kwargs: Any):
        """Run a built-in UI for interacting with the orchestrator."""
        if frontend == 'cli':
            try:
                # Import locally to avoid potential startup cost / circular dependency
                from jiki.cli import _run_interactive_loop 
                _run_interactive_loop(self) # Pass the orchestrator instance (self)
            except ImportError:
                print("[ERROR] Could not import _run_interactive_loop from jiki.cli.", file=sys.stderr)
            except Exception as e:
                 print(f"[ERROR] Failed to run CLI frontend: {e}", file=sys.stderr)
                 
        elif frontend == 'streamlit':
            print("[ERROR] Streamlit frontend not yet implemented.", file=sys.stderr)
            # Example future implementation:
            # try:
            #     from .streamlit_runner import run_streamlit_app # Assuming streamlit_runner.py exists
            #     run_streamlit_app(self, **kwargs) # Pass orchestrator instance
            # except ImportError:
            #     print("[ERROR] Streamlit requires 'streamlit'. pip install streamlit", file=sys.stderr)
            # except Exception as e:
            #     print(f"[ERROR] Failed to run Streamlit frontend: {e}", file=sys.stderr)
                 
        else:
            raise ValueError(f"Unsupported frontend type: '{frontend}'. Available: 'cli'")

    # --- Attach all defined methods ---
    orchestrator.process = types.MethodType(process, orchestrator)
    orchestrator.process_detailed_async = types.MethodType(process_detailed_async, orchestrator)
    orchestrator.process_detailed = types.MethodType(process_detailed, orchestrator)
    orchestrator.export_traces = types.MethodType(export_traces, orchestrator)
    orchestrator.run_ui = types.MethodType(run_ui, orchestrator) 