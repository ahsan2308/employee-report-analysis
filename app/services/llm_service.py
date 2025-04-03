"""
High-level LLM service for text generation and inference operations.
"""
from typing import Dict, List, Any, Optional, Type, Union
import time
import json
import re

from app.model_host import get_llm_provider
from app.core.logger import logger
from app.core.config_provider import get_config_provider
from app.models.structured_models import EmployeeAnalysis
from app.prompts.structured_prompts import StructuredPrompts

config = get_config_provider()
DEFAULT_MODEL = config.get("model", "llama3.1:8b", section="llm")

class LLMService:
    """Service for interacting with LLM models for text generation and inference."""
    
    def __init__(self, model: str = None):
        """
        Initialize LLM service with specified model.
        
        Args:
            model: Model name to use (overrides config default)
        """
        self.model = model or DEFAULT_MODEL
        logger.debug(f"Initializing LLMService with model: {self.model}")
        self.provider = get_llm_provider(model=self.model)
        self.retry_delay = 1.0
        self.max_retries = 3

    def generate_text(self, prompt: str, max_tokens: int = 1000,
                    temperature: float = 0.7, retries: int = None) -> str:
        """
        Generate text response for the given prompt.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            retries: Number of retries on failure (default from config)
            
        Returns:
            Generated text response
        """
        attempts = 0
        max_attempts = retries or self.max_retries
        current_delay = self.retry_delay  # Create local copy of delay
        
        while attempts < max_attempts:
            try:
                response = self.provider.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response
            except Exception as e:
                attempts += 1
                logger.warning(f"LLM generation attempt {attempts} failed: {e}")
                
                if attempts >= max_attempts:
                    logger.error(f"LLM generation failed after {max_attempts} attempts")
                    return ""
                
                logger.debug(f"Waiting {current_delay}s before retry")
                time.sleep(current_delay)
                current_delay *= 2  

    def extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract valid JSON from text that may contain additional content.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON as dictionary or empty dict if parsing fails
        """
        # Try to find JSON between triple backticks with optional "json" language identifier
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from matched code block: {json_str[:100]}...")
        
        # Try to find content between curly braces with proper JSON formatting
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from curly braces match: {json_str[:100]}...")
        
        # As a last resort, try parsing the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error(f"Failed to parse any JSON from response: {text[:100]}...")
            return {}

    def get_structured_response(
        self, 
        prompt: str, 
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2, 
        max_tokens: int = 1000,
        pydantic_model: Optional[Type] = None
    ) -> Dict[str, Any]:
        """
        Generate structured response in specific JSON format.
        
        Args:
            prompt: The input prompt
            response_format: Optional dictionary describing expected response structure.
                Can be a simple template or a JSON schema with 'type', 'properties', etc.
                Will be ignored if pydantic_model is provided.
            temperature: Sampling temperature (lower for more deterministic outputs)
            max_tokens: Maximum tokens to generate
            pydantic_model: Optional Pydantic model class to use (prioritized over response_format)
            
        Returns:
            Structured response as dictionary
            
        Raises:
            ValueError: If neither response_format nor pydantic_model is provided
        """
        # If Pydantic model is provided, derive schema from it
        if pydantic_model is not None:
            try:
                if hasattr(pydantic_model, 'model_json_schema'):
                    response_format = pydantic_model.model_json_schema()
                else:
                    # Fallback for older Pydantic versions
                    response_format = pydantic_model.schema()
                    
                logger.debug(f"Using schema from Pydantic model: {pydantic_model.__name__}")
            except Exception as e:
                logger.error(f"Failed to derive schema from Pydantic model: {e}")
                if response_format is None:
                    raise ValueError(f"Could not derive schema from provided Pydantic model: {e}")
                logger.warning(f"Falling back to provided response_format due to Pydantic schema error")
        
        # If we still don't have a response format, raise an error
        if response_format is None:
            raise ValueError("Either response_format or pydantic_model must be provided")
            
        # Check if response_format is already a proper JSON schema
        is_schema = isinstance(response_format, dict) and any(key in response_format for key in ["type", "properties"])
        
        # Convert simple format template to JSON schema if necessary
        if not is_schema:
            json_schema = {
                "type": "object",
                "properties": {}
            }
            
            for key, value in response_format.items():
                if isinstance(value, list):
                    json_schema["properties"][key] = {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                elif isinstance(value, str):
                    json_schema["properties"][key] = {"type": "string"}
                elif isinstance(value, (int, float)):
                    json_schema["properties"][key] = {"type": "number"}
                elif isinstance(value, bool):
                    json_schema["properties"][key] = {"type": "boolean"}
                else:
                    json_schema["properties"][key] = {"type": "object"}
                    
            example_format = response_format
        else:
            json_schema = response_format
            
            example_format = {}
            if "properties" in json_schema:
                for prop, details in json_schema["properties"].items():
                    if details.get("type") == "array":
                        example_format[prop] = ["example item"]
                    elif details.get("type") == "number":
                        example_format[prop] = 30
                    elif details.get("type") == "boolean":
                        example_format[prop] = True
                    elif details.get("type") == "object" and "properties" in details:
                        example_format[prop] = {k: "example" for k in details["properties"].keys()}
                    else:
                        example_format[prop] = "example value"
        
        # Use a lower temperature for structured outputs
        structured_temp = min(temperature, 0.2)  # Cap at 0.2 for structured outputs
        
        # Try using native structured output if available
        if hasattr(self.provider, "generate_structured_output"):
            try:
                logger.debug(f"Attempting to use native structured output with model {self.model}")
                # Always use pydantic_model directly if it's provided
                schema_arg = pydantic_model if pydantic_model else json_schema
                result = self.provider.generate_structured_output(
                    prompt=prompt,
                    json_schema=schema_arg,
                    temperature=structured_temp,
                    max_tokens=max_tokens
                )
                if result is not None:
                    logger.debug(f"Received native structured output: {result}")
                    return result
                logger.debug("Native structured output returned None, falling back to text generation")
            except Exception as e:
                logger.warning(f"Native structured output generation failed: {e}. Falling back to text generation.")
        
        # Fall back to the text-based approach
        format_instructions = ""
        if is_schema:
            format_instructions = StructuredPrompts.format_schema_prompt(json_schema, example_format)
        else:
            format_instructions = StructuredPrompts.format_simple_prompt(example_format)
            
        full_prompt = StructuredPrompts.combine_prompt(prompt, format_instructions)
        
        try:
            logger.debug("Generating structured response using text approach")
            response = self.generate_text(full_prompt, temperature=temperature, max_tokens=max_tokens)
            logger.debug(f"Raw response from LLM: {response[:200]}...")
            
            result = self.extract_json_from_text(response)
            logger.debug(f"Extracted JSON: {result}")
            
            return result
                
        except Exception as e:
            logger.error(f"Failed to get structured response: {e}")
            return {}

    def analyze_report(
        self, 
        report_text: str, 
        similar_reports: List[str] = None,
        use_custom_format: bool = False,
        custom_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze an employee report.
        
        Args:
            report_text: The report text to analyze
            similar_reports: List of similar previous reports for context
            use_custom_format: If True, use custom_format instead of the Pydantic model
            custom_format: Optional custom response format to use instead of Pydantic model
            
        Returns:
            Analysis results
        """
        # Generate the task-specific prompt using the prompt template
        prompt = StructuredPrompts.employee_analysis_prompt(report_text, similar_reports)
        
        try:
            # Decide whether to use the custom format or the Pydantic model
            if use_custom_format:
                if custom_format is None:
                    # Provide a default format if none is specified
                    custom_format = {
                        "achievements": [{"description": "achievement", "impact": "impact"}],
                        "challenges": [{"description": "challenge", "severity": "medium"}],
                        "sentiment": "positive/negative/neutral",
                        "topics": ["topic1", "topic2"],
                        "action_items": ["action1", "action2"],
                        "risk_level": "low/medium/high",
                        "risk_explanation": "explanation"
                    }
                
                return self.get_structured_response(
                    prompt=prompt,
                    response_format=custom_format,
                    temperature=0
                )
            else:
                # Default behavior: use the EmployeeAnalysis Pydantic model
                return self.get_structured_response(
                    prompt=prompt,
                    pydantic_model=EmployeeAnalysis,
                    temperature=0
                )
        except Exception as e:
            logger.error(f"Error analyzing report: {e}")
            return {"error": str(e), "status": "failed"}


# Convenience function for quick access
def get_llm_service(model: str = None) -> LLMService:
    """Get an instance of the LLM service with the specified model."""
    return LLMService(model)