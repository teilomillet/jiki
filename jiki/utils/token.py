from typing import List, Dict

# Cache encoders per model_name to avoid reinitializing
_encoders = {}

try:
    import tiktoken  # type: ignore
except ImportError:
    tiktoken = None



def count_tokens(messages: List[Dict[str, str]], model_name: str) -> int:
    """
    Count the number of tokens in a list of messages for a given model.
    Uses tiktoken when available, otherwise falls back to a character-based heuristic.
    """
    if tiktoken is not None:
        # Reuse encoder if already loaded
        if model_name in _encoders:
            enc = _encoders[model_name]
        else:
            try:
                enc = tiktoken.encoding_for_model(model_name)
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")
            _encoders[model_name] = enc
        tokens = 0
        for m in messages:
            tokens += 4  # per-message overhead tokens
            tokens += len(enc.encode(m.get("content", "")))
        return tokens
    # Fallback heuristic: 1 token ≈ 4 characters
    return len(str(messages)) // 4 