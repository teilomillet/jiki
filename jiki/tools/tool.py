class Tool:
    """
    Tool class for programmatic tool definition.
    """
    def __init__(self, name, description, arguments):
        """
        Initialize a new tool.
        
        Args:
            name (str): The name of the tool
            description (str): A description of what the tool does
            arguments (dict): A dictionary of argument specifications
        """
        self.name = name
        self.description = description
        self.arguments = arguments
    
    def to_dict(self):
        """
        Convert the tool to a configuration dictionary.
        
        Returns:
            dict: Tool configuration dictionary
        """
        return {
            "tool_name": self.name,
            "description": self.description,
            "arguments": self.arguments
        } 