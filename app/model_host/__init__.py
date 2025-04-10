import os
from typing import Optional
from app.utils.env_loader import load_env_from_file

from app.base.base_llm import LLMProvider
from app.model_host.ollama import OllamaProvider
from app.core.logger import logger

# Load environment variables
load_env_from_file()

# Get LLM settings from environment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("MODEL_LLM", "llama3.1:8b")

def get_llm_provider(provider_type: Optional[str] = None, **kwargs) -> LLMProvider:
    """
    Factory function to get an LLM provider instance.
    
    Args:
        provider_type: Type of provider ("ollama", "openai", etc.)
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        An instance of LLMProvider
    """
    # Use environment variable if provider_type not specified
    if provider_type is None:
        provider_type = LLM_PROVIDER
    
    # Set default values from environment if not in kwargs
    if "base_url" not in kwargs:
        kwargs["base_url"] = LLM_BASE_URL
    if "model" not in kwargs:
        # Log the model being used to trace where gemini is coming from
        logger.debug(f"Using model from environment: {LLM_MODEL}")
        kwargs["model"] = LLM_MODEL
    else:
        logger.debug(f"Using explicitly provided model: {kwargs['model']}")
    
    if provider_type.lower() == "ollama":
        return OllamaProvider(**kwargs)
    # Add more providers here as needed, e.g.:
    # elif provider_type.lower() == "openai":
    #     return OpenAIProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")
