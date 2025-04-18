from typing import Any, Callable, Awaitable, AsyncIterator, Dict, List, Optional

async def generate_and_intercept(
    generate_tokens_fn: Callable[[List[Dict[str, str]]], AsyncIterator[str]],
    handle_tool_call_fn: Callable[[str, List[str]], Awaitable[str]],
    extract_tool_call_fn: Callable[[str], Optional[str]],
    extract_thought_fn: Callable[[str], Optional[str]],
    clean_fn: Callable[[str], str],
    log_complete_trace_fn: Optional[Callable[[Dict[str, Any]], None]],
    log_conversation_fn: Callable[[str, str], None],
    context: List[Dict[str, str]]
) -> str:
    """
    Stream tokens from the LLM, intercepting tool-call and thought blocks.
    Returns the final cleaned assistant response.
    """
    output_buffer: List[str] = []
    raw_conversation: List[Dict[str, Any]] = []
    # record initial system content
    raw_conversation.append({
        "role": "system",
        "content": str(context[0].get("content", "")) if context else ""
    })

    while True:
        tool_call_found = False
        thought_found = False
        async for token in generate_tokens_fn(context):
            output_buffer.append(token)
            combined = "".join(output_buffer)

            # detect thoughts only until first found
            if not thought_found:
                thought_content = extract_thought_fn(combined)
                if thought_content:
                    thought_found = True
                    # continue streaming

            # detect tool calls
            call_content = extract_tool_call_fn(combined)
            if call_content:
                tool_call_found = True
                # record assistant up to tool call
                raw_conversation.append({"role": "assistant", "content": combined})
                # execute tool
                tool_result = await handle_tool_call_fn(call_content, output_buffer)
                # record tool result
                raw_conversation.append({"role": "system", "content": f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"})
                # inject into context
                context.append({"role": "assistant", "content": combined})
                context.append({"role": "system", "content": f"<mcp_tool_result>\n{tool_result}\n</mcp_tool_result>"})
                # reset buffer and restart
                output_buffer.clear()
                break

        if not tool_call_found:
            # final assistant output
            raw_conversation.append({"role": "assistant", "content": "".join(output_buffer)})
            break

    final_output = "".join(output_buffer)
    cleaned = clean_fn(final_output)

    # log complete trace if available
    if log_complete_trace_fn:
        log_complete_trace_fn({
            "conversation": raw_conversation,
            "final_clean_output": cleaned,
            "reward": None
        })

    # log final assistant message
    log_conversation_fn("assistant", cleaned)
    return cleaned 