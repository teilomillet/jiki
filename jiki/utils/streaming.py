from typing import Any, Callable, Awaitable, AsyncIterator, Dict, List, Optional
from .logging import record_conversation_event
import json

# Helper function to encapsulate common logging logic for conversation events.
# This reduces repetition and improves readability in the main streaming function.
def _log_event(
    logger: Optional[Any],
    history: List[Dict[str, Any]],
    role: str,
    content: str,
    event_type: Optional[str] = None
):
    """Logs a conversation event with structured metadata."""
    metadata = {"event_type": event_type} if event_type else None
    record_conversation_event(
        history=history,
        role=role,
        content=content,
        logger=logger,
        metadata=metadata
    )

async def generate_and_intercept(
    generate_tokens_fn: Callable[[List[Dict[str, str]]], AsyncIterator[str]],
    handle_tool_call_fn: Callable[[str, List[str]], Awaitable[str]],
    extract_tool_call_fn: Callable[[str], Optional[str]],
    extract_thought_fn: Callable[[str], Optional[str]],
    clean_fn: Callable[[str], str],
    log_complete_trace_fn: Optional[Callable[[Dict[str, Any]], None]],
    log_conversation_fn: Callable[[str, str, Optional[Any], Optional[Dict[str,Any]]], None],
    logger_instance: Optional[Any],
    context: List[Dict[str, str]]
) -> str:
    """
    Stream tokens from the LLM, intercepting tool-call and thought blocks.
    Logs intermediate steps for potential RL training.
    Returns the final cleaned assistant response.
    """
    output_buffer: List[str] = []
    raw_conversation_for_trace: List[Dict[str, Any]] = list(context)

    while True:
        tool_call_found = False
        thought_found = False
        prompt_for_this_step = context.copy()
        
        # Log the prompt for the current LLM call cycle using the helper.
        _log_event(
            logger=logger_instance,
            history=raw_conversation_for_trace, # history here is the full trace up to this point
            role="llm_prompt",
            content=json.dumps(prompt_for_this_step),
            event_type="llm_prompt"
        )
        
        async for token in generate_tokens_fn(prompt_for_this_step):
            output_buffer.append(token)
            combined = "".join(output_buffer)

            if not thought_found and (thought_content := extract_thought_fn(combined)):
                thought_found = True
                # Log assistant thought using the helper.
                _log_event(
                    logger=logger_instance,
                    history=context, # history here is the context before this LLM turn's thought/call
                    role="assistant_thought", 
                    content=thought_content, 
                    event_type="assistant_thought"
                )
                raw_conversation_for_trace.append({"role": "assistant_thought", "content": thought_content})

            if (call_content := extract_tool_call_fn(combined)):
                tool_call_found = True
                raw_llm_response_with_call = combined
                
                # Log raw LLM response containing a tool call using the helper.
                _log_event(
                    logger=logger_instance,
                    history=raw_conversation_for_trace, # history is full trace
                    role="llm_raw_response",
                    content=raw_llm_response_with_call,
                    event_type="llm_raw_response_with_tool_call"
                )

                raw_conversation_for_trace.append({"role": "assistant", "content": raw_llm_response_with_call})
                
                tool_result = await handle_tool_call_fn(call_content, output_buffer)
                tool_result_block = f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"
                
                # Log tool result injection using the helper.
                _log_event(
                    logger=logger_instance,
                    history=context, # history is context before this LLM turn's thought/call
                    role="system", 
                    content=tool_result_block, 
                    event_type="tool_result_injection"
                )
                raw_conversation_for_trace.append({"role": "system", "content": tool_result_block})
                
                context.append({"role": "assistant", "content": raw_llm_response_with_call})
                context.append({"role": "system", "content": tool_result_block})
                
                output_buffer.clear()
                break

        if not tool_call_found:
            final_output_raw_no_tool = "".join(output_buffer) # This is the raw response for this turn
            # Log raw LLM response without a tool call using the helper.
            _log_event(
                 logger=logger_instance,
                 history=raw_conversation_for_trace, # history is full trace
                 role="llm_raw_response", 
                 content=final_output_raw_no_tool, 
                 event_type="llm_raw_response_no_tool_call"
            )
            raw_conversation_for_trace.append({"role": "assistant", "content": final_output_raw_no_tool})
            break

    final_output_cleaned = clean_fn(final_output_raw_no_tool)

    if log_complete_trace_fn:
        log_complete_trace_fn({
            "conversation_detail": raw_conversation_for_trace, 
            "final_clean_output": final_output_cleaned,
            "reward": None 
        })

    # Log final assistant response (this one doesn't use event_type in metadata directly in the original code)
    # Adapting to _log_event, we can omit event_type or pass None explicitly.
    # The original call was: record_conversation_event(history=context, role="assistant", content=final_output_cleaned, logger=logger_instance, metadata=None)
    _log_event(
        logger=logger_instance,
        history=context,
        role="assistant",
        content=final_output_cleaned
        # event_type is omitted, so metadata will be None as per _log_event logic, matching original behavior.
    )
    
    return final_output_cleaned 