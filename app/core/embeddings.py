import os
import sys
from app.utils.env_loader import load_env_from_file

# Ensure project root is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.config.config import config
from app.model_host import get_llm_provider
from app.core.logger import logger

# Load environment variables from specific .env file
load_env_from_file()


def get_embedding(text: str, model_name: str = None) -> list:
    """
    Generates an embedding for the given text using the configured LLM provider.

    :param text: The text to embed
    :param model_name: Optional model name override
    :return: A list representing the vector embedding
    """
    try:
        # Get the LLM provider (default from config/env)
        provider = get_llm_provider()
        
        # If model_name is provided, create a new provider instance with that model
        if model_name:
            provider = get_llm_provider(model=model_name)
            
        # Get embedding from the provider
        return provider.get_embedding(text)
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []

def generate_text(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """
    Generates text based on a prompt using the configured LLM provider.

    :param prompt: The prompt to send to the LLM
    :param max_tokens: Maximum number of tokens to generate
    :param temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
    :return: Generated text from the LLM
    """
    try:
        # Get the LLM provider (default from config/env)
        provider = get_llm_provider()
        
        # Generate text using the provider
        return provider.generate_text(prompt, max_tokens, temperature)
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        return ""

if __name__ == "__main__":
    # Test embedding output
    sample_text = "This is a test report on employee performance."
    print(get_embedding(sample_text))

    # Test text generation
    prompt = "Write a brief summary of an employee who has been performing well."
    print(generate_text(prompt))
    
    # Test embedding dimension
    sample_text = "Test text"
    sample_embedding = get_embedding(sample_text)
    print(f"Embedding dimension: {len(sample_embedding)}")