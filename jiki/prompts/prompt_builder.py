from typing import Protocol, List, Dict, Any, Optional
from jiki.prompts.utils import (
    create_available_tools_block,
    create_available_resources_block,
    build_initial_prompt as utils_build_initial_prompt,
)


class IPromptBuilder(Protocol):
    """
    Interface for building MCP prompts, including available tools and resources blocks, and the initial system prompt.

    This follows the Model Context Protocol prompt guidelines:
      - Expose tools with a <mcp_available_tools> block
      - Expose resources with a <mcp_available_resources> block
      - Include user instructions and query in a single prompt

    See MCP spec on prompts: https://modelcontextprotocol.io/docs/concepts/prompts

    Usage Example:
        builder = DefaultPromptBuilder()
        tools_block = builder.create_available_tools_block(tools_config)
        resources_block = builder.create_available_resources_block(resources_config)
        prompt = builder.build_initial_prompt(
            user_input="List all files.",
            tools_config=tools_config,
            resources_config=resources_config
        )
    """
    def create_available_tools_block(self, tools_config: List[Dict[str, Any]]) -> str:
        """
        Generate the <mcp_available_tools> section for the prompt.

        Parameters:
            tools_config: List of dicts, each with keys:
                - tool_name (str)
                - description (str)
                - arguments (dict of {param: schema})
                - optional 'required' list
        Returns:
            A formatted string block with indenting and JSON payload.
        """
        ...

    def create_available_resources_block(self, resources_config: List[Dict[str, Any]]) -> str:
        """
        Generate the <mcp_available_resources> section for the prompt.

        Parameters:
            resources_config: List of dicts, each with keys:
                - uri (str)
                - name (str)
                - description (str)
                - mimeType (str)
        Returns:
            A formatted string block with resources represented in JSON.
        """
        ...

    def build_initial_prompt(
        self,
        user_input: str,
        tools_config: List[Dict[str, Any]],
        resources_config: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Construct the full system prompt for the LLM, embedding:
          1. Instructions for tool/resource usage.
          2. The user's initial question.
          3. Available tools block.
          4. Available resources block (optional).

        Parameters:
            user_input: The question or instruction from the user (str).
            tools_config: Schema list for available tools.
            resources_config: Optional schema list for resources.
        Returns:
            A multi-line string representing the complete system prompt.
        """
        ...


class DefaultPromptBuilder:
    """
    Standard PromptBuilder implementation using jiki.utils.prompt utilities.

    This default builder preserves the built-in examples, instruction text, and JSON formatting rules.

    Example:
        builder = DefaultPromptBuilder()
        prompt = builder.build_initial_prompt(
            user_input="What is the current time?",
            tools_config=tools_config,
            resources_config=resources_config
        )
    """
    def create_available_tools_block(self, tools_config: List[Dict[str, Any]]) -> str:
        return create_available_tools_block(tools_config)

    def create_available_resources_block(self, resources_config: List[Dict[str, Any]]) -> str:
        return create_available_resources_block(resources_config)

    def build_initial_prompt(
        self,
        user_input: str,
        tools_config: List[Dict[str, Any]],
        resources_config: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        return utils_build_initial_prompt(user_input, tools_config, resources_config) 