from typing import Any, Callable, Awaitable, AsyncIterator, Dict, List, Optional
from .logging import record_conversation_event
import json

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
    raw_conversation_for_trace: List[Dict[str, Any]] = []
    raw_conversation_for_trace.extend(context)

    while True:
        tool_call_found = False
        thought_found = False
        prompt_for_this_step = context.copy()
        
        # Log the prompt for the current LLM call cycle
        record_conversation_event(
            history=raw_conversation_for_trace, # Does not affect history due to metadata
            role="llm_prompt",
            content=json.dumps(prompt_for_this_step),
            logger=logger_instance,
            metadata={"event_type": "llm_prompt"}
        )
        
        async for token in generate_tokens_fn(prompt_for_this_step):
            output_buffer.append(token)
            combined = "".join(output_buffer)

            if not thought_found:
                thought_content = extract_thought_fn(combined)
                if thought_content:
                    thought_found = True
                    record_conversation_event(
                        history=context,
                        role="assistant_thought", 
                        content=thought_content, 
                        logger=logger_instance, 
                        metadata={"event_type": "assistant_thought"}
                    )
                    raw_conversation_for_trace.append({"role": "assistant_thought", "content": thought_content})

            call_content = extract_tool_call_fn(combined)
            if call_content:
                tool_call_found = True
                raw_llm_response_with_call = combined
                
                record_conversation_event(
                    history=raw_conversation_for_trace, # Does not affect history due to metadata
                    role="llm_raw_response",
                    content=raw_llm_response_with_call,
                    logger=logger_instance,
                    metadata={"event_type": "llm_raw_response_with_tool_call"} # Keep this specific type
                )

                raw_conversation_for_trace.append({"role": "assistant", "content": raw_llm_response_with_call})
                
                tool_result = await handle_tool_call_fn(call_content, output_buffer)
                tool_result_block = f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"
                
                record_conversation_event(
                    history=context,
                    role="system", 
                    content=tool_result_block, 
                    logger=logger_instance, 
                    metadata={"event_type": "tool_result_injection"}
                )
                raw_conversation_for_trace.append({"role": "system", "content": tool_result_block})
                
                context.append({"role": "assistant", "content": raw_llm_response_with_call})
                context.append({"role": "system", "content": tool_result_block})
                
                output_buffer.clear()
                break

        if not tool_call_found:
            final_output_raw_no_tool = "".join(output_buffer) # This is the raw response for this turn
            record_conversation_event(
                 history=raw_conversation_for_trace, # Does not affect history due to metadata
                 role="llm_raw_response", 
                 content=final_output_raw_no_tool, 
                 logger=logger_instance, 
                 metadata={"event_type": "llm_raw_response_no_tool_call"} # New distinct type
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

    record_conversation_event(history=context, role="assistant", content=final_output_cleaned, logger=logger_instance, metadata=None)
    
    return final_output_cleaned 