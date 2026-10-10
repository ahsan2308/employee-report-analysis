from typing import Optional
from app.utils.env_loader import load_env_from_file

from app.integrations.llm.base import LLMProvider
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.llm.ollama import OllamaProvider
from app.integrations.embeddings.ollama import OllamaEmbeddingProvider
from app.integrations.llm.vllm import VLLMProvider
from app.integrations.embeddings.vllm import VLLMEmbeddingProvider
from app.core.logger import logger

# Load environment variables
load_env_from_file()

# Provider selection (provider-agnostic)
from app.core.settings import (
    LLM_PROVIDER,
    EMBEDDING_PROVIDER,
    EMBEDDING_USE_PREFIX,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_API_KEY,
    OLLAMA_EMBEDDING_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_EMBEDDING_API_KEY,
    VLLM_BASE_URL,
    VLLM_MODEL,
    VLLM_API_KEY,
    VLLM_EMBEDDING_BASE_URL,
    VLLM_EMBEDDING_MODEL,
    VLLM_EMBEDDING_API_KEY,
)

def get_llm_provider(provider_type: Optional[str] = None, **kwargs) -> LLMProvider:
    """
    Factory function to get an LLM provider instance.
    
    Args:
        provider_type: Type of provider ("ollama", "vllm", etc.)
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        An instance of LLMProvider
    """
    # Use environment variable if provider_type not specified
    if provider_type is None:
        provider_type = LLM_PROVIDER
    
    # Set default values from environment if not in kwargs
    if "base_url" not in kwargs:
        if provider_type.lower() == "vllm":
            kwargs["base_url"] = VLLM_BASE_URL
        else:
            kwargs["base_url"] = OLLAMA_BASE_URL
    
    if "model" not in kwargs:
        if provider_type.lower() == "vllm":
            logger.debug(f"Using vLLM model from environment: {VLLM_MODEL}")
            kwargs["model"] = VLLM_MODEL
        else:
            logger.debug(f"Using Ollama model from environment: {OLLAMA_MODEL}")
            kwargs["model"] = OLLAMA_MODEL
    else:
        logger.debug(f"Using explicitly provided model: {kwargs['model']}")
    
    # Add API key if available
    if "api_key" not in kwargs:
        if provider_type.lower() == "vllm":
            kwargs["api_key"] = VLLM_API_KEY
        else:
            kwargs["api_key"] = OLLAMA_API_KEY
    
    if provider_type.lower() == "ollama":
        return OllamaProvider(**kwargs)
    elif provider_type.lower() == "vllm":
        return VLLMProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")

def get_embedding_provider(provider_type: Optional[str] = None, **kwargs) -> EmbeddingProvider:
    """
    Factory function to get an embedding provider instance.
    
    Args:
        provider_type: Type of provider ("ollama", "vllm", etc.)
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        An instance of EmbeddingProvider
    """
    # Use environment variable if provider_type not specified
    if provider_type is None:
        provider_type = EMBEDDING_PROVIDER
    
    # Set default values from environment if not in kwargs
    if "base_url" not in kwargs:
        if provider_type.lower() == "vllm":
            kwargs["base_url"] = VLLM_EMBEDDING_BASE_URL
        else:
            kwargs["base_url"] = OLLAMA_EMBEDDING_BASE_URL
    
    if "model" not in kwargs:
        if provider_type.lower() == "vllm":
            logger.debug(f"Using vLLM embedding model from environment: {VLLM_EMBEDDING_MODEL}")
            kwargs["model"] = VLLM_EMBEDDING_MODEL
        else:
            logger.debug(f"Using Ollama embedding model from environment: {OLLAMA_EMBEDDING_MODEL}")
            kwargs["model"] = OLLAMA_EMBEDDING_MODEL
    
    if "use_prefix" not in kwargs:
        kwargs["use_prefix"] = EMBEDDING_USE_PREFIX
    
    # Add API key if available
    if "api_key" not in kwargs:
        if provider_type.lower() == "vllm":
            kwargs["api_key"] = VLLM_EMBEDDING_API_KEY
        else:
            kwargs["api_key"] = OLLAMA_EMBEDDING_API_KEY
    
    if provider_type.lower() == "ollama":
        return OllamaEmbeddingProvider(**kwargs)
    elif provider_type.lower() == "vllm":
        return VLLMEmbeddingProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider_type}")
