import json
from typing import Dict, Any, List, Optional, Union
import ollama  
from app.base.base_llm import LLMProvider
from app.core.logger import logger


class OllamaProvider(LLMProvider):
    """
    LLM provider implementation using Ollama API.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        """
        Initialize the Ollama provider.
        
        Args:
            base_url: Base URL for the Ollama API
            model: Model name to use
        """
        self.base_url = base_url
        self.model = model
        
        # Create a client with the specified host
        self.client = ollama.Client(host=self.base_url)
        
        logger.info(f"Initialized OllamaProvider with model {model} at {base_url}")
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text using Ollama API.
        """
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            )
            return response.get("response", "")
        except Exception as e:
            logger.error(f"Error generating text with Ollama: {e}")
            return ""
    
    def get_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings using Ollama API.
        
        Args:
            text: Either a single string or a list of strings
            
        Returns:
            For single input: a single embedding as List[float]
            For multiple inputs: multiple embeddings as List[List[float]]
        """
        try:
            response = self.client.embed(
                model=self.model,
                input=text  
            )

            if hasattr(response, 'embeddings') and response.embeddings:
                embeddings = response.embeddings
            elif isinstance(response, dict) and 'embeddings' in response:
                embeddings = response['embeddings']
            else:
                return [] if isinstance(text, str) else [[]]
                
            # Return single embedding or list of embeddings based on input type
            if isinstance(text, str):
                return embeddings[0] if embeddings else []
            else:
                return embeddings
                
        except Exception as e:
            logger.error(f"Error generating embedding with Ollama: {e}")
            return [] if isinstance(text, str) else [[]]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model.
        """
        try:
            response = self.client.show(
                name=self.model
            )
            return {
                "name": self.model,
                "provider": "ollama",
                "details": response
            }
        except Exception as e:
            logger.error(f"Error getting model info from Ollama: {e}")
            return {
                "name": self.model,
                "provider": "ollama",
                "details": {}
            }
