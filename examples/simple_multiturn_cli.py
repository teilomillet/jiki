#!/usr/bin/env python3
"""
Simple Multi‑turn CLI using Jiki orchestrator
-------------------------------------------
This example starts an interactive shell where you can chat with Jiki.
The orchestrator decides, via the underlying LLM, whether to call tools or
respond directly. All interaction traces (including tool calls, thoughts, and
results) are logged to the default `interaction_traces/` directory so they can
later be used for RL training.

Run:
    python examples/simple_multiturn_cli.py --tools add,subtract
    # or use a JSON file describing tools
    python examples/simple_multiturn_cli.py --tools tools.json

Exit the chat with Ctrl‑D or by typing `exit`.
"""

import argparse
import json
import os
import sys

from jiki import create_jiki


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple multi‑turn CLI demonstrating Jiki tool use"
    )
    parser.add_argument(
        "--tools",
        "-t",
        help=(
            "Tools configuration: path to JSON file, comma‑separated names, "
            "or inline JSON list. Defaults to built‑in calculator tools."
        ),
    )
    parser.add_argument(
        "--model",
        "-m",
        default="anthropic/claude-3-7-sonnet-latest",
        help="LLM model to use",
    )
    parser.add_argument(
        "--trace-dir",
        help="Directory where interaction traces will be saved (defaults to interaction_traces/)",
    )
    return parser


def parse_tools_arg(tools_arg):
    """Convert CLI `--tools` value to the format expected by create_jiki."""
    if not tools_arg:
        return ["add", "subtract", "multiply", "divide"]  # sensible defaults

    # Is it a filepath?
    if os.path.exists(tools_arg):
        return tools_arg  # create_jiki will load JSON file

    # Try inline JSON list
    try:
        return json.loads(tools_arg)
    except json.JSONDecodeError:
        # Fallback: comma‑separated names
        return tools_arg.split(",")


def chat_loop(orchestrator):
    """Run an interactive chat loop until the user exits."""
    print("Jiki multi‑turn CLI. Type your message, or 'exit' to quit.")
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
            print(f"Jiki: {response}\n")
        except Exception as e:
            print(f"[ERROR] {e}")

    # Save traces (if tracing enabled)
    try:
        orchestrator.export_traces(None)  # default path
    except Exception:
        pass


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    tools_cfg = parse_tools_arg(args.tools)

    orchestrator = create_jiki(
        model=args.model,
        tools=tools_cfg,
        trace=True,
        trace_dir=args.trace_dir,
    )

    chat_loop(orchestrator)


if __name__ == "__main__":
    main() 