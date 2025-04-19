#!/usr/bin/env python3
"""
Custom Transport Example: SSE & Resource Listing

This script demonstrates:
1. Using SSE transport to connect to an MCP server by URL.
2. Listing and reading resources via the MCP client.
3. Running a simple query with available resources.
"""

import asyncio
from jiki import Jiki


def example_sse_resources():
    # Create orchestrator (try auto-discovery; fallback to manual tools.json)
    try:
        orchestrator = Jiki(
            auto_discover_tools=True,
            mcp_mode="sse",
            mcp_script_path="http://localhost:8000/mcp",
            trace=True
        )
    except Exception as e:
        print(f"[WARN] SSE discovery failed, falling back to stdio and tools.json: {e}")
        orchestrator = Jiki(
            tools="tools.json",
            mcp_mode="stdio",
            mcp_script_path="servers/calculator_server.py",
            trace=True
        )

    # List available resources (gracefully handle connectivity issues)
    try:
        resources = asyncio.run(orchestrator.mcp_client.list_resources())
    except Exception as e:
        print(f"[WARN] Could not list resources: {e}")
        resources = []
    print("[Resources] Available resources:")
    for res in resources:
        print(f"- {res.get('uri')}: {res.get('description') or ''}")

    # Read content of the first resource if present (handle failures)
    if resources:
        uri = resources[0]['uri']
        try:
            contents = asyncio.run(orchestrator.mcp_client.read_resource(uri))
        except Exception as e:
            print(f"[WARN] Could not read resource {uri}: {e}")
            contents = []
        print(f"[Resources] Contents of {uri}:")
        for chunk in contents:
            print(chunk.get('text', '')[:200])

    # Demonstrate direct tool invocation via MCP client (RPC call)
    try:
        sum_result = asyncio.run(orchestrator.mcp_client.execute_tool_call("add", {"a": 10, "b": 5}))
        print(f"[RPC add] 10 + 5 = {sum_result}")
    except Exception as e:
        print(f"[WARN] Could not perform RPC tool call: {e}")


if __name__ == "__main__":
    example_sse_resources() 