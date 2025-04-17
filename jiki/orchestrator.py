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
        # Remove any tool call blocks or tool result blocks
        patterns = [
            r"<mcp_tool_call>.*?</mcp_tool_call>",
            r"<mcp_tool_result>.*?</mcp_tool_result>",
            r"<mcp_available_tools>.*?</mcp_available_tools>",
            r"<Assistant_Thought>.*?</Assistant_Thought>",
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, "", result, flags=re.DOTALL)
            
        # Trim whitespace and normalize newlines
        result = re.sub(r"\n{3,}", "\n\n", result.strip())
        
        return result

    async def _handle_tool_call(self, call_content: str, output_buffer: List[str]) -> str:
        """
        Extract call details, validate, pass to MCP client, inject the result in conversation, and continue generation.
        Attempts to robustly parse JSON even if surrounded by extraneous text within the tags.
        Returns the tool result content (string) for context continuation.
        """
        if self.logger:
            # Use repr() for raw content to show quotes/escapes clearly
            self.logger.debug(f"Received raw tool call content: {call_content!r}") 
        
        # ------------------------------------------------------------------
        # Parse the JSON payload inside <mcp_tool_call> tags.
        # Strategy:
        #   1. First try to parse the entire `call_content` as JSON.
        #   2. If that fails, look for the first '{' and last '}' and
        #      attempt to parse that substring as JSON.
        # This handles cases where the LLM wraps the JSON with explanatory
        # text while keeping the implementation relatively simple.
        # ------------------------------------------------------------------

        tool_name: Optional[str] = None
        arguments: Dict[str, Any] = {}

        try:
            tool_call = json.loads(call_content)
        except json.JSONDecodeError:
            json_start = call_content.find('{')
            json_end = call_content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                try:
                    tool_call = json.loads(call_content[json_start : json_end + 1])
                except json.JSONDecodeError:
                    tool_call = {}
            else:
                tool_call = {}

        if isinstance(tool_call, dict):
            tool_name = tool_call.get("tool_name")
            raw_args = tool_call.get("arguments", {})
            arguments = raw_args if isinstance(raw_args, dict) else {}

        # --- Validation Checks ---
        
        if not tool_name:
            if self.logger:
                self.logger.debug(f"Invalid tool call: could not determine 'tool_name' from content: {call_content!r}")
            result_content = "ERROR: Invalid tool call (missing or malformed JSON 'tool_name')."
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content

        # Validate tool_name exists in tools_config
        tool_schema = next((tool for tool in self.tools_config if tool.get("tool_name") == tool_name), None)
        if not tool_schema:
            if self.logger:
                self.logger.debug(f"Tool '{tool_name}' not found in configured tools.")
            result_content = f"ERROR: Tool '{tool_name}' not found."
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content

        # Validate arguments match expected schema (basic check: required keys)
        expected_args = tool_schema.get("arguments", {})
        missing_args = [k for k in expected_args if k not in arguments]
        if missing_args:
            if self.logger:
                self.logger.debug(f"Tool '{tool_name}' called with missing required arguments: {missing_args}")
            result_content = f"ERROR: Tool '{tool_name}' missing required arguments: {missing_args}"
            result_block = f"<mcp_tool_result>\n{result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return result_content
            
        # --- Execute Tool via MCP Client --- (Unchanged)
        try:
            if self.logger:
                # Use repr() for arguments to show structure clearly
                self.logger.debug(f"Calling MCP client: tool='{tool_name}', args={arguments!r}")
            tool_result_content = await self.mcp_client.execute_tool_call(tool_name, arguments)
            if self.logger:
                # Use repr() for result to show structure clearly
                self.logger.debug(f"MCP client result for '{tool_name}': {tool_result_content!r}")
            # Record this successful call
            self._last_tool_calls.append(ToolCall(tool_name=tool_name, arguments=arguments, result=str(tool_result_content)))
            
            # Format the result for injection
            result_block = f"<mcp_tool_result>\n{tool_result_content}\n</mcp_tool_result>"
            self._log_conversation("system", result_block)
            return str(tool_result_content) # Return the actual result content
            
        except Exception as e:
            if self.logger:
                # Log exception info for more details
                self.logger.debug(f"Error calling tool '{tool_name}' via MCP client: {e}", exc_info=True)
            result_content = f"ERROR: Failed to execute tool '{tool_name}': {e}"
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
        # Regex remains the same, captures everything between tags
        match = re.search(r"(<mcp_tool_call>)(.*?)(</mcp_tool_call>)", text, re.DOTALL)
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
        pattern = r"<Assistant_Thought>(.*?)</Assistant_Thought>"
        match = re.search(pattern, text, flags=re.DOTALL)
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