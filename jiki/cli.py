import asyncio
import json
import os
import datetime
from typing import Optional

class JikiCLI:
    """Command-line interface for Jiki"""
    
    def __init__(self, orchestrator, mcp_client, logger=None):
        """
        Initialize the CLI with the necessary components
        
        :param orchestrator: JikiOrchestrator instance
        :param mcp_client: MCP client instance (EnhancedMCPClient)
        :param logger: Optional TraceLogger for recording interactions
        """
        self.orchestrator = orchestrator
        self.mcp_client = mcp_client
        self.logger = logger

    def save_interaction_traces(self, traces, conversation_history):
        """Save interaction traces and conversation history to files for training data."""
        if not traces:
            print("No interaction traces to save.")
            return
            
        # Create a directory for traces if it doesn't exist
        traces_dir = "interaction_traces"
        os.makedirs(traces_dir, exist_ok=True)
        
        # Generate a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save the interaction traces
        traces_file = os.path.join(traces_dir, f"traces_{timestamp}.json")
        with open(traces_file, "w") as f:
            json.dump(traces, f, indent=2)
            
        # Save the full conversation history if available
        if hasattr(self.orchestrator, "conversation_history") and self.orchestrator.conversation_history:
            history_file = os.path.join(traces_dir, f"conversation_{timestamp}.json")
            with open(history_file, "w") as f:
                json.dump(self.orchestrator.conversation_history, f, indent=2)
                
        print(f"Saved interaction traces to {traces_file}")

    async def run_cli(self):
        """Run the interactive command-line interface."""
        print("Jiki orchestrator CLI. Type your question or 'exit' to quit.")
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input or user_input.lower() == "exit":
                    # Save interaction traces before exiting
                    if hasattr(self.mcp_client, "get_interaction_traces"):
                        self.save_interaction_traces(
                            self.mcp_client.get_interaction_traces(), 
                            getattr(self.orchestrator, "conversation_history", [])
                        )
                    # Also save any traces from the logger
                    if self.logger and hasattr(self.logger, "save_all_traces"):
                        self.logger.save_all_traces()
                    print("Exiting.")
                    break
                result = await self.orchestrator.process_user_input(user_input)
                print(f"Jiki: {result}")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                # Save interaction traces on keyboard interrupt too
                if hasattr(self.mcp_client, "get_interaction_traces"):
                    self.save_interaction_traces(
                        self.mcp_client.get_interaction_traces(), 
                        getattr(self.orchestrator, "conversation_history", [])
                    )
                # Also save any traces from the logger
                if self.logger and hasattr(self.logger, "save_all_traces"):
                    self.logger.save_all_traces()
                break
            except Exception as e:
                print(f"Error: {e}")

def run_cli():
    """Entry point for the CLI."""
    from .orchestrator import JikiOrchestrator
    from .models.litellm import LiteLLMModel
    from .mcp_client import EnhancedMCPClient
    from .tools.config import load_tools_config
    from .logging import TraceLogger
    
    # Configuration
    model_name = "anthropic/claude-3-7-sonnet-latest"  # Or any LiteLLM-supported model
    tools_config_path = "tools.json"
    transport_mode = "stdio"  # Options: "stdio" or "sse"
    
    # Initialize components
    model = LiteLLMModel(model_name)
    logger = TraceLogger()
    
    # Setup MCP client
    print(f"[INFO] Using MCP with {transport_mode} transport")
    mcp_client = EnhancedMCPClient(
        transport_type=transport_mode,
        script_path="servers/calculator_server.py"
    )
    
    # Load tools and create orchestrator
    tools_config = load_tools_config(tools_config_path)
    orchestrator = JikiOrchestrator(model, mcp_client, tools_config, logger=logger)
    
    # Run the CLI
    cli = JikiCLI(orchestrator, mcp_client, logger)
    asyncio.run(cli.run_cli()) 