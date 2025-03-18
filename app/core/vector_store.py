import os
import sys
import logging
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from uuid import uuid4  # For generating unique document IDs
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import Filter, FieldCondition, MatchValue, NamedVector

# Ensure project root is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.core.embeddings import get_embedding
from app.core.logger import logger
from app.config.config import config

# Load environment variables from .env file
load_dotenv()

# Load Qdrant settings dynamically from .env with fallback to config.yaml
QDRANT_HOST = os.getenv("QDRANT_HOST").strip()  # On-premise server host
QDRANT_PORT = os.getenv("QDRANT_PORT").strip()  # On-premise server port
QDRANT_STORAGE_PATH = os.getenv("QDRANT_STORAGE_PATH", config["vector_db"].get("storage_path", "./qdrant_data"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", config["vector_db"].get("collection_name", "employee_reports"))

# Decide between embedded or on-premise server
if QDRANT_HOST and QDRANT_PORT.isdigit():
    qdrant = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))  # On-premise mode
    logger.info(f"Using on-premise Qdrant server at {QDRANT_HOST}:{QDRANT_PORT}")
else:
    qdrant = QdrantClient(path=QDRANT_STORAGE_PATH)  # Local embedded mode
    logger.info("Using local embedded Qdrant storage.")

def get_embedding_size():
    """Dynamically determine the embedding size from Ollama."""
    sample_text = "Test text"
    sample_embedding = get_embedding(sample_text)
    return len(sample_embedding)


# Ensure collection exists
def setup_qdrant_collection():
    """Ensure the collection exists with correct settings."""
    try:
        embedding_size = get_embedding_size()  # Get dynamic size
        collections = qdrant.get_collections()
        if COLLECTION_NAME not in [c.name for c in collections.collections]:
            qdrant.create_collection(
                COLLECTION_NAME,
                vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE)  
            )
            logging.info(f"Collection '{COLLECTION_NAME}' created with vector size {embedding_size}.")
    except Exception as e:
        logging.error(f"Error checking/creating collection: {e}")


def add_to_vector_store(doc_id: str, text: str, employee_id: int):
    """
    Adds a document to the vector store with its embedding.
    
    :param doc_id: Unique identifier for the document
    :param text: The document content
    :param employee_id: ID of the employee the document belongs to
    """
    try:
        embedding = get_embedding(text)
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=doc_id or str(uuid4()),  # Generate ID if not provided
                    vector=embedding,
                    payload={"text": text, "employee_id": employee_id}  # Metadata
                )
            ]
        )
        logger.info(f"Successfully added document {doc_id} for employee {employee_id}.")
    except Exception as e:
        logger.error(f"Failed to add {doc_id}: {e}")

def search_reports(query: str, employee_id: int, top_k: int = 5):
    """
    Searches for the most relevant reports based on the query.

    :param query: The search query
    :param employee_id: Employee ID to filter results
    :param top_k: Number of top results to return
    :return: List of relevant report texts
    """
    try:
        query_embedding = get_embedding(query)

        # Construct the filter using Qdrant's Filter and FieldCondition
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="employee_id",
                    match=MatchValue(value=employee_id)
                )
            ]
        )

        response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,   # Pass the vector directly as a list of floats
            limit=top_k,
            query_filter=query_filter  # Apply the filter
        )

        points = response.points

        logger.info(f"Search completed for query: {query}")
        return [hit.payload for hit in points]
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def check_collection_size():
    try:
        collection_info = qdrant.get_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' contains {collection_info.points_count} points.")
    except Exception as e:
        print(f"Error retrieving collection size: {e}")

if __name__ == "__main__":

    setup_qdrant_collection()

    # Test storing & searching
    test_documents = [
        (1, "Employee John Doe exceeded targets this quarter.", 3211),
        (2, "Employee Jane Doe achieved 95% customer satisfaction.", 3212),
        (3, "Employee John Doe led a successful project launch.", 3211)
    ]
    
    for doc_id, text, emp_id in test_documents:
        add_to_vector_store(doc_id, text, emp_id)
    
    check_collection_size()  # Check if documents were added

    search_results = search_reports("John Doe", 3211)
    print("Search Results:")
    for result in search_results:
        print(result)
