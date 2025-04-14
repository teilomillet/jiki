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
        os.makedirs(log_dir, exist_ok=True)

    def log_event(self, event: Dict[str, Any]):
        """
        Append a structured event to the log.
        """
        self.events.append(event)
        
    def log_complete_trace(self, trace_data: Dict[str, Any]):
        """
        Log a complete interaction trace suitable for training data generation.
        The trace should include the full conversation with all MCP-related tags.
        
        :param trace_data: Dictionary containing the complete trace information
        """
        # Add timestamp to the trace
        timestamp = datetime.datetime.now().isoformat()
        trace_with_meta = {
            "timestamp": timestamp,
            **trace_data
        }
        
        self.complete_traces.append(trace_with_meta)
        
        # Save the trace to a file
        self._save_trace_to_file(trace_with_meta)
        
    def _save_trace_to_file(self, trace: Dict[str, Any]):
        """
        Save a single trace to a JSON file in the log directory.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/trace_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(trace, f, indent=2)
            
    def save_all_traces(self):
        """
        Save all accumulated traces and events to files.
        Useful for saving everything at the end of a session.
        """
        # Save the regular events
        if self.events:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            events_file = f"{self.log_dir}/events_{timestamp}.json"
            with open(events_file, "w") as f:
                json.dump(self.events, f, indent=2)
        
        # Save each complete trace that hasn't been saved yet
        for trace in self.complete_traces:
            if not trace.get("_saved", False):
                self._save_trace_to_file(trace)
                trace["_saved"] = True 