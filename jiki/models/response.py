class ToolCall:
    """
    Represents a single tool call.
    """
    def __init__(self, tool, arguments, result):
        self.tool = tool
        self.arguments = arguments
        self.result = result
    
    def __repr__(self):
        return f"ToolCall(tool={self.tool}, arguments={self.arguments})"

class DetailedResponse:
    """
    Enhanced response object with additional information about tool calls and traces.
    """
    def __init__(self, result, tool_calls=None, traces=None):
        self.result = result
        self.tool_calls = tool_calls or []
        self.traces = traces
    
    def __repr__(self):
        return f"DetailedResponse(result={self.result[:50]}{'...' if len(self.result) > 50 else ''}, tool_calls={len(self.tool_calls)})" 