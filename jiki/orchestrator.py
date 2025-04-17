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
            # First turn: push system instructions and tool list
            self._messages.append({"role": "system", "content": self.build_initial_prompt("")})

        # Append the new user message
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
                call_content, tag = self._extract_tool_call_if_present(combined_output)
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
            
        # The helper string is no longer inserted; keep regex for backward compatibility but it's optional
        result = re.sub(r"Continue your response based on this result:", "", result)
            
        # Trim whitespace and normalize newlines
        result = re.sub(r"\n{3,}", "\n\n", result.strip())
        
        return result

    async def _handle_tool_call(self, call_content: str, output_buffer: List[str]):
        """
        Extract call details, validate, pass to MCP client, inject the result in conversation, and continue generation.
        Returns the tool result for context continuation.
        """
        print("[DEBUG] Raw tool call content:", call_content)
        # Attempt to parse tool name and arguments from call_content (assume JSON inside tag)
        try:
            tool_call = json.loads(call_content)
            tool_name = tool_call.get("tool_name")
            arguments = tool_call.get("arguments", {})
            print(f"[DEBUG] Parsed tool_name: {tool_name}, arguments: {arguments}")
        except Exception as e:
            print(f"[DEBUG] Failed to parse tool call JSON: {e}")
            tool_name = None
            arguments = {}
        
        if not tool_name:
            print("[DEBUG] Invalid tool call: missing tool_name")
            result_block = "<mcp_tool_result>\nERROR: Invalid tool call (missing tool_name)\n</mcp_tool_result>"
            output_buffer.append(result_block)
            self._log_conversation("system", result_block)
            return "ERROR: Invalid tool call (missing tool_name)"
        
        # Validate tool_name exists in tools_config
        tool_schema = next((tool for tool in self.tools_config if tool.get("tool_name") == tool_name), None)
        if not tool_schema:
            print(f"[DEBUG] Tool '{tool_name}' not found in tools_config")
            result_block = f"<mcp_tool_result>\nERROR: Tool '{tool_name}' not found.\n</mcp_tool_result>"
            output_buffer.append(result_block)
            self._log_conversation("system", result_block)
            return f"ERROR: Tool '{tool_name}' not found."
        
        # Validate arguments match expected schema (basic check: required keys)
        expected_args = tool_schema.get("arguments", {})
        missing_args = [k for k in expected_args if k not in arguments]
        if missing_args:
            print(f"[DEBUG] Missing required arguments: {missing_args}")
            result_block = f"<mcp_tool_result>\nERROR: Missing required arguments: {', '.join(missing_args)}\n</mcp_tool_result>"
            output_buffer.append(result_block)
            self._log_conversation("system", result_block)
            return f"ERROR: Missing required arguments: {', '.join(missing_args)}"
        
        # Call the tool via MCP client
        try:
            tool_result = await self.mcp_client.execute_tool_call(tool_name, arguments)
            
            # Record tool call for detailed response
            self._last_tool_calls.append(ToolCall(
                tool=tool_name,
                arguments=arguments,
                result=tool_result
            ))
            
        except Exception as e:
            print(f"[DEBUG] Exception during tool call: {e}")
            tool_result = f"ERROR: Exception during tool call: {e}"
            # Also record failed tool calls
            self._last_tool_calls.append(ToolCall(
                tool=tool_name,
                arguments=arguments,
                result=f"ERROR: {e}"
            ))
        
        result_block = f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"
        output_buffer.append(result_block)
        self._log_conversation("system", result_block)
        return tool_result

    def _log_conversation(self, role: str, content: str):
        """
        Record conversation events for debugging or training logs.
        """
        event = {"role": role, "content": content}
        self.conversation_history.append(event)
        if self.logger:
            self.logger.log_event(event)

    def _extract_tool_call_if_present(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect a <mcp_tool_call> or <mcp_tool_request> block in text and return its content and tag.
        """
        patterns = [
            (r"<mcp_tool_call>(.*?)</mcp_tool_call>", "mcp_tool_call"),
            (r"<mcp_tool_request>(.*?)</mcp_tool_request>", "mcp_tool_request"),
        ]
        for pattern, tag in patterns:
            match = re.search(pattern, text, flags=re.DOTALL)
            if match:
                return match.group(1).strip(), tag
        return None, None

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