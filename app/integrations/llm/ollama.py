import json
from typing import Dict, Any, List, Optional, Union, Type
import ollama  
from app.integrations.llm.base import LLMProvider
from app.core.logger import logger

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class OllamaProvider(LLMProvider):
    """
    LLM provider implementation using Ollama API.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:8b", api_key: Optional[str] = None, **kwargs):
        """
        Initialize the Ollama provider.
        
        Args:
            base_url: Base URL for the Ollama API
            model: Model name to use
            api_key: Not used by Ollama, included for API compatibility with other providers
            **kwargs: Additional arguments (ignored)
        """
        self.base_url = base_url
        self.model = model
        # api_key is ignored since Ollama doesn't use API keys
        if api_key:
            logger.debug("API key provided but not used by Ollama provider")
        
        # Create a client with the specified host
        self.client = ollama.Client(host=self.base_url)
        
        logger.info(f"Initialized OllamaProvider with model {model} at {base_url}")
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, stream: bool = False, num_ctx: int = 8192) -> str:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            stream: Whether to stream the response (not currently implemented in Ollama provider)
            num_ctx: Context window size (Ollama-specific parameter)

        Raises:
            Exception: whatever the Ollama client raises, so the caller can retry or fail the run
        """
        # If streaming is requested, log that it's not implemented
        if stream:
            logger.warning("Streaming not implemented in Ollama provider, returning full response")

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "num_ctx": num_ctx,
            }
        )
        return response.get("response", "")
    
    def generate_structured_output(
        self,
        prompt: str,
        json_schema: Union[Dict[str, Any], Type[BaseModel]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.0,
        num_ctx: int = 8192
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a structured output using Ollama's native support for structured outputs.
        
        This method instructs the model to produce a response in JSON format conforming to
        the provided JSON schema. For best results, the temperature is set to 0 (or close to 0)
        to ensure consistency.
        
        Args:
            prompt: The main prompt for the model.
            json_schema: Either a dictionary representing the JSON schema or a Pydantic BaseModel class.
            max_tokens: Maximum number of tokens for the response.
            temperature: Sampling temperature for the generation (0 recommended for structured outputs).
        
        Returns:
            A dictionary parsed from the JSON output of the model, or None if the answer is empty or not JSON.

        Raises:
            Exception: whatever the Ollama client raises
        """
        # Process schema if it's a Pydantic model
        schema_dict = json_schema
        if HAS_PYDANTIC and hasattr(json_schema, 'model_json_schema'):
            schema_dict = json_schema.model_json_schema()
        elif HAS_PYDANTIC and isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            schema_dict = json_schema.model_json_schema()
            
        # Add instruction to return as JSON to help model understand
        enhanced_prompt = f"{prompt}\n\nReturn as JSON according to the specified schema."
            
        # According to latest Ollama API, format is a top-level parameter, not part of options.
        # Client errors propagate; an empty or unparseable answer returns None (the caller falls back).
        response = self.client.generate(
            model=self.model,
            prompt=enhanced_prompt,
            format=schema_dict,  # Format is now a top-level parameter
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "num_ctx": num_ctx,

            }
        )

        output_text = response.get("response", "")
        if not output_text:
            logger.warning("Empty response from Ollama structured output")
            return None

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}, response: {output_text}")
            return None

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
            response = self.client.show(self.model)
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
