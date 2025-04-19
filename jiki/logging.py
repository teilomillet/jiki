from typing import Dict, Any, List
import json
import os
import datetime

class TraceLogger:
    """
    Logger for recording structured conversation events and interaction traces.
    This logger supports the MCP interaction trace format needed for training data generation.
    """
    def __init__(self, log_dir="interaction_traces"):
        self.events: List[Dict[str, Any]] = []
        self.complete_traces: List[Dict[str, Any]] = []
        self.log_dir = log_dir
        # Ensure log_dir exists, possibly handle path object
        try:
            os.makedirs(log_dir, exist_ok=True)
        except TypeError:
            # Handle if log_dir is a Path object
            os.makedirs(str(log_dir), exist_ok=True)
            self.log_dir = str(log_dir)

    def log_event(self, event: Dict[str, Any]):
        """
        Append a structured event to the log.
        """
        self.events.append(event)
        
    def debug(self, message: str, **kwargs):
        """Log a debug message (currently prints to stderr)."""
        # Simple implementation: print to stderr
        # Could be expanded to use Python's logging module later
        import sys
        print(f"[DEBUG] {message}", file=sys.stderr)
        
    def log_complete_trace(self, trace_data: Dict[str, Any]):
        """
        Log a complete interaction trace suitable for training data generation.
        The trace should include the full conversation with all MCP-related tags.
        
        :param trace_data: Dictionary containing the complete trace information
        """
        # Add timestamp to the trace
        timestamp = datetime.datetime.now().isoformat()
        # Always include an explicit reward field so downstream RL code can
        # easily fill it in.  If the caller already supplied one, keep it.
        trace_with_meta = {
            "timestamp": timestamp,
            "reward": trace_data.get("reward"),  # None if missing
            **trace_data,
        }
        # Include any recorded events (e.g., system messages, tool results, thoughts)
        if self.events:
            trace_with_meta["events"] = self.events.copy()
            # Clear events after snapshotting to avoid duplication
            self.events.clear()
        
        self.complete_traces.append(trace_with_meta)
        
        # Remove automatic saving per trace
        # self._save_trace_to_file(trace_with_meta)
        
    def _save_trace_to_file(self, trace: Dict[str, Any]):
        """
        Save a single trace to a JSON file in the log directory.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/trace_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(trace, f, indent=2)
            
    def get_current_traces(self):
        """
        Get all traces from the current session.
        
        Returns:
            list: List of trace dictionaries
        """
        return self.complete_traces.copy()

    def save_all_traces(self, filepath=None):
        """
        Save all accumulated traces to a file.
        If filepath is not provided, use the default log directory with timestamp.
        
        Args:
            filepath (str, optional): Path to save the traces
        """
        if not self.complete_traces:
            print("No interaction traces to save.")
            return
            
        if filepath is None:
            # Create a directory for traces if it doesn't exist
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Generate a timestamp for unique filenames
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Default filepath with timestamp
            filepath = os.path.join(self.log_dir, f"traces_{timestamp}.json")
        
        # Ensure directory exists before writing
        abs_filepath = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(abs_filepath), exist_ok=True)
        
        # Save as JSON or JSONL based on extension
        if filepath.endswith('.jsonl'):
            # append so multiple calls accumulate in one file
            with open(abs_filepath, "a") as f:
                for trace in self.complete_traces:
                    f.write(json.dumps(trace) + "\n")
        else:
            # Default to JSON if not .jsonl
            with open(abs_filepath, "w") as f:
                json.dump(self.complete_traces, f, indent=2)
                
        print(f"Saved {len(self.complete_traces)} interaction traces to {abs_filepath}")
        
        # Removed saving of self.events as per plan focus on complete_traces 