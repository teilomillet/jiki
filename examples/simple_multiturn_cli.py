#!/usr/bin/env python3
"""
Minimal example launching Jiki's interactive CLI programmatically via Auto-Discovery
----------------------------------------------------------------------------------
This script shows the simplest way to create a Jiki orchestrator 
using auto-discovery of tools from a server and launch the 
built-in command-line UI using the `.run_ui()` method.

It uses the default model and discovers tools from the default calculator server.

Run:
    # Ensure the calculator server is runnable from the servers/ directory
    python examples/simple_multiturn_cli.py

Exit the chat with Ctrl-D, Ctrl-C, or by typing `exit`.
"""

import sys

# Only need Jiki from the library
from jiki import Jiki

def main():
    try:
        # 1. Create the orchestrator instance using auto-discovery
        print("[INFO] Using default model and discovering tools from servers/calculator_server.py...", file=sys.stderr)
        orchestrator = Jiki(
            # model="anthropic/claude-3-7-sonnet-latest", # Use default from Jiki
            # tools=... # Tools are discovered, so this argument is omitted
            trace=True, # Interactive mode implies tracing
            # trace_dir=None, # Use default from Jiki
            auto_discover_tools=True, # Discover tools from the server
            mcp_script_path="servers/calculator_server.py", # Specify the server script path
            mcp_mode="stdio", # Default mode
        )

        # 2. Launch the built-in CLI frontend
        orchestrator.run_ui(frontend='cli')

    except (ValueError, FileNotFoundError, RuntimeError) as e:
        # Catch errors during orchestrator creation (e.g., discovery failure) or UI launch
        print(f"[ERROR] Failed to start Jiki: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 