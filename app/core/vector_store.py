import chromadb
from chromadb.config import Settings
import os
from dotenv import load_dotenv
from app.core.embeddings import get_embedding
from app.core.logger import logger 
from app.config.config import config

# Configure settings with telemetry disabled
settings = Settings(anonymized_telemetry=False)

# Load environment variables from .env file
load_dotenv()

# Load values with fallback to config.yaml
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", config["vector_db"]["path"])
COLLECTION_NAME = os.getenv("COLLECTION_NAME", config["vector_db"]["collection_name"])

# Validate environment variables (fallback if empty)
if not VECTOR_DB_PATH.strip():
    VECTOR_DB_PATH = config["vector_db"]["path"]

if not COLLECTION_NAME.strip():
    COLLECTION_NAME = config["vector_db"]["collection_name"]

# Initialize ChromaDB dynamically
chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH, settings=settings)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

def add_to_vector_store(doc_id: str, text: str):
    """
    Adds a document to the vector store with its embedding.
    
    :param doc_id: Unique identifier for the document
    :param text: The document content
    """
    try:
        embedding = get_embedding(text)
        collection.add(ids=[doc_id], embeddings=[embedding], documents=[text])
        logger.info(f"Successfully added document {doc_id} to vector store.")
    except Exception as e:
        logger.error(f"Failed to add {doc_id}: {e}")

def search_reports(query: str, top_k: int = 5):
    """
    Searches for the most relevant reports based on the query.
    
    :param query: The search query
    :param top_k: Number of top results to return
    :return: List of relevant report texts
    """
    try:
        query_embedding = get_embedding(query)
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        logger.info(f"Search completed for query: {query}")
        return results["documents"]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

if __name__ == "__main__":
    # Test storing & searching
    add_to_vector_store("report_1", "Employee John Doe exceeded targets this quarter.")
    print(search_reports("high-performing employee"))
