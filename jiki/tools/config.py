from typing import List, Dict, Any
import json
import os

def load_tools_config(config_path: str) -> List[Dict[str, Any]]:
    """
    Load tool configuration from a JSON file and return as a list of tool schemas.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Tool config file not found: {config_path}")
    with open(config_path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Tool config JSON must be a list of tool schemas.")
    return data 