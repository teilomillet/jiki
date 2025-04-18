"""
Jiki Orchestrator
=================

This module contains the :class:`JikiOrchestrator` – the central coordination
engine that powers Jiki's tool‑augmented conversations.

High‑level responsibilities
--------------------------
1. Build an initial system prompt exposing the available tool schemas to the
   underlying Large Language Model (LLM).
2. Stream tokens from the LLM, intercepting ``<mcp_tool_call>`` blocks emitted
   by the model in‑flight.
3. Validate tool calls against the configured schemas and dispatch them via an
   :class:`~jiki.mcp_client.EnhancedMCPClient` implementation.
4. Inject tool results back into the conversational context so the model can
   continue reasoning.
5. Maintain a rolling message buffer that is trimmed to stay within the model's
   context window.
6. Emit richly‑structured interaction traces through :class:`~jiki.logging.TraceLogger`
   for offline reinforcement learning (RL) or analysis.

Typical Usage
-------------
>>> from jiki import create_jiki
>>> orchestrator = create_jiki()
>>> response = orchestrator.process("What is 2 + 2?")
>>> print(response)

"""
from typing import List, Dict, Any, Optional
from jiki.utils.cleaning import clean_output
from jiki.models.response import ToolCall
from jiki.prompt_builder import IPromptBuilder, DefaultPromptBuilder
from jiki.tool_client import IToolClient
from jiki.utils.context import trim_context
from jiki.utils.parsing import extract_tool_call, extract_thought
from jiki.utils.tool import parse_tool_call_content, validate_tool_call
from jiki.utils.streaming import generate_and_intercept
from jiki.utils.token import count_tokens
from jiki.utils.logging import record_conversation_event

class JikiOrchestrator:
    """
    Central orchestration engine for Jiki, managing LLM messages, tool/resource calls, and conversation context.

    Example:
        >>> from jiki import create_jiki
        >>> orchestrator = create_jiki(
        ...     model="anthropic/claude-3-7-sonnet", 
        ...     tools=None, 
        ...     mcp_mode="stdio"
        ... )
        >>> result = orchestrator.process("What is 2 + 3?")
        >>> print(result)
    """
    def __init__(
        self,
        model: Any,
        mcp_client: IToolClient,
        tools_config: List[Dict[str, Any]],
        logger=None,
        prompt_builder: IPromptBuilder = None
    ):
        """
        :param model: LLM model wrapper (e.g., LiteLLMModel)
        :param mcp_client: Tool client implementing IToolClient interface
        :param tools_config: List of available tool schemas
        :param logger: Optional logger for trace events
        :param prompt_builder: Prompt builder abstraction (delegates prompt template generation)
        """
        self.model = model
        self.mcp_client = mcp_client
        self.tools_config = tools_config
        # Build a dict mapping tool_name to its schema for fast validation lookups
        self._tools_map = {tool.get("tool_name"): tool for tool in tools_config}
        # Prompt builder abstraction (delegates prompt template generation)
        self.prompt_builder: IPromptBuilder = prompt_builder or DefaultPromptBuilder()
        self.conversation_history: List[Dict[str, str]] = []
        self.logger = logger
        self._last_tool_calls = []
        # In‑memory chat log in LiteLLM / OpenAI format
        self._messages: List[Dict[str, str]] = []

    def create_available_tools_block(self) -> str:
        """
        Format a block describing the available tools (e.g., <mcp_available_tools> ... </mcp_available_tools>).
        """
        return self.prompt_builder.create_available_tools_block(self.tools_config)

    def build_initial_prompt(
        self,
        user_input: str,
        resources_config: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build the initial prompt for the LLM, including user input and available tools.
        """
        return self.prompt_builder.build_initial_prompt(
            user_input,
            self.tools_config,
            resources_config
        )

    async def process_user_input(self, user_input: str, max_tokens_ctx: int = 6000) -> str:
        """
        Orchestrate a single user query, returning the final answer.
        """
        self._last_tool_calls = []

        if not self._messages:
            # FIRST TURN — fetch resources, then combine instructions, tool list, resources, and user question
            resources_config = []
            try:
                resources_config = await self.mcp_client.list_resources()
            except Exception:
                pass  # proceed even if resources fetch fails
            initial_content = self.build_initial_prompt(user_input, self.tools_config, resources_config)
            self._messages.append({
                "role": "system",
                "content": initial_content
            })
        else:
            # SUBSEQUENT TURNS — add the user message as a separate turn
            self._messages.append({"role": "user", "content": user_input})

        # Trim context if oversized based on token count using token_utils
        trim_context(self._messages, lambda msgs: count_tokens(msgs, self.model.model_name), max_tokens_ctx)

        record_conversation_event(self.conversation_history, "system", str(self._messages), self.logger)
        final_answer = await self._generate_and_intercept(self._messages)

        self._messages.append({"role": "assistant", "content": final_answer})
        return final_answer

    async def _generate_and_intercept(self, messages: List[Dict[str, str]]) -> str:
        """
        Delegate token streaming and tool-call interception to the shared utility.
        """
        log_complete = self.logger.log_complete_trace if self.logger else None
        return await generate_and_intercept(
            generate_tokens_fn=self.model.generate_tokens,
            handle_tool_call_fn=self._handle_tool_call,
            extract_tool_call_fn=extract_tool_call,
            extract_thought_fn=extract_thought,
            clean_fn=clean_output,
            log_complete_trace_fn=log_complete,
            log_conversation_fn=lambda role, content: record_conversation_event(self.conversation_history, role, content, self.logger),
            context=messages,
        )

    async def _handle_tool_call(self, call_content: str, output_buffer: List[str]) -> str:
        """
        Extract call details, validate, pass to MCP client, inject the result in conversation, and continue generation.
        Attempts to robustly parse JSON even if surrounded by extraneous text within the tags.
        Returns the tool result content (string) for context continuation.
        """
        if self.logger:
            # Use repr() for raw content to show quotes/escapes clearly
            self.logger.debug(f"Received raw tool call content: {call_content!r}") 
        
        # Parse and validate the tool call
        tool_name, arguments, parse_error = parse_tool_call_content(call_content)
        if parse_error:
            if self.logger:
                self.logger.debug(f"Tool call parse error: {parse_error}")
            record_conversation_event(self.conversation_history, "system", f"<mcp_tool_result>\n{parse_error}\n</mcp_tool_result>", self.logger)
            return parse_error

        # Validate using O(1) schema lookup via tools_map
        tool_schema, validation_error = validate_tool_call(tool_name, arguments, self._tools_map)
        if validation_error:
            if self.logger:
                self.logger.debug(f"Tool call validation error: {validation_error}")
            record_conversation_event(self.conversation_history, "system", f"<mcp_tool_result>\n{validation_error}\n</mcp_tool_result>", self.logger)
            return validation_error

        # --- Execute Tool via MCP Client ---
        try:
            if self.logger:
                self.logger.debug(f"Calling MCP client: tool='{tool_name}', args={arguments!r}")
            tool_result_content = await self.mcp_client.execute_tool_call(tool_name, arguments)
            if self.logger:
                # Use repr() for result to show structure clearly
                self.logger.debug(f"MCP client result for '{tool_name}': {tool_result_content!r}")
            # Record this successful call
            self._last_tool_calls.append(ToolCall(tool_name=tool_name, arguments=arguments, result=str(tool_result_content)))
            
            # Format the result for injection
            result_block = f"<mcp_tool_result>\n{tool_result_content}\n</mcp_tool_result>"
            record_conversation_event(self.conversation_history, "system", result_block, self.logger)
            return str(tool_result_content) # Return the actual result content
            
        except Exception as e:
            if self.logger:
                # Log exception info for more details
                self.logger.debug(f"Error calling tool '{tool_name}' via MCP client: {e}", exc_info=True)
            result_content = f"ERROR: Failed to execute tool '{tool_name}': {e}"
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            record_conversation_event(self.conversation_history, "system", result_block, self.logger)
            return result_content 

    def snapshot(self) -> Dict[str, Any]:
        """
        Capture the current conversation state as a snapshot dict.
        """
        # Make shallow copies to avoid external mutation
        return {
            "messages": list(self._messages),
            "conversation_history": list(self.conversation_history),
            "last_tool_calls": [
                {"tool": tc.tool, "arguments": tc.arguments, "result": tc.result}
                for tc in getattr(self, '_last_tool_calls', [])
            ]
        }

    def resume(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore conversation state from a snapshot dict.
        """
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dict containing messages, conversation_history, and last_tool_calls")
        # Restore messages
        msgs = snapshot.get('messages')
        if not isinstance(msgs, list):
            raise TypeError("snapshot['messages'] must be a list")
        self._messages = list(msgs)
        # Restore conversation history
        history = snapshot.get('conversation_history')
        if not isinstance(history, list):
            raise TypeError("snapshot['conversation_history'] must be a list")
        self.conversation_history = list(history)
        # Restore last tool calls
        calls = snapshot.get('last_tool_calls', [])
        if not isinstance(calls, list):
            raise TypeError("snapshot['last_tool_calls'] must be a list")
        # Reconstruct ToolCall objects
        from jiki.models.response import ToolCall
        restored = []
        for item in calls:
            if isinstance(item, dict):
                restored.append(ToolCall(
                    item.get('tool'),
                    item.get('arguments'),
                    item.get('result')
                ))
        self._last_tool_calls = restored 