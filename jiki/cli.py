import argparse
import asyncio
import os
import sys
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple

# Import other needed components, but NOT create_jiki here
from .orchestrator import JikiOrchestrator
from .tools.tool import Tool
from .models.response import DetailedResponse, ToolCall
# We still need create_jiki, but will import it later
# from . import create_jiki 

def process_command(args):
    """Handle the process command."""
    # Import create_jiki here, just before it's needed
    from . import create_jiki
    
    # Read from stdin if no query
    query = args.query
    if not query and not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    
    if not query:
        print("Error: No query provided.", file=sys.stderr)
        sys.exit(1)
        
    # Process tools argument
    tools_arg = args.tools
    tools_input = None
    if tools_arg:
        # Check if it's a file path first
        if os.path.exists(tools_arg):
            tools_input = tools_arg
        else:
            # Assume comma-separated list of names or inline JSON
            try:
                # Is it a JSON list?
                tools_input = json.loads(tools_arg)
            except json.JSONDecodeError:
                # Assume comma-separated names
                tools_input = tools_arg.split(',')
                
    # Create orchestrator
    try:
        orchestrator = create_jiki(
            model=args.model if args.model else "anthropic/claude-3-7-sonnet-latest",
            tools=tools_input,
            trace=args.trace
            # Add other args like mcp_mode, mcp_script_path if needed based on args
        )
    except ValueError as e:
        print(f"Error creating orchestrator: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
         print(f"Error loading tools: {e}", file=sys.stderr)
         sys.exit(1)
         
    # Process query
    try:
        if args.detailed:
            response = orchestrator.process_detailed(query)
            if args.json:
                print(json.dumps({
                    "result": response.result,
                    "tool_calls": [
                        {"tool": tc.tool, "arguments": tc.arguments, "result": tc.result}
                        for tc in response.tool_calls
                    ]
                    # Optionally add traces if needed
                }, indent=2))
            else:
                print(response.result)
                if args.show_tools and response.tool_calls:
                    print("\n--- Tool Calls ---")
                    for tc in response.tool_calls:
                        print(f"- Tool: {tc.tool}")
                        print(f"  Args: {tc.arguments}")
                        print(f"  Result: {tc.result}")
        else:
            result = orchestrator.process(query)
            print(result)
    except Exception as e:
        print(f"Error during processing: {e}", file=sys.stderr)
        sys.exit(1)

def trace_command(args):
    """Handle the trace command."""
    # Import create_jiki here, just before it's needed
    from . import create_jiki
        
    if args.action == "export":
        # Create a dummy orchestrator just to access logger/traces
        # This assumes create_jiki sets up logging even if not processing
        try:
            # Need trace=True to ensure logger is created by create_jiki
            orchestrator = create_jiki(trace=True) 
            orchestrator.export_traces(args.output)
        except RuntimeError as e:
             print(f"Error exporting traces: {e}", file=sys.stderr)
             sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during trace export: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown trace action: {args.action}", file=sys.stderr)
        sys.exit(1)

def run_interactive_cli(args):
    """Run the interactive command-line interface (similar to old run_cli)."""
    # Import create_jiki here, just before it's needed
    from . import create_jiki
    
    print("Jiki orchestrator CLI (interactive). Type your question or 'exit' to quit.")
    
    # Process tools argument (similar to process_command)
    tools_arg = args.tools
    tools_input = None
    if tools_arg:
        if os.path.exists(tools_arg):
            tools_input = tools_arg
        else:
            try:
                tools_input = json.loads(tools_arg)
            except json.JSONDecodeError:
                tools_input = tools_arg.split(',')
                
    # Create orchestrator
    try:
        orchestrator = create_jiki(
            model=args.model if args.model else "anthropic/claude-3-7-sonnet-latest",
            tools=tools_input,
            trace=True # Always trace in interactive mode?
        )
    except ValueError as e:
        print(f"Error creating orchestrator: {e}", file=sys.stderr)
        return
    except FileNotFoundError as e:
         print(f"Error loading tools: {e}", file=sys.stderr)
         return
         
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() == "exit":
                print("Exiting interactive mode.")
                # Optionally save traces on exit
                try:
                    orchestrator.export_traces(None) # Use default path
                except RuntimeError:
                    pass # Tracing might not have been enabled or no traces
                break
            
            # Use the simple process method for interactive mode
            result = orchestrator.process(user_input)
            print(f"Jiki: {result}")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive mode.")
            # Optionally save traces on exit
            try:
                orchestrator.export_traces(None)
            except RuntimeError:
                pass
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main CLI entrypoint using argparse."""
    parser = argparse.ArgumentParser(description="Jiki: LLM Orchestration Framework")
    subparsers = parser.add_subparsers(dest="command", help="Command to run", required=True)
    
    # --- Process command --- 
    process_parser = subparsers.add_parser("process", help="Process a query non-interactively")
    process_parser.add_argument("query", nargs="?", help="Query to process (reads from stdin if omitted)")
    process_parser.add_argument("--model", "-m", help="Model to use (e.g., anthropic/claude-3-...) Default: Claude 3.7 Sonnet")
    process_parser.add_argument("--tools", "-t", help="Tools configuration: path to JSON file, comma-separated names, or inline JSON list")
    process_parser.add_argument("--trace", action="store_true", help="Enable interaction tracing")
    process_parser.add_argument("--detailed", "-d", action="store_true", help="Output detailed response object")
    process_parser.add_argument("--show-tools", "-s", action="store_true", help="Show tool calls in detailed output (requires --detailed)")
    process_parser.add_argument("--json", "-j", action="store_true", help="Output detailed response in JSON format (requires --detailed)")
    process_parser.set_defaults(func=process_command)
    
    # --- Trace command --- 
    trace_parser = subparsers.add_parser("trace", help="Manage interaction traces")
    trace_subparsers = trace_parser.add_subparsers(dest="action", help="Trace action", required=True)
    export_parser = trace_subparsers.add_parser("export", help="Export accumulated traces to a file")
    export_parser.add_argument("--output", "-o", required=True, help="Output file path (e.g., traces.json or traces.jsonl)")
    # Output format is inferred from extension in logger
    # export_parser.add_argument("--format", "-f", choices=["json", "jsonl"], default="json", help="Output format") 
    export_parser.set_defaults(func=trace_command)
    
    # --- Run command (interactive mode) --- 
    run_parser = subparsers.add_parser("run", help="Run Jiki in interactive mode")
    run_parser.add_argument("--model", "-m", help="Model to use. Default: Claude 3.7 Sonnet")
    run_parser.add_argument("--tools", "-t", help="Tools configuration: path to JSON file, comma-separated names, or inline JSON list")
    # Trace is implicitly enabled in interactive mode for now
    run_parser.set_defaults(func=run_interactive_cli)
    
    args = parser.parse_args()
    
    # Call the function associated with the chosen subcommand
    args.func(args)

# This allows running `python -m jiki.cli ...`
if __name__ == "__main__":
    main() 