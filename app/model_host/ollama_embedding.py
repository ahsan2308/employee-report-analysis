from typing import Dict, Any, List, Union, Optional, Sequence
import numpy as np
import ollama

from app.base.base_embedding import EmbeddingProvider
from app.core.logger import logger

class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider implementation using Ollama API.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "bge-m3", use_prefix: bool = True, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the Ollama embedding provider.
        
        Args:
            base_url: Base URL for the Ollama API
            model: Model name to use for embeddings (default: bge-m3)
            use_prefix: Whether to add "query:" or "passage:" prefixes to inputs
            api_key: Not used by Ollama, included for API compatibility with other providers
            **kwargs: Additional arguments (ignored)
        """
        self.base_url = base_url
        self.model = model
        self.use_prefix = use_prefix
        # api_key is ignored since Ollama doesn't use API keys
        if api_key:
            logger.debug("API key provided but not used by Ollama embedding provider")
        
        # Create a client with the specified host
        self.client = ollama.Client(host=self.base_url)
        
        logger.info(f"Initialized OllamaEmbeddingProvider with model {model} at {base_url}")
    
    def add_prefix(self, text: str, is_query: bool = False) -> str:
        """
        Add appropriate prefix to text for better embedding quality.
        
        Args:
            text: Input text to prefix
            is_query: Whether the text is a query (True) or passage (False)
            
        Returns:
            Prefixed text
        """
        if not self.use_prefix:
            return text
            
        prefix = "query" if is_query else "passage"
        return f"{prefix}: {text}"
    
    def get_embedding(self, text: Union[str, List[str]], is_query: bool = False, **kwargs) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings using Ollama API.
        
        Args:
            text: Either a single string or a list of strings
            is_query: Whether the text is a query (for prefix)
            **kwargs: Additional parameters
            
        Returns:
            For single input: a single embedding as List[float]
            For multiple inputs: multiple embeddings as List[List[float]]
        """
        try:
            # Handle single text vs batch
            is_single = isinstance(text, str)
            
            # Apply prefixes if configured
            if self.use_prefix:
                if is_single:
                    text_input = self.add_prefix(text, is_query)
                else:
                    text_input = [self.add_prefix(t, is_query) for t in text]
            else:
                text_input = text
                
            # Call Ollama embed endpoint
            response = self.client.embed(
                model=self.model,
                input=text_input
            )

            # Extract embeddings from response
            if hasattr(response, 'embeddings') and response.embeddings:
                embeddings = response.embeddings
            elif isinstance(response, dict) and 'embeddings' in response:
                embeddings = response['embeddings']
            else:
                return [] if is_single else [[]]
            
            # Apply L2 normalization to embeddings
            normalized = self.normalize_embedding(embeddings)
            
            # Return single embedding or list of embeddings based on input type
            if is_single:
                return normalized[0] if normalized else []
            else:
                return normalized
                
        except Exception as e:
            logger.error(f"Error generating embedding with Ollama: {e}")
            return [] if isinstance(text, str) else [[]]
    
    def normalize_embedding(self, embedding: Union[Sequence[float], Sequence[Sequence[float]], np.ndarray], 
                           as_numpy: bool = False) -> Union[List[float], List[List[float]], np.ndarray]:
        """
        Apply L2 normalization to embeddings.
        
        Args:
            embedding: Single embedding vector or list of embedding vectors
            as_numpy: If True, return numpy arrays directly (for compatibility with libraries like FAISS)
            
        Returns:
            Normalized embedding vector(s)
        """
        try:
            # Use asarray instead of array to avoid an extra copy if already ndarray
            vectors = np.asarray(embedding, dtype=np.float32)
            
            # Validate dimensions
            if vectors.ndim not in (1, 2):
                logger.warning(f"Expected 1D or 2D array for normalization, got shape {vectors.shape}")
                return embedding
                
            # Log shape info at debug level
            logger.debug(f"Normalizing embeddings shape: {vectors.shape}, dtype: {vectors.dtype}")
            
            # Check if we have a single vector or multiple vectors
            if vectors.ndim == 1:
                # Single vector: normalize with L2 norm
                norm = np.linalg.norm(vectors, ord=2)
                # Add epsilon directly in division to avoid extra comparison
                vectors = vectors / (norm + 1e-12)
            else:
                # Multiple vectors: normalize each vector with its L2 norm
                norms = np.linalg.norm(vectors, ord=2, axis=1, keepdims=True)
                # Avoid division by zero
                vectors = vectors / np.maximum(norms, 1e-12)
                
            # Return numpy array or Python list based on caller's preference
            return vectors if as_numpy else vectors.tolist()
                
        except (ValueError, TypeError) as e:
            # More specific exception handling for better debugging
            logger.error(f"Error normalizing embeddings ({type(e).__name__}): {e}")
            return embedding
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model.
        """
        try:
            response = self.client.show(self.model)
            return {
                "name": self.model,
                "provider": "ollama",
                "embedding_dimensions": len(self.get_embedding("test")),
                "details": response
            }
        except Exception as e:
            logger.error(f"Error getting model info from Ollama: {e}")
            return {
                "name": self.model,
                "provider": "ollama",
                "details": {}
            }
