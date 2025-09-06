from typing import Dict, Any, List, Union, Optional, Sequence
import numpy as np
import requests
from app.base.base_embedding import EmbeddingProvider
from app.core.logger import logger

class VLLMEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider implementation using vLLM API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", model: str = "BAAI/bge-m3", 
                 api_key: Optional[str] = None, use_prefix: bool = False, timeout: float = 60.0):
        """
        Initialize the vLLM embedding provider.
        
        Args:
            base_url: Base URL for the vLLM API
            model: Model name to use for embeddings
            api_key: API key for authorization
            use_prefix: Whether to add "query:" or "passage:" prefixes to inputs
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.use_prefix = use_prefix
        self.timeout = timeout
        self.api_key = api_key
        
        # Create a session for connection pooling
        self.session = requests.Session()
        
        # Set up headers - make sure to include Authorization if API key is provided
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.debug(f"Authorization header set for vLLM embedding provider")
        else:
            logger.debug(f"No API key provided for vLLM embedding provider")
            
        self.embedding_endpoint = f"{self.base_url}/v1/embeddings"
        
        logger.info(f"Initialized VLLMEmbeddingProvider with model {model} at {base_url}")
        
        # Validate the model ID
        self._validate_model_id()
    
    def _validate_model_id(self):
        """Validate if the model ID exists in the served models"""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/models", 
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            models = response.json()
            
            # Check if our model ID is in the list of available models
            available_models = [m.get("id") for m in models.get("data", [])]
            if self.model not in available_models:
                if len(available_models) == 1:
                    logger.warning(f"Model '{self.model}' not found. Auto-replacing with available model: {available_models[0]}")
                    self.model = available_models[0]
                else:
                    available_str = ", ".join(available_models)
                    logger.warning(f"Model '{self.model}' not found in available models: {available_str}")
        except Exception as e:
            logger.warning(f"Could not validate model ID: {e}")
    
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
        Generate embeddings using vLLM API.
        
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
            
            # Convert single input to list for API
            input_texts = [text_input] if is_single else text_input
                
            # Call vLLM embed endpoint
            payload = {
                "model": self.model,
                "input": input_texts
            }
            
            response = self.session.post(
                self.embedding_endpoint, 
                json=payload, 
                headers=self.headers,
                timeout=self.timeout
            )
            
            try:
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Embedding request failed: {e}, Response: {response.text}")
                return [] if is_single else [[]]
                
            result = response.json()
            
            # Extract embeddings from response
            if "data" in result and len(result["data"]) > 0:
                embeddings = [item["embedding"] for item in result["data"]]
            else:
                return [] if is_single else [[]]
            
            # BGE-M3 embeddings are already normalized, but we'll normalize again to be safe
            # This is redundant but harmless
            normalized = self.normalize_embedding(embeddings)
            
            # Return single embedding or list of embeddings based on input type
            if is_single:
                return normalized[0] if normalized else []
            else:
                return normalized
                
        except Exception as e:
            logger.error(f"Error generating embedding with vLLM: {e}")
            return [] if is_single else [[]]
    
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
            response = self.session.get(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            models = response.json()
            
            # Find our model in the list
            model_info = next((m for m in models.get("data", []) if m.get("id") == self.model), {})
            
            # Try to get embedding dimensions - note this makes an API call
            try:
                embedding_dimensions = len(self.get_embedding("test"))
            except:
                embedding_dimensions = None
            
            return {
                "name": self.model,
                "provider": "vllm",
                "embedding_dimensions": embedding_dimensions,
                "details": model_info,
                "available_models": [m.get("id") for m in models.get("data", [])]
            }
        except Exception as e:
            logger.error(f"Error getting model info from vLLM: {e}")
            return {
                "name": self.model,
                "provider": "vllm",
                "details": {}
            }
