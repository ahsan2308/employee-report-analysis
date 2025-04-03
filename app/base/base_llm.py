from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Implement this class for each LLM provider you want to support.
    """
    
    @abstractmethod
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Generated text from the LLM
        """
        pass
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
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

