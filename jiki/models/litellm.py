import os
from typing import List, AsyncGenerator, Optional
from jiki.sampling import ISamplerConfig, SamplerConfig
import litellm

class LiteLLMModel:
    """
    Wrapper for LiteLLM providing async token streaming with configurable sampling.
    """
    def __init__(self, model_name: str, sampler_config: Optional[ISamplerConfig] = None):
        self.model_name = model_name
        # Use provided sampler_config or default parameters
        self.sampler_config: ISamplerConfig = sampler_config or SamplerConfig()
        # API keys are set via environment variables as per LiteLLM docs

    async def generate_tokens(self, messages: List[dict]) -> AsyncGenerator[str, None]:
        """
        Async generator yielding tokens from LiteLLM with sampler config.

        :param messages: List of message dicts (OpenAI/Anthropic format)
        :return: Async generator of text tokens
        """
        # Merge sampling parameters into request
        sampling_params = self.sampler_config.to_dict()
        response = litellm.completion(
            model=self.model_name,
            messages=messages,
            stream=True,
            **sampling_params
        )
        for chunk in response:
            # Each chunk is a dict with 'choices' -> 'delta' -> 'content'
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content 