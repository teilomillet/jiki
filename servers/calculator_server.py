from fastmcp import FastMCP
import mcp.types as types  # Import types for roots

mcp = FastMCP("Calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract b from a"""
    return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
def divide(a: int, b: int) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# NOTE: FastMCP currently does not expose a server‑side decorator for roots listing.
# The MCP spec defines `roots/list` as a *client* capability, so servers generally
# do not implement a handler.  If future FastMCP versions add such support, we
# can uncomment and update the block below accordingly.

# Example (future‑looking):
# @mcp.list_roots()
# async def list_roots() -> list[types.Root]:
#     """List available roots for Calculator service"""
#     return [
#         types.Root(uri="calculator://root", name="Calculator Root")
#     ]

# Expose a simple static resource. FastMCP automatically includes resources
# defined with the @mcp.resource decorator in the `resources/list` response.
@mcp.resource("config://calculator")
def calculator_config() -> str:
    """Return JSON configuration for the calculator server."""
    return '{"precision": 2}'

if __name__ == "__main__":
    # Run the server. Transport and port configuration should be handled
    # by the command-line runner (e.g., `fastmcp run --transport sse --port 8000`).
    mcp.run() 