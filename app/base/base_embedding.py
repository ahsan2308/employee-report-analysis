from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union, Optional, Sequence
import numpy as np

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
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dictionary containing model information
        """
        pass
