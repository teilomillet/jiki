from typing import Protocol, Optional, List, Dict
from dataclasses import dataclass


class ISamplerConfig(Protocol):
    """
    Interface for LLM sampling configuration parameters, following MCP sampling guidelines.

    See Model Context Protocol Sampling spec: https://modelcontextprotocol.io/docs/concepts/sampling

    Sampling parameters control model behavior at runtime:
      - temperature: randomness in sampling (0.0 = deterministic, 1.0 = default)
      - top_p: nucleus sampling threshold (1.0 = disabled)
      - max_tokens: maximum number of tokens to generate (optional)
      - stop: list of strings where generation should stop (optional)

    Example:
        class MySamplerConfig:
            temperature = 0.5
            top_p = 0.9
            max_tokens = 200
            stop = ["\n"]

            def to_dict(self):
                return {
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "max_tokens": self.max_tokens,
                    "stop": self.stop
                }
    """
    temperature: float
    top_p: float
    max_tokens: Optional[int]
    stop: Optional[List[str]]
    
    def to_dict(self) -> Dict[str, any]:
        """
        Convert sampling parameters to a dict for LLM APIs.
        """
        ...


@dataclass
class SamplerConfig:
    """
    Default dataclass for LLM sampling configuration.

    Controls how the underlying LLM samples tokens:
      - temperature (float): sampling randomness (lower = more deterministic).
      - top_p (float): nucleus sampling probability (lower = restrict options).
      - max_tokens (Optional[int]): cap on tokens generated.
      - stop (Optional[List[str]]): stop sequences to terminate generation early.

    Example:
        config = SamplerConfig(
            temperature=0.7,
            top_p=0.8,
            max_tokens=300,
            stop=["###"]
        )

    To apply in an LLM API call:
        params = config.to_dict()
        response = llm_api.create(
            model="gpt-4",
            messages=messages,
            **params
        )
    """
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, any]:
        """
        Convert to dict, omitting None values.
        """
        params = {"temperature": self.temperature, "top_p": self.top_p}
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.stop is not None:
            params["stop"] = self.stop
        return params 