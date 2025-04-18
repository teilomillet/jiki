#!/usr/bin/env python3
"""
Advanced Examples: Manual Tools, Sampling Config, Snapshot/Resume

This script consolidates three advanced usage patterns:
1. Manual tools configuration using a local JSON tools file
2. Custom sampling parameters via SamplerConfig
3. Conversation snapshot and resume functionality
"""

from jiki import create_jiki, SamplerConfig

# Example 1: Manual tools configuration
# Uses the existing tools.json and calculator_server.py

def example_manual_tools():
    orchestrator = create_jiki(
        tools="tools.json",
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        trace=True
    )
    result = orchestrator.process("What is 7 * 6?")
    print("[Manual Tools] 7 * 6 =", result)

# Example 2: Custom sampling parameters
# Adjust temperature and top_p for the LLM

def example_sampling_config():
    sample_cfg = SamplerConfig(temperature=0.5, top_p=0.9)
    orchestrator = create_jiki(
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        sampler_config=sample_cfg,
        trace=True
    )
    result = orchestrator.process("Tell me a short poem about the number 5.")
    print("[Sampling Config] Poem:\n", result)

# Example 3: Conversation snapshot and resume
# Capture state mid-conversation and resume later

def example_snapshot_resume():
    orchestrator = create_jiki(
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        trace=True
    )
    first = orchestrator.process("What is 10 + 5?")
    print("[Snapshot/Resume] First result =", first)
    snapshot = orchestrator.snapshot()

    second = orchestrator.process("Multiply the result by 2.")
    print("Second result =", second)

    # Create a fresh orchestrator and restore to the previous snapshot
    orchestrator2 = create_jiki(
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        trace=True
    )
    orchestrator2.resume(snapshot)
    third = orchestrator2.process("Add 3 to the original result.")
    print("Resumed result =", third)

if __name__ == "__main__":
    print("=== Example 1: Manual Tools ===")
    example_manual_tools()
    print("\n=== Example 2: Sampling Config ===")
    example_sampling_config()
    print("\n=== Example 3: Snapshot/Resume ===")
    example_snapshot_resume() 