import json
import requests
from typing import Dict, Any, List, Optional, Union, Type
from app.integrations.llm.base import LLMProvider
from app.core.logger import logger

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class VLLMProvider(LLMProvider):
    """
    LLM provider implementation using vLLM API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct", 
                 api_key: Optional[str] = None, timeout: float = 60.0):
        """
        Initialize the vLLM provider.
        
        Args:
            base_url: Base URL for the vLLM API
            model: Model name to use (full model ID)
            api_key: API key for authorization
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
        # Create a session for connection pooling
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.debug(f"Authorization header set for vLLM provider")
        else:
            logger.debug(f"No API key provided for vLLM provider")
            
        # Define API endpoints
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
        self.completions_endpoint = f"{self.base_url}/v1/completions"
        self.embedding_endpoint = f"{self.base_url}/v1/embeddings"
        
        logger.info(f"Initialized VLLMProvider with model {model} at {base_url}")
        
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
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, stream: bool = False, **kwargs) -> str:
        """
        Generate text using vLLM API.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters (ignored in vLLM)
            
        Returns:
            Generated text from the LLM
        """
        # Handle Ollama-specific parameters gracefully
        if 'num_ctx' in kwargs:
            logger.debug("num_ctx parameter provided but not used by vLLM provider")

        # Use chat completions API for better results with chat models
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        response = self.session.post(
            self.chat_endpoint,
            json=payload,
            headers=self.headers,
            timeout=self.timeout
        )

        try:
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}, Response: {response.text}")
            raise

        result = response.json()

        # Extract the generated text from the response
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return ""
    
    def generate_structured_output(
        self,
        prompt: str,
        json_schema: Union[Dict[str, Any], Type[BaseModel]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.0,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a structured output using vLLM with guided JSON.
        
        Args:
            prompt: The main prompt for the model.
            json_schema: Either a dictionary representing the JSON schema or a Pydantic BaseModel class.
            max_tokens: Maximum number of tokens for the response.
            temperature: Sampling temperature for the generation (0 recommended for structured outputs).
            **kwargs: Additional provider-specific parameters (ignored in vLLM)
        
        Returns:
            A dictionary parsed from the JSON output of the model, or None if parsing fails.
        """
        # Handle Ollama-specific parameters gracefully
        if 'num_ctx' in kwargs:
            logger.debug("num_ctx parameter provided but not used by vLLM provider")
            
        # Process schema if it's a Pydantic model
        schema_dict = json_schema
        if HAS_PYDANTIC and hasattr(json_schema, 'model_json_schema'):
            schema_dict = json_schema.model_json_schema()
        elif HAS_PYDANTIC and isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            schema_dict = json_schema.model_json_schema()
            
        try:
            # Use guided_json for structured output
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "guided_json": schema_dict  # vLLM's structured output feature
            }
            
            response = self.session.post(
                self.chat_endpoint, 
                json=payload, 
                headers=self.headers,
                timeout=self.timeout
            )
            
            try:
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}, Response: {response.text}")
                raise
                
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                text_response = result["choices"][0]["message"]["content"]
                
                # Try to parse the response as JSON
                try:
                    return json.loads(text_response)
                except json.JSONDecodeError:
                    # Fallback: Look for JSON between triple backticks
                    if "```json" in text_response and "```" in text_response.split("```json", 1)[1]:
                        json_part = text_response.split("```json", 1)[1].split("```", 1)[0].strip()
                        return json.loads(json_part)
                    else:
                        logger.error(f"Failed to parse JSON response: {text_response}")
                        return None
            return None

        except requests.RequestException:
            raise  # transport and HTTP errors reach the caller, which retries or fails the run
        except Exception as e:
            logger.error(f"Error generating structured output with vLLM: {e}")
            return None

    def get_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings using vLLM API.
        
        Args:
            text: Either a single string or a list of strings
            
        Returns:
            For single input: a single embedding as List[float]
            For multiple inputs: multiple embeddings as List[List[float]]
        """
        try:
            is_single = isinstance(text, str)
            input_texts = [text] if is_single else text
            
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
            
            if "data" in result and len(result["data"]) > 0:
                embeddings = [item["embedding"] for item in result["data"]]
                return embeddings[0] if is_single else embeddings
            return [] if is_single else [[]]
                
        except Exception as e:
            logger.error(f"Error generating embedding with vLLM: {e}")
            return [] if isinstance(text, str) else [[]]
    
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
            
            return {
                "name": self.model,
                "provider": "vllm",
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
