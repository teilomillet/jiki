#!/usr/bin/env python3
"""
custom_tools_server.py

Simple FastMCP server implementing the 'concat' tool.
"""

from fastmcp import FastMCP

mcp = FastMCP("CustomTools")

@mcp.tool()
def concat(a: str, b: str) -> str:
    """Concatenate two strings"""
    return a + b

if __name__ == "__main__":
    mcp.run() 