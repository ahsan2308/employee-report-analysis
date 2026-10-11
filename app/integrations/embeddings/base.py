from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union, Sequence
import numpy as np

from app.core.logger import logger

class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    Implement this class for each embedding provider you want to support.
    """
    
    @abstractmethod
    def get_embedding(self, text: Union[str, List[str]], is_query: bool = False, **kwargs) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for a single text or a batch of texts.
        
        Args:
            text: Either a single string or a list of strings to embed
            is_query: Whether the text is a query (True) or passage (False)
            **kwargs: Additional parameters for embedding generation
            
        Returns:
            For single input: a single embedding as List[float]
            For multiple inputs: multiple embeddings as List[List[float]]
        """
        pass
    
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
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dictionary containing model information
        """
        pass
