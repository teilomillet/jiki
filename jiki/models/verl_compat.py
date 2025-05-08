"""
Model wrapper for Hugging Face models loaded using verl's registry,
ensuring compatibility with both JikiOrchestrator and verl training.
"""
import asyncio
from typing import List, AsyncGenerator, Optional, Dict, Any

# Ensure verl is available in the environment
try:
    from verl.models.registry import ModelRegistry
except ImportError:
    print("Warning: 'verl' package not found. VerlCompatibleModel will not be usable.")
    ModelRegistry = None # type: ignore

# Ensure transformers is available
try:
    from transformers import AutoTokenizer, PreTrainedModel, PreTrainedTokenizer
    import torch
except ImportError:
    print("Warning: 'transformers' or 'torch' not found. VerlCompatibleModel will not be usable.")
    AutoTokenizer = None # type: ignore
    PreTrainedModel = None # type: ignore
    PreTrainedTokenizer = None # type: ignore
    torch = None # type: ignore

from jiki.sampling import ISamplerConfig, SamplerConfig

class VerlCompatibleModel:
    """
    Wraps a Hugging Face model loaded via verl's ModelRegistry.

    This wrapper allows JikiOrchestrator to use a locally loaded, potentially
    customized model (as defined by verl) for generation, while also providing
    access to the underlying model and tokenizer for training loops (e.g., in mcp-trainer
    using verl as a backend).
    """
    def __init__(self, 
                 model_arch: str, 
                 model_path: str, 
                 tokenizer_path: Optional[str] = None,
                 load_value_head: bool = False,
                 sampler_config: Optional[ISamplerConfig] = None, 
                 model_kwargs: Optional[Dict[str, Any]] = None):
        """
        Initializes and loads the model and tokenizer.

        Args:
            model_arch: The model architecture string recognized by verl's ModelRegistry (e.g., "LlamaForCausalLM").
            model_path: Path to the pre-trained Hugging Face model weights.
            tokenizer_path: Optional path to the tokenizer. If None, defaults to model_path.
            load_value_head: If True, attempts to load the value head version of the model via verl registry.
            sampler_config: Configuration for generation sampling parameters.
            model_kwargs: Additional keyword arguments passed to the model's `from_pretrained` method.
        """
        if not ModelRegistry or not AutoTokenizer or not torch:
            raise ImportError("'verl', 'transformers', or 'torch' not installed. Cannot initialize VerlCompatibleModel.")

        self.model_arch = model_arch
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path or model_path
        self.sampler_config: ISamplerConfig = sampler_config or SamplerConfig()
        self._model_kwargs = model_kwargs or {}

        # Load tokenizer
        try:
            self.tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
            # Ensure pad token is set if missing
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                print(f"Warning: Tokenizer for {self.tokenizer_path} missing pad_token. Set to eos_token: {self.tokenizer.eos_token}")
        except Exception as e:
            raise RuntimeError(f"Failed to load tokenizer from {self.tokenizer_path}: {e}") from e

        # Load model using verl registry
        VerlModelClass = ModelRegistry.load_model_cls(self.model_arch, value=load_value_head)
        if VerlModelClass is None:
            raise ValueError(f"Model architecture '{self.model_arch}' is not supported by verl's ModelRegistry.")
        
        print(f"Loading verl model class {VerlModelClass.__name__} from path {self.model_path}...")
        try:
            # Assuming verl model classes support from_pretrained
            # Pass torch_dtype if specified in kwargs, otherwise default might be used
            dtype_kwargs = {}
            if 'torch_dtype' in self._model_kwargs:
                dtype_str = str(self._model_kwargs['torch_dtype']).lower()
                if 'bfloat16' in dtype_str:
                    dtype_kwargs['torch_dtype'] = torch.bfloat16
                elif 'float16' in dtype_str:
                     dtype_kwargs['torch_dtype'] = torch.float16
                elif 'float32' in dtype_str:
                     dtype_kwargs['torch_dtype'] = torch.float32
                else:
                    # Keep original value if it's already a torch.dtype or unknown string
                     dtype_kwargs['torch_dtype'] = self._model_kwargs['torch_dtype']
            
            # Combine specific dtype kwargs with other kwargs
            combined_kwargs = {**self._model_kwargs, **dtype_kwargs}
            
            self.model: PreTrainedModel = VerlModelClass.from_pretrained(self.model_path, **combined_kwargs)
            # Try to move model to GPU if available
            if torch.cuda.is_available():
                try:
                   self.model.to(torch.cuda.current_device())
                   print(f"Moved model {self.model_path} to device: {torch.cuda.current_device()}")
                except Exception as e:
                    print(f"Warning: Failed to move model to GPU: {e}")
            else:
                 print(f"Warning: No CUDA device found. Model {self.model_path} will run on CPU.")

        except Exception as e:
            raise RuntimeError(f"Failed to load verl model {VerlModelClass.__name__} from {self.model_path}: {e}") from e
        
        self.model_name = f"verl::{self.model_arch}::{self.model_path}" # For identification

    async def generate_tokens(self, messages: List[dict]) -> AsyncGenerator[str, None]:
        """
        Async generator yielding tokens using the loaded Hugging Face model.
        Note: This basic implementation is synchronous internally for generation
              but wrapped in async generator for compatibility with JikiOrchestrator.
              Real async generation with HF models is more complex.

        Args:
            messages: List of message dicts (OpenAI/Anthropic format).
                      Currently simplified: Assumes last message is user prompt,
                      concatenates content for basic generation.
                      Needs proper conversion to prompt format for the specific model.

        Returns: Async generator of text tokens.
        """
        # --- Basic Prompt Formatting (Needs Improvement) ---
        # This needs to be adapted based on how the specific model expects prompts.
        # Using apply_chat_template is preferred if available.
        prompt_text = ""
        if hasattr(self.tokenizer, 'apply_chat_template'):
             try:
                 # Ensure roles are 'user', 'assistant', 'system' if needed
                 formatted_messages = []
                 for msg in messages:
                     role = msg.get('role', 'user')
                     content = msg.get('content', '')
                     # Adjust roles if needed, e.g., map 'system' to first 'user' for some models
                     formatted_messages.append({'role': role, 'content': content})
                 
                 # `tokenize=False` returns a string prompt
                 prompt_text = self.tokenizer.apply_chat_template(formatted_messages, tokenize=False, add_generation_prompt=True)
             except Exception as e:
                 print(f"Warning: Failed to apply chat template: {e}. Falling back to simple concatenation.")
                 prompt_text = "\n".join([m.get('content', '') for m in messages])
        else:
             # Simple concatenation fallback
             prompt_text = "\n".join([m.get('content', '') for m in messages])

        # --- Tokenization --- 
        # Generation typically works best with input_ids, not text prompts.
        inputs = self.tokenizer(prompt_text, return_tensors="pt")
        # Move inputs to the same device as the model
        try:
             inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        except Exception as e:
             print(f"Warning: Failed to move input tensors to model device ({self.model.device}): {e}")
        
        # --- Generation --- 
        # Combine sampling parameters
        sampling_params = self.sampler_config.to_dict()
        max_new_tokens = sampling_params.pop("max_tokens", 50) # Max tokens in HF is max_new_tokens
        
        # Use torch.no_grad() for inference
        with torch.no_grad():
             # `generate` is synchronous in Hugging Face transformers
             # TODO: Explore async generation options or streaming decoders if needed.
             output_ids = self.model.generate(
                 **inputs,
                 max_new_tokens=max_new_tokens,
                 pad_token_id=self.tokenizer.pad_token_id, # Ensure pad token is set
                 eos_token_id=self.tokenizer.eos_token_id,
                 **sampling_params
             )

        # --- Decoding --- 
        # Decode only the newly generated tokens
        input_length = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0, input_length:]
        generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        # --- Yielding (Simulated Stream) --- 
        # Yield the whole generated text at once as a single item in the async generator.
        # A true streaming implementation would decode token by token.
        # Use asyncio.sleep(0) to yield control briefly, making it behave like an async source.
        yield generated_text
        await asyncio.sleep(0) 

    def get_verl_model(self) -> PreTrainedModel:
        """Returns the underlying verl-compatible model instance."""
        return self.model
    
    def get_tokenizer(self) -> PreTrainedTokenizer:
        """Returns the Hugging Face tokenizer instance."""
        return self.tokenizer 