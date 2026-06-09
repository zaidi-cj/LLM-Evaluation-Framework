import time
import logging
from typing import Dict, Any, List, Optional
import litellm
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Ensure API keys are set from config
if settings.OPENAI_API_KEY:
    litellm.openai_key = settings.OPENAI_API_KEY
if settings.GEMINI_API_KEY:
    litellm.gemini_key = settings.GEMINI_API_KEY
if settings.ANTHROPIC_API_KEY:
    litellm.anthropic_key = settings.ANTHROPIC_API_KEY

class LLMCallResponse:
    def __init__(
        self,
        text: str,
        latency_seconds: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        error_message: Optional[str] = None
    ):
        self.text = text
        self.latency_seconds = latency_seconds
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd
        self.error_message = error_message

def call_target_model(
    model_name: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    parameters: Optional[Dict[str, Any]] = None
) -> LLMCallResponse:
    """
    Calls an LLM using LiteLLM, abstracting OpenAI, Anthropic, Gemini, Llama, Qwen, etc.
    Measures latency, extracts token usage, and calculates execution cost.
    Bypasses network for models prefixed with mock/ to ensure instant execution.
    """
    if model_name.startswith("mock/"):
        time.sleep(0.02)  # Simulate minor processing delay
        prompt_lower = prompt.lower()
        if "select" in prompt_lower or "table" in prompt_lower or "name" in prompt_lower:
            mock_text = "SELECT name FROM employees WHERE id = 2;"
        elif "summar" in prompt_lower:
            mock_text = "This is a mock summary of the user input query, demonstrating conciseness."
        elif "quantum" in prompt_lower:
            mock_text = "Quantum computing is a type of computing that performs calculations using qubits based on quantum physics."
        else:
            mock_text = f"Mock evaluation response for query: {prompt}"
            
        return LLMCallResponse(
            text=mock_text,
            latency_seconds=0.02,
            prompt_tokens=15,
            completion_tokens=20,
            cost_usd=0.00005
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    additional_params = parameters or {}
    
    start_time = time.time()
    try:
        # LiteLLM completes the call dynamically based on the model prefix
        # Examples: "openai/gpt-4o", "anthropic/claude-3-5-sonnet", "gemini/gemini-1.5-pro", etc.
        response = litellm.completion(
            model=model_name,
            messages=messages,
            temperature=temperature,
            **additional_params
        )
        latency = time.time() - start_time
        
        text = response.choices[0].message.content or ""
        
        # Extract token usage and cost
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        
        try:
            # LiteLLM built-in cost calculation
            cost_usd = litellm.completion_cost(completion_response=response) or 0.0
        except Exception:
            # Fallback approximate cost calculation if LiteLLM doesn't support pricing lookup for the model
            cost_usd = 0.0
            
        return LLMCallResponse(
            text=text,
            latency_seconds=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd
        )
        
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"Error calling model {model_name}: {str(e)}", exc_info=True)
        return LLMCallResponse(
            text="",
            latency_seconds=latency,
            error_message=str(e)
        )
