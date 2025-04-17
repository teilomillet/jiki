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
from typing import List, Dict, Any, Optional, Tuple
import re
import json
from jiki.models.response import ToolCall
from jiki.utils import (
    repair_json, 
    validate_tool_arguments, 
    categorize_error, 
    format_argument_descriptions,
    clean_output
)

try:
    # Optional dependency – provides exact token counts for OpenAI models
    import tiktoken  # type: ignore
except ImportError:
    tiktoken = None

class JikiOrchestrator:
    def __init__(self, model, mcp_client, tools_config: List[Dict[str, Any]], logger=None):
        """
        :param model: LLM model wrapper (e.g., LiteLLMModel)
        :param mcp_client: MCPClient instance
        :param tools_config: List of available tool schemas
        :param logger: Optional logger for trace events
        """
        self.model = model
        self.mcp_client = mcp_client
        self.tools_config = tools_config
        self.conversation_history: List[Dict[str, str]] = []
        self.logger = logger
        self._last_tool_calls = []
        # In‑memory chat log in LiteLLM / OpenAI format
        self._messages: List[Dict[str, str]] = []
        
        # Pre-compile regex patterns for better performance
        self._tool_call_pattern = re.compile(r"(<mcp_tool_call>)(.*?)(</mcp_tool_call>)", re.DOTALL)
        self._thought_pattern = re.compile(r"<Assistant_Thought>(.*?)</Assistant_Thought>", re.DOTALL)
        # Patterns used in _clean_output
        self._clean_patterns = [
            re.compile(r"<mcp_tool_call>.*?</mcp_tool_call>", re.DOTALL),
            re.compile(r"<mcp_tool_result>.*?</mcp_tool_result>", re.DOTALL),
            re.compile(r"<mcp_available_tools>.*?</mcp_available_tools>", re.DOTALL),
            re.compile(r"<Assistant_Thought>.*?</Assistant_Thought>", re.DOTALL),
        ]
        self._whitespace_pattern = re.compile(r"\n{3,}")

    def create_available_tools_block(self) -> str:
        """
        Format a block describing the available tools (e.g., <mcp_available_tools> ... </mcp_available_tools>).
        """
        return f"<mcp_available_tools>\n{json.dumps(self.tools_config, indent=2)}\n</mcp_available_tools>"

    def build_initial_prompt(self, user_input: str) -> str:
        """
        Build the initial prompt for the LLM, including user input and available tools.
        """
        block = self.create_available_tools_block()
        instruction = (
            "INSTRUCTIONS: You are an AI assistant that can use tools to help solve problems. "
            "After using tools to gather information, you should provide a complete, natural language response to the user's question. "
            "If you want to use a tool, you MUST use ONLY the tool names listed in the <mcp_available_tools> block below. "
            "Always emit a <mcp_tool_call>...</mcp_tool_call> block with valid, complete JSON inside. "
            "Before calling a tool, explain your thinking in an <Assistant_Thought>...</Assistant_Thought> block. "
            "Do NOT invent tool names. Do NOT use any tool not listed. "
            "Do NOT emit malformed or incomplete JSON. "
            "After using a tool and receiving its result, continue your reasoning to provide a complete answer to the user's question. "
            "Remember to answer all parts of the user's question completely.\n"
            "\nCORRECT EXAMPLE:\n"
            "<Assistant_Thought>I need to add two numbers. I'll use the add tool.</Assistant_Thought>\n"
            "<mcp_tool_call>\n{\n  \"tool_name\": \"add\", \"arguments\": {\"a\": 3, \"b\": 3}\n}\n</mcp_tool_call>\n"
            "\nINCORRECT EXAMPLES (do NOT do this):\n"
            "<mcp_tool_call>\n{\n  \"tool_name\": \"calculator\", \"arguments\": {\"operation\": \"add\", \"numbers\": [3, 4]}\n}\n</mcp_tool_call>\n"
            "<mcp_tool_call>\n{\n  \"tool_name\": \"add\", \"arguments\": {\"a\": 3, \"b\": 4}\n  // missing closing brace\n</mcp_tool_call>\n"
            "\nAfter using a tool and getting its result, continue to answer the user's original question completely."
        )
        prompt = (
            f"{instruction}\n\n"
            f"User: {user_input}\n\n"
            f"{block}\n\n"
        )
        return prompt

    async def process_user_input(self, user_input: str, max_tokens_ctx: int = 6000) -> str:
        """
        Orchestrate a single user query, returning the final answer.
        """
        self._last_tool_calls = []

        if not self._messages:
            # FIRST TURN — combine instructions, tool list, *and* initial user question
            # This avoids injecting a blank "User:" line in the system prompt and eliminates
            # the need for a second user‑role message.
            self._messages.append({
                "role": "system",
                "content": self.build_initial_prompt(user_input)
            })
        else:
            # SUBSEQUENT TURNS — add the user message as a separate turn
            self._messages.append({"role": "user", "content": user_input})

        # Trim context if oversized based on token count
        while self._num_tokens(self._messages) > max_tokens_ctx and len(self._messages) > 2:
            # Pop the second message (index 1) – keep system message
            self._messages.pop(1)


        self._log_conversation("system", str(self._messages))
        final_answer = await self._generate_and_intercept(self._messages)

        self._messages.append({"role": "assistant", "content": final_answer})
        return final_answer

    async def _generate_and_intercept(self, messages: List[Dict[str, str]]) -> str:
        """
        Streams tokens from the model and intercepts <mcp_tool_call> or <mcp_tool_request> if encountered.
        Also captures <Assistant_Thought> blocks for training data.
        """
        output_buffer = []
        # Copy the reference of the running context list so we can mutate it in‑place
        context = messages

        raw_conversation: List[Dict[str, Any]] = []  # Store complete convo (using strings for content)
        raw_conversation.append({"role": "system", "content": str(context[0]["content"]) if context else ""})
        
        while True:
            tool_call_found = False
            thought_found = False
            async for token in self.model.generate_tokens(context):
                output_buffer.append(token)
                combined_output = "".join(output_buffer)
                
                # Check for Assistant_Thought blocks
                thought_content = self._extract_thought_if_present(combined_output)
                if thought_content and not thought_found:
                    thought_found = True
                    # Log the thought but continue streaming tokens
                    
                # Check for tool calls
                call_content = self._extract_tool_call_if_present(combined_output)
                if call_content:
                    tool_call_found = True
                    
                    # Record the assistant's output up to this point in raw conversation
                    raw_conversation.append({"role": "assistant", "content": combined_output})
                    
                    # Handle the tool call
                    tool_result = await self._handle_tool_call(call_content, output_buffer)
                    
                    # Record the tool result in raw conversation
                    raw_conversation.append({
                        "role": "system",
                        "content": f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"
                    })
                    
                    # Append to the running message context: assistant output so far, then tool result, then an instruction to continue
                    context.append({"role": "assistant", "content": combined_output})
                    context.append({"role": "system", "content": f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"})
                    # No need for a textual nudge; the chat schema will prompt the model to continue

                    output_buffer = []  # reset buffer
                    break  # restart generation with updated context list
            
            if not tool_call_found:
                # If no tool call was found, add final assistant response to raw conversation
                raw_conversation.append({"role": "assistant", "content": "".join(output_buffer)})
                break
        
        # Clean the final output to remove MCP-related tags
        final_output = "".join(output_buffer)
        clean_output = self._clean_output(final_output)
        
        # Log the complete conversation history including all tags for training
        if self.logger:
            self.logger.log_complete_trace({
                "conversation": raw_conversation,
                "final_clean_output": clean_output,
                "reward": None
            })
        
        self._log_conversation("assistant", clean_output)
        return clean_output
        
    def _clean_output(self, text: str) -> str:
        """
        Clean the output by removing MCP-related tags and formatting for final user display.
        For training data generation, the original output with tags is preserved in the logs.
        """
        return clean_output(text, self._clean_patterns)

    async def _handle_tool_call(self, call_content: str, output_buffer: List[str]) -> str:
        """
        Extract call details, validate, pass to MCP client, inject the result in conversation, and continue generation.
        Enhanced with better JSON parsing and error recovery for malformed tool calls.
        Returns the tool result content (string) for context continuation.
        """
        if self.logger:
            # Use repr() for raw content to show quotes/escapes clearly
            self.logger.debug(f"Received raw tool call content: {call_content!r}") 
        
        # ------------------------------------------------------------------
        # ENHANCED JSON PARSING WITH BETTER ERROR RECOVERY
        # Strategy:
        #   1. First try to parse the entire `call_content` as JSON.
        #   2. If that fails, look for the first '{' and last '}' and
        #      attempt to parse that substring as JSON.
        #   3. If that fails, try to fix common JSON errors (single quotes, trailing commas)
        #   4. Track the parsing method used for better error reporting
        # ------------------------------------------------------------------

        tool_name: Optional[str] = None
        arguments: Dict[str, Any] = {}
        
        # Use the repair_json utility function
        tool_call, parsing_method, parsing_error = repair_json(call_content)

        # Log the parsing method used (helpful for debugging)
        if self.logger and parsing_method != "direct":
            self.logger.debug(f"JSON parsing method: {parsing_method}, error: {parsing_error}")

        # Extract tool name and arguments with better validation
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("tool_name")
            raw_args = tool_call.get("arguments", {})
            arguments = raw_args if isinstance(raw_args, dict) else {}

        # --- Enhanced Validation and Error Reporting ---
        
        if not tool_name:
            detailed_error = "Missing or invalid 'tool_name' field in the JSON object."
            if parsing_method != "direct":
                detailed_error += f" JSON parsing method: {parsing_method}."
                if parsing_error:
                    detailed_error += f" Error: {parsing_error}"
            
            result_content = f"ERROR: Invalid tool call. {detailed_error} Please provide a valid JSON object with 'tool_name' and 'arguments' fields."
            if self.logger:
                self.logger.debug(f"Tool call validation failed: {detailed_error}")
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content

        # Validate tool_name exists in tools_config
        tool_schema = next((tool for tool in self.tools_config if tool.get("tool_name") == tool_name), None)
        if not tool_schema:
            if self.logger:
                self.logger.debug(f"Tool '{tool_name}' not found in configured tools.")
            
            # Enhanced error message with available tools
            available_tools = [t.get("tool_name") for t in self.tools_config if t.get("tool_name")]
            result_content = f"ERROR: Tool '{tool_name}' not found. Available tools are: {', '.join(available_tools)}"
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content

        # Enhanced argument validation with more detailed feedback
        expected_args = tool_schema.get("arguments", {})
        required_args = tool_schema.get("required", [])
        
        # Use the validate_tool_arguments utility function
        missing_args, type_mismatches = validate_tool_arguments(
            arguments, expected_args, required_args
        )
        
        if missing_args or type_mismatches:
            error_details = []
            if missing_args:
                error_details.append(f"Missing required arguments: {', '.join(missing_args)}")
            if type_mismatches:
                error_details.append(f"Type mismatches: {', '.join(type_mismatches)}")
            
            # Include argument schema in error message for clarity
            arg_descriptions = format_argument_descriptions(expected_args, required_args)
            
            result_content = (
                f"ERROR: Invalid arguments for tool '{tool_name}'.\n"
                f"{'; '.join(error_details)}\n\n"
                f"Expected arguments:\n"
                f"{chr(10).join(arg_descriptions)}"
            )
            
            if self.logger:
                self.logger.debug(f"Tool '{tool_name}' called with invalid arguments: {error_details}")
            
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content
            
        # --- Execute Tool via MCP Client with Enhanced Error Handling ---
        try:
            if self.logger:
                # Use repr() for arguments to show structure clearly
                self.logger.debug(f"Calling MCP client: tool='{tool_name}', args={arguments!r}")
            
            # Execute the tool call
            tool_result_content = await self.mcp_client.execute_tool_call(tool_name, arguments)
            
            if self.logger:
                # Use repr() for result to show structure clearly
                self.logger.debug(f"MCP client result for '{tool_name}': {tool_result_content!r}")
            
            # Record this successful call
            self._last_tool_calls.append(ToolCall(tool=tool_name, arguments=arguments, result=str(tool_result_content)))
            
            # Format the result for injection
            result_block = f"<mcp_tool_result>\n{tool_result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return str(tool_result_content) # Return the actual result content
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            
            if self.logger:
                # Log detailed exception info
                self.logger.debug(f"Error calling tool '{tool_name}' via MCP client: {e}", exc_info=True)
            
            # Use the categorize_error utility function
            error_category, friendly_message = categorize_error(e)
            
            # Create a detailed error message
            result_content = (
                f"ERROR ({error_category}): Failed to execute tool '{tool_name}'.\n"
                f"{friendly_message}\n"
                f"Please check your inputs and try again."
            )
            
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content

    def _log_conversation(self, role: str, content: str):
        """
        Record conversation events for debugging or training logs.
        """
        event = {"role": role, "content": content}
        self.conversation_history.append(event)
        if self.logger:
            self.logger.log_event(event)

    def _extract_tool_call_if_present(self, text: str) -> Optional[str]:
        """
        Check if a complete <mcp_tool_call>...</mcp_tool_call> block is present.
        Returns the raw content inside the block if found, otherwise None.
        The content might contain more than just JSON.
        """
        # Use pre-compiled pattern for better performance
        match = self._tool_call_pattern.search(text)
        if match:
            content = match.group(2)
            closing_tag = match.group(3)
            # Basic check: ensure closing tag matches opening tag name conceptually
            if closing_tag == f"</{match.group(1)[1:-1]}>":
                # Return raw content; parsing responsibility is in _handle_tool_call
                return content
        return None

    def _extract_thought_if_present(self, text: str) -> Optional[str]:
        """
        Detect an <Assistant_Thought> block in text and return its content.
        """
        match = self._thought_pattern.search(text)
        if match:
            return match.group(1).strip()
        return None 

    # ------------------------------------------------------------------
    # Helper – estimate prompt length in model tokens so we can trim
    # context safely.  Uses tiktoken if available; otherwise falls back
    # to rough character‑based heuristic (≈4 chars per token).
    # ------------------------------------------------------------------
    def _num_tokens(self, messages: List[Dict[str, str]]) -> int:
        if tiktoken is not None:
            try:
                enc = tiktoken.encoding_for_model(self.model.model_name)
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")

            tokens = 0
            for m in messages:
                # Per OpenAI guide: every message gets <|start|>role\ncontent<|end|>
                tokens += 4  # rough per‑message overhead
                tokens += len(enc.encode(m.get("content", "")))
            return tokens
        # Fallback – 1 token ≈ 4 chars (very rough)
        return len(str(messages)) // 4 