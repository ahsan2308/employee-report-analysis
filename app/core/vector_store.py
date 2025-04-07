import os
import sys
import logging
from datetime import datetime
import warnings
from app.utils.env_loader import load_env_from_file
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from uuid import uuid4  
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import Filter, FieldCondition, MatchValue, NamedVector
from sqlalchemy.sql import text
import json 

# Ensure project root is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.core.embeddings import get_embedding
from app.core.logger import logger
from app.vector_store import get_vector_store
from app.database import get_database
from app.models.base import schema_name
from app.core.config_provider import get_config_provider

# Load environment variables from specific .env file
load_env_from_file()

# Get configuration using the new config provider
config = get_config_provider()

# Use config provider for consistency
QDRANT_HOST = os.getenv("QDRANT_HOST", "").strip() if os.getenv("QDRANT_HOST") else ""
QDRANT_PORT = os.getenv("QDRANT_PORT", "").strip() if os.getenv("QDRANT_PORT") else ""
QDRANT_STORAGE_PATH = os.getenv("QDRANT_STORAGE_PATH", config.get("storage_path", "./qdrant_data", section="vector_db"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", config.get("collection_name", "employee_reports", section="vector_db"))

# Get the vector store provider using the new factory function
qdrant = get_vector_store()

# Show deprecation warning for this module
warnings.warn(
    "app.core.vector_store is deprecated in favor of app.vector_store and app.services.vector_store_service",
    DeprecationWarning, 
    stacklevel=2
)

def get_embedding_size():
    """Dynamically determine the embedding size from Ollama."""
    warnings.warn("Use app.services.vector_store_service instead", DeprecationWarning, stacklevel=2)
    sample_text = "Test text"
    sample_embedding = get_embedding(sample_text)
    return len(sample_embedding)


def chunk_text(text, max_chunk_size=500):
    """
    Splits the text into smaller chunks of a specified size.

    :param text: The text to chunk.
    :param max_chunk_size: Maximum size of each chunk (in characters).
    :return: A list of text chunks.
    """
    warnings.warn("Use app.services.vector_store_service.chunk_text instead", DeprecationWarning, stacklevel=2)
    if not text or not isinstance(text, str):
        return []  # Return an empty list if the input is invalid

    chunks = []
    while len(text) > max_chunk_size:
        # Find the last period within the chunk size to avoid splitting sentences
        split_index = text[:max_chunk_size].rfind(".")
        if split_index == -1:  # If no period is found, split at max_chunk_size
            split_index = max_chunk_size
        chunks.append(text[:split_index + 1].strip())
        text = text[split_index + 1:].strip()
    if text:  # Add the remaining text as the last chunk
        chunks.append(text)
    return chunks


# Ensure collection exists
def setup_qdrant_collection():
    """Ensure the collection exists with correct settings."""
    warnings.warn("Use app.services.vector_store_service.setup_collection instead", DeprecationWarning, stacklevel=2)
    try:
        embedding_size = get_embedding_size()  # Get dynamic size
        return qdrant.setup_collection(COLLECTION_NAME, embedding_size)
    except Exception as e:
        logging.error(f"Error checking/creating collection: {e}")
        return False


def store_qdrant_mapping(qdrant_id, report_id, chunk_index, metadata):
    """
    Stores the Qdrant mapping in the structured database.

    :param qdrant_id: Qdrant document ID.
    :param report_id: ID of the report in the structured database (UUID).
    :param chunk_index: Index of the chunk.
    :param metadata: Additional metadata (e.g., employee_id, report_date).
    """
    warnings.warn("Use app.services.vector_store_service.store_mapping instead", DeprecationWarning, stacklevel=2)
    required_fields = ["employee_id", "report_date"]
    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        logger.error(f"Metadata is missing required fields: {', '.join(missing_fields)}")
        return False

    if not isinstance(metadata, dict):
        logger.error(f"Metadata must be a dictionary. Received: {type(metadata)}")
        return False

    db_instance = get_database()
    with db_instance.create_session() as session:
        try:
            # Log the schema and database being used
            logger.debug(f"Using schema: {schema_name}")
            logger.debug(f"Database URL: {db_instance.engine.url}")

            # Convert metadata dictionary to JSON string
            metadata_json = json.dumps(metadata)

            session.execute(
                text(f"""
                INSERT INTO {schema_name}.qdrant_mappings (qdrant_id, report_id, chunk_index, meta_data)
                VALUES (:qdrant_id, :report_id, :chunk_index, :metadata)
                """),
                {
                    "qdrant_id": qdrant_id,
                    "report_id": report_id,
                    "chunk_index": chunk_index,
                    "metadata": metadata_json  
                }
            )
            session.commit()
            logger.info(f"Successfully stored Qdrant mapping for Qdrant ID {qdrant_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to store Qdrant mapping for Qdrant ID {qdrant_id}: {e}")
            return False

def add_report_to_qdrant(report_id, employee_id, report_date, report_text):
    """
    Adds a report to Qdrant by chunking the text and storing embeddings in a batch.

    :param report_id: ID of the report in the structured database (automatically generated by SQLAlchemy).
    :param employee_id: ID of the employee who submitted the report.
    :param report_date: Date of the report.
    :param report_text: Full text of the report.
    """
    warnings.warn("Use app.services.vector_store_service.add_report_to_vector_store instead", DeprecationWarning, stacklevel=2)
    try:
        # Log the received report_id for debugging
        logger.info(f"Adding report to Qdrant with ID: {report_id}")
        
        chunks = chunk_text(report_text)
        
        for chunk_index, chunk in enumerate(chunks):
            # Generate a NEW unique UUID for each Qdrant document (different from report_id)
            qdrant_id = str(uuid4())  # Generate a unique Qdrant ID
            embedding = get_embedding(chunk)  # Generate embedding for the chunk

            # Add to vector store using the provider interface
            qdrant.add_document(
                collection_name=COLLECTION_NAME,
                document_id=qdrant_id,
                vector=embedding,
                payload={
                    "report_id": str(report_id),  # Convert UUID to string for Qdrant
                    "employee_id": employee_id,
                    "chunk_index": chunk_index,
                    "report_date": report_date,
                    "text": chunk
                }
            )

            # Store mapping in the structured database - links Qdrant ID to the report_id
            store_qdrant_mapping(qdrant_id, report_id, chunk_index, {
                "employee_id": employee_id,
                "report_date": report_date
            })
        
        logger.info(f"Report added to Qdrant with {len(chunks)} chunks.")
        return True
    except Exception as e:
        logger.error(f"Failed to add report {report_id} to Qdrant: {e}")
        return False


def search_reports(query: str, employee_id: int, top_k: int = 5, score_threshold: float = 0.3):
    """
    Searches for the most relevant reports based on the query.

    :param query: The search query
    :param employee_id: Employee ID to filter results
    :param top_k: Number of top results to return
    :param score_threshold: Minimum similarity score (0 to 1) to include a result
    :return: List of relevant report texts
    """
    warnings.warn("Use app.services.vector_store_service.search_reports instead", DeprecationWarning, stacklevel=2)
    try:
        query_embedding = get_embedding(query)

        # Construct filter parameters for the provider interface
        filter_params = {
            "must": [
                {
                    "key": "employee_id",
                    "match": {"value": employee_id}
                }
            ]
        }

        # Search with scores using the provider interface
        logger.debug(f"Searching with query: '{query}' for employee: {employee_id}")
        response = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k,
            filter_params=filter_params
        )

        # Log raw scores for debugging
        logger.debug(f"Raw search results: {len(response)} items")

        # Filter out results with low similarity scores
        filtered_results = [r for r in response if r.get("score", 0) >= score_threshold]

        # Sort by date (most recent first)
        sorted_results = sorted(
            filtered_results, 
            key=lambda hit: datetime.strptime(hit.get("report_date", "1900-01-01"), "%Y-%m-%d"), 
            reverse=True
        )

        logger.info(f"Search completed for query '{query}', found {len(sorted_results)} relevant results")
        return sorted_results

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def check_collection_size():
    warnings.warn("Use app.vector_store methods directly", DeprecationWarning, stacklevel=2)
    try:
        collection_info = qdrant.get_collection_info(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' contains {collection_info.get('points_count', 0)} points.")
    except Exception as e:
        print(f"Error retrieving collection size: {e}")

def get_report_chunks(report_id):
    """
    Retrieve all chunks for a given report ID from Qdrant.

    :param report_id: ID of the report in the structured database (UUID).
    :return: List of text chunks.
    """
    warnings.warn("Use app.services.vector_store_service.get_report_chunks instead", DeprecationWarning, stacklevel=2)
    try:
        db_instance = get_database()
        with db_instance.create_session() as session:
            # Get Qdrant IDs for the report
            result = session.execute(
                text(f"""
                SELECT qdrant_id, chunk_index
                FROM {schema_name}.qdrant_mappings
                WHERE report_id = :report_id
                ORDER BY chunk_index
                """),
                {"report_id": report_id}
            ).fetchall()

            # Retrieve chunks from Qdrant
            chunks = []
            for row in result:
                qdrant_id = str(row[0])
                document = qdrant.retrieve_document(COLLECTION_NAME, qdrant_id)
                if document and "text" in document:
                    chunks.append(document["text"])

            logger.info(f"Retrieved {len(chunks)} chunks for report ID {report_id}.")
            return chunks
    except Exception as e:
        logger.error(f"Failed to retrieve chunks for report ID {report_id}: {e}")
        return []
    
def check_qdrant_connection():
    """
    Checks if the Qdrant server is reachable.
    """
    warnings.warn("Use app.vector_store methods directly", DeprecationWarning, stacklevel=2)
    try:
        # The collection_info will fail if connection issues exist
        qdrant.get_collection_info(COLLECTION_NAME)
        logger.info(f"Qdrant server is reachable.")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant server: {e}")
        return False

if __name__ == "__main__":
    # Step 1: Setup Qdrant Collection
    setup_qdrant_collection()

    # Step 2: Test storing & searching
    test_documents = [
        (1, "Employee John Doe exceeded targets this quarter.", 3211, "2025-03-15"),
        (2, "Employee Jane Doe achieved 95% customer satisfaction.", 3212, "2025-03-16"),
        (3, "Employee John Doe led a successful project launch.", 3211, "2025-03-17")
    ]

    for doc_id, textt, emp_id, report_date in test_documents:
        add_report_to_qdrant(doc_id, emp_id, report_date, textt)

    # Step 3: Check collection size
    check_collection_size()

    # Step 4: Test search functionality
    search_results = search_reports("John Doe", 3211)
    logger.info("Search Results (Sorted by Date):")
    for result in search_results:
        logger.info(result)
