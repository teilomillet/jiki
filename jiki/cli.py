import argparse
import os
import sys
import json

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

def _run_interactive_loop(orchestrator):
    """Core interactive chat loop logic."""
    print("Jiki multi-turn CLI. Type your message, or 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()  # newline after ^C/^D
            break

        if not user_input or user_input.lower() == "exit":
            break

        try:
            response = orchestrator.process(user_input)
            # Add a newline for better spacing in interactive mode
            print(f"Jiki: {response}\n") 
        except Exception as e:
            # Print error clearly and continue loop
            print(f"[ERROR] {e}\n", file=sys.stderr) 

    # Save traces (if tracing enabled in orchestrator)
    print("Exiting interactive mode.")
    try:
        # Default path (None) uses configured trace_dir or default
        orchestrator.export_traces(None) 
    except RuntimeError as e:
        # Handle case where tracing might not have been enabled or no traces logged
        print(f"[INFO] Could not export traces: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Unexpected error exporting traces: {e}", file=sys.stderr)

def run_interactive_cli(args):
    """Set up and run the interactive command-line interface."""
    # Import create_jiki here, just before it's needed
    from . import create_jiki

    # Process tools argument (reusing logic, could be refactored)
    tools_arg = args.tools
    tools_input = None
    if tools_arg:
        # Is it a filepath?
        if os.path.exists(tools_arg):
            tools_input = tools_arg
        else:
            # Try inline JSON list
            try:
                tools_input = json.loads(tools_arg)
            except json.JSONDecodeError:
                # Fallback: comma-separated names
                # Consider adding default tool lookup here if desired
                tools_input = tools_arg.split(',')
    else:
        # Add sensible defaults if no tools specified for interactive mode
        # Match the defaults from the old example for consistency
        tools_input = ["add", "subtract", "multiply", "divide"]
        print("[INFO] No tools specified, using default calculator tools.", file=sys.stderr)

    # Create orchestrator
    try:
        orchestrator = create_jiki(
            model=args.model if args.model else "anthropic/claude-3-7-sonnet-latest",
            tools=tools_input,
            trace=True, # Always trace in interactive mode
            trace_dir=args.trace_dir # Pass trace_dir argument
        )
    except ValueError as e:
        print(f"Error creating orchestrator: {e}", file=sys.stderr)
        sys.exit(1) # Exit if orchestrator fails
    except FileNotFoundError as e:
         print(f"Error loading tools: {e}", file=sys.stderr)
         sys.exit(1) # Exit if tools file not found
    except Exception as e: # Catch other potential errors during creation
         print(f"Unexpected error creating orchestrator: {e}", file=sys.stderr)
         sys.exit(1)

    # Start the interactive loop using the new method
    orchestrator.run_ui(frontend='cli')

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
    run_parser.add_argument("--tools", "-t", help="Tools configuration: path to JSON file, comma-separated names, or inline JSON list. Defaults to calculator tools.")
    run_parser.add_argument("--trace-dir", help="Directory to save interaction traces (defaults to interaction_traces/)")
    # Trace is implicitly enabled in interactive mode
    run_parser.set_defaults(func=run_interactive_cli)
    
    args = parser.parse_args()
    
    # Call the function associated with the chosen subcommand
    args.func(args)

# This allows running `python -m jiki.cli ...`
if __name__ == "__main__":
    main() 