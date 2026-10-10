"""
Embedding service for generating text embeddings using various providers.
This is the new modular implementation that replaces app.core.embeddings.
"""

from typing import List
from app.model_host import get_embedding_provider
from app.core.logger import logger
from app.core.settings import EMBEDDING_PROVIDER, EMBEDDING_DEFAULT_MODEL as DEFAULT_MODEL  # noqa: F401  (module attributes kept for compatibility)


def get_embedding(text: str, model_name: str = None, is_query: bool = False) -> list:
    """
    Generates an embedding for the given text using the configured LLM provider.

    :param text: The text to embed
    :param model_name: Optional model name override
    :param is_query: Whether the text is a query (True) or passage (False)
    :return: A list representing the vector embedding
    """
    try:
        # Get the LLM provider (default from config/env)
        provider = get_embedding_provider()
        
        # If model_name is provided, create a new provider instance with that model
        if model_name:
            provider = get_embedding_provider(model=model_name)
            
        # Log the model being used for debugging
        logger.debug(f"Generating embedding with model: {provider.model}")
            
        # Get embedding from the provider, passing is_query parameter
        embedding = provider.get_embedding(text, is_query=is_query)
        
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

def get_embeddings(texts: List[str], model_name: str = None, is_query: bool = False) -> List[list]:
    """
    Generates embeddings for multiple texts in a single batch operation.
    This is more efficient than calling get_embedding() multiple times.
    
    :param texts: List of texts to embed
    :param model_name: Optional model name override
    :param is_query: Whether the texts are queries (True) or passages (False)
    :return: List of embeddings corresponding to the input texts
    """
    if not texts:
        return []
        
    try:
        # Get the LLM provider (default from config/env)
        provider = get_embedding_provider()
        
        # If model_name is provided, create a new provider instance with that model
        if model_name:
            provider = get_embedding_provider(model=model_name)
            
        # Log the model being used for debugging
        logger.debug(f"Generating batch embeddings for {len(texts)} texts with model: {provider.model}")
        
        # Get embeddings from the provider in a single batch operation, passing is_query parameter
        embeddings = provider.get_embedding(texts, is_query=is_query)
        
        # Log basic embedding info for debugging
        if embeddings and isinstance(embeddings, list):
            logger.debug(f"Generated {len(embeddings)} embeddings successfully")
        else:
            logger.warning("Empty or invalid embeddings returned from provider")
            return []
            
        return embeddings
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [[] for _ in range(len(texts))]  # Return empty embeddings for each input text
