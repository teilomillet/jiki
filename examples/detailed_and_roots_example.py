#!/usr/bin/env python3
"""
Detailed & Roots Example: list roots, send roots_list_changed, process_detailed usage

This script demonstrates:
1. Listing and notifying roots changes via the MCP client
2. Using the synchronous `process_detailed` wrapper to get a DetailedResponse
3. Inspecting the result, tool calls, and raw traces for deeper analysis
"""
import asyncio
from jiki import Jiki
import json


def detailed_and_roots_example():
    # Initialize orchestrator with tracing and tool discovery
    orchestrator = Jiki(
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        trace=True
    )

    # 1. List available roots
    try:
        roots = asyncio.run(orchestrator.mcp_client.list_roots())
        print("[Roots] Available roots:")
        for root in roots:
            print(f"- {root.get('uri')}: {root.get('name')}")
    except Exception as e:
        print(f"[WARN] Could not list roots: {e}")

    # 2. Send roots list changed notification
    try:
        asyncio.run(orchestrator.mcp_client.send_roots_list_changed())
        print("[Roots] Sent roots list changed notification to server.")
    except Exception as e:
        print(f"[WARN] Failed to send roots notification: {e}")

    # 3. Use process_detailed to get a DetailedResponse with traces and tool calls
    query = "What is 8 + 5?"
    print(f"\n[Query] {query}")
    detailed_resp = orchestrator.process_detailed(query)

    print("\n[Detailed Response] result:", detailed_resp.result)
    print("[Detailed Response] tool_calls:", detailed_resp.tool_calls)
    print("[Detailed Response] raw traces:")
    print(json.dumps(detailed_resp.traces, indent=2, default=str))


if __name__ == "__main__":
    detailed_and_roots_example()