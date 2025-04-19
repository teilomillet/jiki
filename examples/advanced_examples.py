#!/usr/bin/env python3
"""
Advanced Examples: Manual Tools, Sampling Config, Snapshot/Resume

This script consolidates three advanced usage patterns:
1. Manual tools configuration using a local JSON tools file
2. Custom sampling parameters via SamplerConfig
3. Conversation snapshot and resume functionality
"""

from jiki import Jiki, SamplerConfig
# Define a single JSONL file for all example traces
TRACE_FILE = "advanced_examples_traces.jsonl"

# Example 1: Manual tools configuration
# Uses the existing tools.json and calculator_server.py

def example_manual_tools():
    orchestrator = Jiki(
        tools="tools.json", # Specify path to tools definition
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        auto_discover_tools=False, # Disable auto-discovery
        trace=True
    )
    result = orchestrator.process("What is 7 * 6?")
    print("[Manual Tools] 7 * 6 =", result)
    orchestrator.export_traces(TRACE_FILE)

# Example 2: Custom sampling configuration
def example_custom_sampling():
    custom_sampler = SamplerConfig(temperature=0.1, top_p=0.8, max_tokens=50)
    orchestrator = Jiki(
        sampler_config=custom_sampler,
        auto_discover_tools=True, # Use auto-discovery for tools
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        trace=True
    )
    result = orchestrator.process("Give me a short sentence about clouds.")
    print("[Custom Sampling] Cloud sentence:", result)
    orchestrator.export_traces(TRACE_FILE)


# Example 3: Conversation Snapshot and Resume
# Uses a simple in-memory root manager for demonstration
from jiki.roots.conversation_root_manager import IConversationRootManager
from typing import Any

class SimpleMemoryRootManager(IConversationRootManager):
    _state: Any = None
    def snapshot(self) -> Any:
        print("[RootManager] Snapshotting state...")
        self._state = "Conversation snapshot data"
        return self._state
    def resume(self, snapshot: Any) -> None:
        print(f"[RootManager] Resuming state from: {snapshot}")
        self._state = snapshot

def example_snapshot_resume():
    root_manager = SimpleMemoryRootManager()
    
    # First orchestrator instance
    orchestrator1 = Jiki(
        conversation_root_manager=root_manager,
        auto_discover_tools=True,
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        trace=True
    )
    print("\n[Snapshot/Resume] First interaction...")
    orchestrator1.process("My favorite number is 17.")
    # Assume snapshot is implicitly called by root_manager logic or manually
    saved_state = root_manager.snapshot() 
    orchestrator1.export_traces(TRACE_FILE)

    # Second orchestrator instance, resuming state
    print("\n[Snapshot/Resume] Creating second instance and resuming...")
    orchestrator2 = Jiki(
        conversation_root_manager=root_manager, # Re-use the same manager instance
        auto_discover_tools=True, 
        mcp_script_path="servers/calculator_server.py",
        mcp_mode="stdio",
        trace=True
    )
    # Manually trigger resume (in real app, this might happen on load)
    root_manager.resume(saved_state)
    print("\n[Snapshot/Resume] Second interaction (should know favorite number)...")
    result = orchestrator2.process("What is my favorite number plus 3?")
    print("[Snapshot/Resume] Result:", result) # Should ideally use 17
    orchestrator2.export_traces(TRACE_FILE)


if __name__ == "__main__":
    print("--- Running Manual Tools Example ---")
    example_manual_tools()
    print("\n--- Running Custom Sampling Example ---")
    example_custom_sampling()
    print("\n--- Running Snapshot/Resume Example ---")
    example_snapshot_resume() 