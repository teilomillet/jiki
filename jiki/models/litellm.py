import os
from typing import List, AsyncGenerator
import litellm

class LiteLLMModel:
    """
    Wrapper for LiteLLM to provide async token streaming for any supported model.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        # API keys are set via environment variables as per LiteLLM docs

    async def generate_tokens(self, messages: List[dict]) -> AsyncGenerator[str, None]:
        """
        Async generator that yields tokens from the LiteLLM model as they are streamed.
        :param messages: List of message dicts (OpenAI/Anthropic format)
        """
        response = litellm.completion(
            model=self.model_name,
            messages=messages,
            stream=True
        )
        for chunk in response:
            # Each chunk is a dict with 'choices' -> 'delta' -> 'content'
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content 