from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Type

try:
    from pydantic import BaseModel  # noqa: F401  (availability check)
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Implement this class for each LLM provider you want to support.
    """
    
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, stream: bool = False, **kwargs) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            stream: Whether to stream the response (if supported)
            **kwargs: Provider-specific parameters (e.g., num_ctx for Ollama)
            
        Returns:
            Generated text from the LLM
        """
        pass
    
    @abstractmethod
    def generate_structured_output(
        self,
        prompt: str,
        json_schema: Union[Dict[str, Any], Type] = None,
        max_tokens: int = 1000,
        temperature: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a structured output (typically JSON) based on a prompt and schema.
        
        Args:
            prompt: The prompt to send to the LLM
            json_schema: Schema definition for the expected response format
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 recommended for structured outputs)
            
        Returns:
            Parsed JSON response as a dictionary, or None if parsing fails
        """
        pass
    
    @abstractmethod
    def get_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate an embedding vector for the given text or texts.
        
        Args:
            text: The text to embed (string or list of strings)
            
        Returns:
            Embedding vector(s) as a list of floats or list of lists of floats
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model.
        
        Returns:
            Dictionary containing model information
        """
        pass

