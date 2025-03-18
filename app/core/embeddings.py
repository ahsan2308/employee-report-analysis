import ollama
import os
from dotenv import load_dotenv
import sys


# Ensure project root is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.config.config import config  # Import the dynamically loaded config

# Load environment variables from .env
load_dotenv()

# Load values, prioritizing .env over config.yaml
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", config["llm"]["api_url"])
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", config["llm"]["model"])

def get_embedding(text: str, model_name: str = OLLAMA_MODEL) -> list:
    """
    Generates an embedding for the given text using Ollama's model.

    :param text: The text to embed
    :param model_name: The Ollama embedding model to use (default from config)
    :return: A list representing the vector embedding
    """
    try:
        response = ollama.embeddings(model=model_name, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

if __name__ == "__main__":
    sample_text = "This is a test report on employee performance."
    print(get_embedding(sample_text))  # Test embedding output

    sample_text = "Test text"
    sample_embedding = get_embedding(sample_text)
    print(len(sample_embedding))  # Prints the dimension of the vector