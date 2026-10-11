"""
Embedding service for generating text embeddings using various providers.
This is the new modular implementation that replaces app.core.embeddings.
"""

from typing import List
from app.integrations.providers import get_embedding_provider
from app.core.logger import logger
from app.core.settings import VECTOR_EMBEDDING_BATCH_SIZE
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
    Generates embeddings for multiple texts, in calls of at most
    VECTOR_EMBEDDING_BATCH_SIZE texts (vector_db.batch_processing.embedding_batch_size).

    :param texts: List of texts to embed
    :param model_name: Optional model name override
    :param is_query: Whether the texts are queries (True) or passages (False)
    :return: One embedding per text, in order; an empty list if any call fails
    """
    if not texts:
        return []
        
    try:
        # The configured provider, or one for the given model
        provider = get_embedding_provider(model=model_name) if model_name else get_embedding_provider()
        batch_size = max(1, VECTOR_EMBEDDING_BATCH_SIZE)
        logger.debug(f"Generating embeddings for {len(texts)} texts in batches of {batch_size} with model: {provider.model}")

        embeddings = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            batch_embeddings = provider.get_embedding(batch, is_query=is_query)
            if not batch_embeddings or not isinstance(batch_embeddings, list) or len(batch_embeddings) != len(batch):
                logger.warning("Empty or invalid embeddings returned from provider")
                return []
            embeddings.extend(batch_embeddings)

        logger.debug(f"Generated {len(embeddings)} embeddings successfully")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # No partial result: callers check for one embedding per text
        return []
