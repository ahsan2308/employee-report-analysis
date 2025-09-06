import os
from typing import Optional
from app.utils.env_loader import load_env_from_file

from app.base.base_llm import LLMProvider
from app.base.base_embedding import EmbeddingProvider
from app.model_host.ollama import OllamaProvider
from app.model_host.ollama_embedding import OllamaEmbeddingProvider
from app.model_host.vllm import VLLMProvider
from app.model_host.vllm_embedding import VLLMEmbeddingProvider
from app.core.logger import logger

# Load environment variables
load_env_from_file()

# Provider selection (provider-agnostic)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
EMBEDDING_USE_PREFIX = os.getenv("EMBEDDING_USE_PREFIX", "false").lower() == "true"

# Ollama-specific settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", None)

# Ollama embedding-specific settings
OLLAMA_EMBEDDING_BASE_URL = os.getenv("OLLAMA_EMBEDDING_BASE_URL", OLLAMA_BASE_URL)
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_EMBEDDING_API_KEY = os.getenv("OLLAMA_EMBEDDING_API_KEY", OLLAMA_API_KEY)

# vLLM-specific settings
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", None)

# vLLM embedding-specific settings
VLLM_EMBEDDING_BASE_URL = os.getenv("VLLM_EMBEDDING_BASE_URL", "http://localhost:8001")
VLLM_EMBEDDING_MODEL = os.getenv("VLLM_EMBEDDING_MODEL", "BAAI/bge-m3")
VLLM_EMBEDDING_API_KEY = os.getenv("VLLM_EMBEDDING_API_KEY", VLLM_API_KEY)

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
