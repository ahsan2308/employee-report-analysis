import ollama

def get_embedding(text: str, model_name: str = "llama3.1:8b") -> list:
    """
    Generates an embedding for the given text using Ollama's model.
    
    :param text: The text to embed
    :param model_name: The Ollama embedding model to use
    :return: A list representing the vector embedding
    """
    response = ollama.embeddings(model=model_name, prompt=text)
    return response["embedding"]

if __name__ == "__main__":
    sample_text = "This is a test report on employee performance."
    print(get_embedding(sample_text))  # Test embedding output