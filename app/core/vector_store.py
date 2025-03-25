import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from uuid import uuid4  
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import Filter, FieldCondition, MatchValue, NamedVector
from sqlalchemy.sql import text
import json 
import uuid

# Ensure project root is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.core.embeddings import get_embedding
from app.core.logger import logger
from app.config.config import config
from app.database import get_database
from app.models.base import schema_name

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


def chunk_text(text, max_chunk_size=500):
    """
    Splits the text into smaller chunks of a specified size.

    :param text: The text to chunk.
    :param max_chunk_size: Maximum size of each chunk (in characters).
    :return: A list of text chunks.
    """
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



def store_qdrant_mapping(qdrant_id, report_id, chunk_index, metadata):
    """
    Stores the Qdrant mapping in the structured database.

    :param qdrant_id: Qdrant document ID.
    :param report_id: ID of the report in the structured database (UUID).
    :param chunk_index: Index of the chunk.
    :param metadata: Additional metadata (e.g., employee_id, report_date).
    """
    required_fields = ["employee_id", "report_date"]
    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        logger.error(f"Metadata is missing required fields: {', '.join(missing_fields)}")
        return

    if not isinstance(metadata, dict):
        logger.error(f"Metadata must be a dictionary. Received: {type(metadata)}")
        return

    db_instance = get_database()
    with db_instance.create_session() as session:
        try:
            # Log the schema and database being used
            logger.debug(f"Using schema: {schema_name}")
            logger.debug(f"Database URL: {db_instance.engine.url}")

            # Convert metadata dictionary to JSON string
            metadata_json = json.dumps(metadata)

            session.execute(
                text("""
                INSERT INTO employee_reports.qdrant_mappings (qdrant_id, report_id, chunk_index, meta_data)
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
        except Exception as e:
            logger.error(f"Failed to store Qdrant mapping for Qdrant ID {qdrant_id}: {e}")

def add_report_to_qdrant(report_id, employee_id, report_date, report_text):
    """
    Adds a report to Qdrant by chunking the text and storing embeddings in a batch.

    :param report_id: ID of the report in the structured database (automatically generated by SQLAlchemy).
    :param employee_id: ID of the employee who submitted the report.
    :param report_date: Date of the report.
    :param report_text: Full text of the report.
    """
    try:
        # Log the received report_id for debugging
        logger.info(f"Adding report to Qdrant with ID: {report_id}")
        
        # The report_id parameter is already the automatically generated UUID from the Report model
        # The Report model has: report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        
        chunks = chunk_text(report_text)
        points = []  # Collect all points for batch upsert

        for chunk_index, chunk in enumerate(chunks):
            # Generate a NEW unique UUID for each Qdrant document (different from report_id)
            qdrant_id = str(uuid4())  # Generate a unique Qdrant ID
            embedding = get_embedding(chunk)  # Generate embedding for the chunk

            # Create a PointStruct for the chunk
            points.append(
                PointStruct(
                    id=qdrant_id,
                    vector=embedding,
                    payload={
                        "report_id": str(report_id),  # Convert UUID to string for Qdrant
                        "employee_id": employee_id,
                        "chunk_index": chunk_index,
                        "report_date": report_date,
                        "text": chunk
                    }
                )
            )

            # Store mapping in the structured database - links Qdrant ID to the report_id
            store_qdrant_mapping(qdrant_id, report_id, chunk_index, {
                "employee_id": employee_id,
                "report_date": report_date
            })

        # Perform batch upsert
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points  # Batch upsert all points
        )

        logger.info(f"Report added to Qdrant with {len(chunks)} chunks in a batch.")

    except Exception as e:
        logger.error(f"Failed to add report {report_id} to Qdrant: {e}")

    

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

        # Extract results and sort by report_date (most recent first)
        sorted_results = sorted(
            points, 
            key=lambda hit: datetime.strptime(hit.payload.get("report_date", "1900-01-01"), "%Y-%m-%d"), 
            reverse=True  # Sort descending (most recent first)
        )

        logger.info(f"Search completed for query: {query}")
        return [hit.payload for hit in sorted_results]

    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def check_collection_size():
    try:
        collection_info = qdrant.get_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' contains {collection_info.points_count} points.")
    except Exception as e:
        print(f"Error retrieving collection size: {e}")

def get_report_chunks(report_id):
    """
    Retrieve all chunks for a given report ID from Qdrant.

    :param report_id: ID of the report in the structured database (UUID).
    :return: List of text chunks.
    """
    try:
        # Ensure report_id is a UUID
        if isinstance(report_id, str):
            try:
                report_id = uuid.UUID(report_id)
            except ValueError:
                logger.error(f"Invalid UUID format for report_id: {report_id}")
                return []

        db_instance = get_database()
        with db_instance.create_session() as session:
            # Get Qdrant IDs for the report
            result = session.execute(
                text("""
                SELECT qdrant_id, chunk_index
                FROM employee_reports.qdrant_mappings
                WHERE report_id = :report_id
                ORDER BY chunk_index
                """),
                {"report_id": report_id}
            ).fetchall()

            # Retrieve chunks from Qdrant
            chunks = []
            for row in result:
                qdrant_id = row[0]
                response = qdrant.retrieve(collection_name=COLLECTION_NAME, ids=[str(qdrant_id)])
                if response:
                    chunks.append(response[0].payload["text"])

            logger.info(f"Retrieved {len(chunks)} chunks for report ID {report_id}.")
            return chunks
    except Exception as e:
        logger.error(f"Failed to retrieve chunks for report ID {report_id}: {e}")
        return []
    
def check_qdrant_connection():
    """
    Checks if the Qdrant server is reachable.
    """
    try:
        response = qdrant.get_collections()
        logger.info(f"Qdrant server is reachable. Collections: {[c.name for c in response.collections]}")
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant server: {e}")

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
