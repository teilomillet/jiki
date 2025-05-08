from typing import Dict, Any, List, Optional
import json
import os
import datetime

class TraceLogger:
    """
    Logger for recording structured conversation events and interaction traces.
    This logger is designed to be general-purpose. Downstream systems (like an RL trainer)
    can use this to log rich interaction data from Jiki.
    """
    def __init__(self, log_dir="interaction_traces"):
        self.events: List[Dict[str, Any]] = []
        self.complete_traces: List[Dict[str, Any]] = []
        self.log_dir = log_dir
        try:
            os.makedirs(log_dir, exist_ok=True)
        except TypeError:
            os.makedirs(str(log_dir), exist_ok=True)
            self.log_dir = str(log_dir)

    def log_event(self, event: Dict[str, Any]):
        """
        Append a structured event to the internal events list.
        These events are typically aggregated into a complete trace.
        """
        self.events.append(event)
        
    def debug(self, message: str, **kwargs):
        """Log a debug message (currently prints to stderr)."""
        import sys
        print(f"[DEBUG] {message}", file=sys.stderr)
        
    def log_complete_trace(self, trace_data: Dict[str, Any]):
        """
        Log a complete interaction trace.
        The trace_data dictionary is augmented with a timestamp, a default reward field (if not present),
        and any accumulated events, then stored.
        
        Args:
            trace_data: Dictionary containing the primary trace information.
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Ensure a 'reward' field exists, defaulting to None if not provided in trace_data.
        # This allows downstream systems to populate it meaningfully if applicable.
        current_reward = trace_data.get("reward") # Preserve existing reward if any

        trace_with_meta = {
            "timestamp": timestamp,
            "reward": current_reward, # Will be None if not in trace_data
            **trace_data,
        }

        # If there are any accumulated events, add them to this trace and clear the events list.
        if self.events:
            trace_with_meta["events"] = self.events.copy()
            self.events.clear()

        self.complete_traces.append(trace_with_meta)
        
    def _save_trace_to_file(self, trace: Dict[str, Any]):
        """
        Internal helper to save a single trace to a JSON file.
        Not typically called directly; save_all_traces is preferred.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/trace_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(trace, f, indent=2)
            
    def get_current_traces(self) -> List[Dict[str, Any]]:
        """
        Get a copy of all accumulated traces from the current session.
        
        Returns:
            List[Dict[str, Any]]: A list of trace dictionaries.
        """
        return self.complete_traces.copy()

    def save_all_traces(self, filepath: Optional[str] = None):
        """
        Save all accumulated traces to a file. 
        Defaults to a timestamped .jsonl file in the log_dir.
        
        Args:
            filepath: Optional path to save the traces. If None, a default is used.
        """
        if not self.complete_traces:
            print("No interaction traces to save.")
            return
            
        if filepath is None:
            os.makedirs(self.log_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Defaulting to .jsonl as it's generally better for appending logs.
            filepath = os.path.join(self.log_dir, f"traces_{timestamp}.jsonl") 
        
        abs_filepath = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(abs_filepath), exist_ok=True)
        
        is_jsonl = filepath.endswith('.jsonl')
        mode = "a" if is_jsonl else "w" # Append for .jsonl, overwrite for .json

        with open(abs_filepath, mode) as f:
            if is_jsonl:
                for trace in self.complete_traces:
                    f.write(json.dumps(trace) + "\n")
            else: # .json or other
                json.dump(self.complete_traces, f, indent=2)
                
        self.debug(f"Saved {len(self.complete_traces)} interaction traces to {abs_filepath}")
        # Consider clearing traces after saving if that's the desired behavior, e.g.:
        # self.complete_traces.clear()
        # For now, traces are kept, allowing multiple saves or continued accumulation. 