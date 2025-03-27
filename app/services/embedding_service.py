"""
Embedding service for generating text embeddings using various providers.
This is the new modular implementation that replaces app.core.embeddings.
"""

from app.model_host import get_llm_provider
from app.core.logger import logger
from app.core.config_provider import get_config_provider

# Get configuration
config = get_config_provider()
DEFAULT_MODEL = config.get("embedding_model", "default_embedding_model", section="llm")

def get_embedding(text: str, model_name: str = None) -> list:
    """
    Generates an embedding for the given text using the configured LLM provider.

    :param text: The text to embed
    :param model_name: Optional model name override
    :return: A list representing the vector embedding
    """
    try:
        # Get the LLM provider (default from config/env)
        provider = get_llm_provider()
        
        # If model_name is provided, create a new provider instance with that model
        if model_name:
            provider = get_llm_provider(model=model_name)
            
        # Log the model being used for debugging
        logger.debug(f"Generating embedding with model: {provider.model}")
            
        # Get embedding from the provider
        embedding = provider.get_embedding(text)
        
        # Log basic embedding info for debugging
        if embedding:
            logger.debug(f"Embedding generated successfully with dimension: {len(embedding)}")
        else:
            logger.warning("Empty embedding returned from provider")
            
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
