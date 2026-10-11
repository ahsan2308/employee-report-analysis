from typing import Dict, Any, List, Union, Optional
import ollama

from app.integrations.embeddings.base import EmbeddingProvider
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
