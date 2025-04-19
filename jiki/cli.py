#!/usr/bin/env python3
"""
Jiki Command Line Interface (CLI)

Provides commands for running interactive sessions, processing single queries,
and managing interaction traces.
"""

import argparse
import sys
import json
import os

# Import Jiki factory here, just before it's needed
from . import Jiki 
from .orchestrator import JikiOrchestrator
from .logging import TraceLogger # Needed for trace export command
from .models.response import DetailedResponse # Needed for type hint

# Helper functions

def _load_tools_from_arg(tools_arg: str) -> list:
    """Load tools config from file path or parse as inline JSON."""
    if not tools_arg:
        return []
    if os.path.exists(tools_arg):
        try:
            with open(tools_arg, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tools file {tools_arg}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading tools file {tools_arg}: {e}")
    else:
        # Try parsing as inline JSON list
        try:
            tools_list = json.loads(tools_arg)
            if not isinstance(tools_list, list):
                raise ValueError("Inline tools must be a JSON list of objects.")
            return tools_list
        except json.JSONDecodeError:
            raise ValueError(f"Invalid tools argument: '{tools_arg}'. Not a valid file path or inline JSON list.")

def _get_stdin_query() -> str:
    """Read query from standard input."""
    if sys.stdin.isatty():
        print("Enter query (press Ctrl+D to end):", file=sys.stderr)
    return sys.stdin.read().strip()


def _handle_orchestrator_creation(**kwargs) -> 'JikiOrchestrator':
    """Handles common orchestrator creation logic and errors."""
    try:
        # Use the new Jiki factory function
        orchestrator = Jiki(**kwargs)
        return orchestrator
    except (ValueError, FileNotFoundError, RuntimeError, ConnectionError) as e:
        print(f"[ERROR] Failed to initialize Jiki: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during initialization: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() # Print stack trace for unexpected errors
        sys.exit(1)

# --- Command Functions --- 

def run_command(args):
    """Runs the interactive CLI loop."""
    print("[INFO] Starting interactive session...", file=sys.stderr)
    
    tools_config = _load_tools_from_arg(args.tools) if args.tools else None
    
    orchestrator = _handle_orchestrator_creation(
        model=args.model, # Can be None, Jiki() uses default
        tools=tools_config, # Can be None or empty list
        auto_discover_tools=args.auto_discover,
        mcp_mode=args.mcp_mode,
        mcp_script_path=args.mcp_script_path,
        mcp_url=args.mcp_url,
        trace=True, # Always trace interactive sessions
        trace_dir=args.trace_dir # Can be None, Jiki() uses default
    )
    
    # run_ui is attached by Jiki()
    orchestrator.run_ui(frontend='cli')
    print("[INFO] Interactive session ended.", file=sys.stderr)

def process_command(args):
    """Processes a single query non-interactively."""
    query = args.query or _get_stdin_query()
    if not query:
        print("[ERROR] No query provided via argument or stdin.", file=sys.stderr)
        sys.exit(1)
        
    tools_config = _load_tools_from_arg(args.tools) if args.tools else None
    
    orchestrator = _handle_orchestrator_creation(
        model=args.model,
        tools=tools_config,
        auto_discover_tools=args.auto_discover,
        mcp_mode=args.mcp_mode,
        mcp_script_path=args.mcp_script_path,
        mcp_url=args.mcp_url,
        trace=args.trace,
        trace_dir=args.trace_dir
    )

    try:
        if args.detailed:
            response: DetailedResponse = orchestrator.process_detailed(query)
            output_data = response.to_dict(include_tool_calls=args.show_tools, include_traces=args.show_traces)
            if args.json:
                print(json.dumps(output_data, indent=2))
            else:
                # Pretty print detailed non-JSON output
                print(f"Result: {output_data['result']}")
                if args.show_tools and output_data['tool_calls']:
                    print("\nTool Calls:")
                    for call in output_data['tool_calls']:
                        print(f"  - Tool: {call['tool_name']}")
                        print(f"    Args: {json.dumps(call['arguments'])}")
                        print(f"    Result: {call['result']}")
                if args.show_traces and output_data['traces']:
                    print("\nTraces:")
                    for i, trace in enumerate(output_data['traces']):
                         print(f"  Trace {i+1}: {json.dumps(trace)}") # Basic trace printing
        else:
            result = orchestrator.process(query)
            print(result)
            
        # Explicitly save traces if tracing was enabled for this single run
        if args.trace:
             orchestrator.export_traces(None) # Use default path/naming
             
    except Exception as e:
        print(f"[ERROR] Failed during processing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def trace_command(args):
    """Handles trace management actions."""
    if args.action == "export":
        print(f"[INFO] Exporting traces to {args.output}...", file=sys.stderr)
        try:
            # We need a TraceLogger instance. We can get one by creating a dummy orchestrator
            # with tracing enabled, assuming the default trace_dir is where traces are.
            # Alternatively, instantiate TraceLogger directly if we know the dir.
            # Let's try instantiating directly for simplicity here.
            # NOTE: This assumes traces were saved to the default dir by previous runs.
            # A more robust CLI might store the trace_dir path used by runs.
            logger = TraceLogger(trace_dir=None) # Use default trace dir
            logger.load_traces() # Load existing traces from default dir
            count = logger.save_all_traces(args.output) # Save loaded traces to specified file
            print(f"[INFO] Exported {count} trace(s).")
        except FileNotFoundError:
             print(f"[ERROR] No trace directory found or trace file does not exist in the default location. Ensure tracing was enabled in previous runs.", file=sys.stderr)
             sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to export traces: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"[ERROR] Unknown trace action: {args.action}", file=sys.stderr)
        sys.exit(1)

def _run_interactive_loop(orchestrator):
    """Interactive CLI loop for Jiki orchestrator."""
    try:
        while True:
            try:
                user_input = input(">> ")
            except EOFError:
                # Exit on EOF (Ctrl-D)
                break
            # Strip whitespace
            user_input = user_input.strip()
            if not user_input:
                continue
            # Exit commands
            if user_input.lower() in ("exit", "quit"):
                break
            # Process input and print result
            try:
                result = orchestrator.process(user_input)
                print(result)
            except Exception as e:
                print(f"[ERROR] Exception during processing: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        # Exit on Ctrl-C
        pass
    finally:
        # Export traces on exit
        try:
            orchestrator.export_traces()
        except Exception:
            pass

# --- Argument Parser Setup --- 

def main():
    """Main CLI entrypoint using argparse."""
    parser = argparse.ArgumentParser(
        description="Jiki: LLM Orchestration Framework CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run", required=True)

    # --- Common arguments --- 
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--model", "-m", help="Model name (e.g., 'anthropic/claude-3-haiku-20240307'). Uses default if omitted.")
    common_parser.add_argument("--trace-dir", help="Directory to store interaction traces (default: ./interaction_traces)")
    
    mcp_group = common_parser.add_argument_group("MCP Connection")
    mcp_group.add_argument("--mcp-mode", choices=["stdio", "sse"], default="stdio", help="MCP transport mode (default: stdio)")
    mcp_group.add_argument("--mcp-script-path", help="Path to MCP server script (for stdio mode)")
    mcp_group.add_argument("--mcp-url", help="URL of MCP server (for sse mode)")

    tools_group = common_parser.add_argument_group("Tool Configuration")
    tools_mutex_group = tools_group.add_mutually_exclusive_group()
    tools_mutex_group.add_argument("--tools", "-t", help="Tools config: path to JSON file or inline JSON list. Cannot be used with --auto-discover.")
    tools_mutex_group.add_argument("--auto-discover", "-a", action="store_true", help="Auto-discover tools from MCP server. Cannot be used with --tools.")

    # --- Run command --- 
    run_parser = subparsers.add_parser("run", help="Run an interactive chat session", parents=[common_parser])
    # run command implies tracing, but allow setting dir
    run_parser.set_defaults(func=run_command)

    # --- Process command --- 
    process_parser = subparsers.add_parser("process", help="Process a single query non-interactively", parents=[common_parser])
    process_parser.add_argument("query", nargs="?", help="Query text (reads from stdin if omitted)")
    process_parser.add_argument("--trace", action="store_true", help="Enable interaction tracing for this run")
    
    detailed_group = process_parser.add_argument_group("Detailed Output")
    detailed_group.add_argument("--detailed", "-d", action="store_true", help="Output detailed response object instead of just the result string")
    detailed_group.add_argument("--show-tools", action="store_true", help="Include tool calls in detailed output (requires --detailed)")
    detailed_group.add_argument("--show-traces", action="store_true", help="Include raw traces in detailed output (requires --detailed)")
    detailed_group.add_argument("--json", "-j", action="store_true", help="Output detailed response in JSON format (requires --detailed)")
    process_parser.set_defaults(func=process_command)

    # --- Trace command --- 
    trace_parser = subparsers.add_parser("trace", help="Manage interaction traces")
    trace_subparsers = trace_parser.add_subparsers(dest="action", help="Trace action", required=True)
    export_parser = trace_subparsers.add_parser("export", help="Export accumulated traces from the default trace directory to a file")
    export_parser.add_argument("--output", "-o", required=True, help="Output file path (e.g., traces.jsonl)")
    export_parser.set_defaults(func=trace_command)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main() 