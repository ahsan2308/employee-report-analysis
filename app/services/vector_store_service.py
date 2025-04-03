from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4
import json
import numpy as np

# Use the proper import from model_host folder
from app.services.embedding_service import get_embedding

from app.core.logger import logger
from app.vector_store import get_vector_store
from app.database import get_database
from app.models.base import schema_name
from app.core.config_provider import get_config_provider
from sqlalchemy.sql import text

# Get configuration
config = get_config_provider()
COLLECTION_NAME = config.get("collection_name", "employee_reports", section="vector_db")


def chunk_text(text: str, max_chunk_size: int = 500) -> List[str]:
    """
    Splits the text into smaller chunks of a specified size.
    """
    if not text or not isinstance(text, str):
        return []

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

def get_embedding_size() -> int:
    """Dynamically determine the embedding size."""
    sample_text = "Test text"
    sample_embedding = get_embedding(sample_text)
    return len(sample_embedding)

def setup_collection() -> bool:
    """Ensure the vector collection exists with correct settings."""
    try:
        vector_store = get_vector_store()
        embedding_size = get_embedding_size()
        return vector_store.setup_collection(COLLECTION_NAME, embedding_size)
    except Exception as e:
        logger.error(f"Error setting up vector collection: {e}")
        return False

def store_mapping(document_id: str, report_id: str, chunk_index: int) -> bool:
    """Stores the vector store mapping in the database."""

    db_instance = get_database()
    with db_instance.create_session() as session:
        try:
            session.execute(
                text(f"""
                INSERT INTO {schema_name}.qdrant_mappings (qdrant_id, report_id, chunk_index)
                VALUES (:qdrant_id, :report_id, :chunk_index)
                """),
                {
                    "qdrant_id": document_id,
                    "report_id": report_id,
                    "chunk_index": chunk_index,  
                }
            )
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store mapping: {e}")
            return False

def add_report_to_vector_store(report_id: str, employee_id: int, report_date: str, report_text: str) -> bool:
    """
    Adds a report to the vector store by chunking text and storing embeddings.
    """
    try:
        logger.info(f"Adding report to vector store: {report_id}")
        vector_store = get_vector_store()
        
        # Ensure collection exists
        if not setup_collection():
            logger.error("Failed to setup vector collection")
            return False
            
        # Chunk the text
        chunks = chunk_text(report_text)
        
        for chunk_index, chunk in enumerate(chunks):
            # Generate unique ID for each vector document
            document_id = str(uuid4())
            
            # Generate embedding
            embedding = get_embedding(chunk)
            
            # Create payload
            payload = {
                "report_id": str(report_id),
                "employee_id": employee_id,
                "chunk_index": chunk_index,
                "report_date": report_date,
                "text": chunk
            }
            
            # Add to vector store
            success = vector_store.add_document(
                collection_name=COLLECTION_NAME,
                document_id=document_id,
                vector=embedding,
                payload=payload
            )
            
            if success:
                # Store mapping in database
                store_mapping(
                    document_id, 
                    str(report_id), 
                    chunk_index 
                )
        
        logger.info(f"Report added with {len(chunks)} chunks")
        return True
    except Exception as e:
        logger.error(f"Failed to add report to vector store: {e}")
        return False

def search_reports(query: str, employee_id: int, top_k: int = 5, score_threshold: float = 0.3, bypass_threshold: bool = False) -> List[Dict[str, Any]]:
    """
    Searches for the most relevant reports based on the query.
    
    Args:
        query: The search query text
        employee_id: ID of the employee to filter reports for
        top_k: Maximum number of results to return
        score_threshold: Minimum similarity score (0-1) for results
        bypass_threshold: If True, ignores the score threshold (for debugging)
    """
    try:
        vector_store = get_vector_store()
        
        # Add debug logging for embedding generation
        logger.debug(f"Generating embedding for query: '{query}'")
        query_embedding = get_embedding(query)
        
        # Check if embedding is valid
        if not query_embedding or len(query_embedding) == 0:
            logger.error("Generated embedding is empty or None")
            return []
            
        # Log embedding details for debugging
        embedding_sample = str(query_embedding[:3]) + "..." + str(query_embedding[-3:])
        embedding_stats = {
            "length": len(query_embedding),
            "type": type(query_embedding).__name__,
            "min": np.min(query_embedding) if isinstance(query_embedding, (list, np.ndarray)) else "N/A",
            "max": np.max(query_embedding) if isinstance(query_embedding, (list, np.ndarray)) else "N/A",
            "has_zeros_only": all(x == 0 for x in query_embedding) if isinstance(query_embedding, (list, np.ndarray)) else "N/A"
        }
        logger.debug(f"Embedding generated - sample: {embedding_sample}, stats: {embedding_stats}")
        
        # Construct the filter for employee ID
        filter_params = {
            "must": [
                {
                    "key": "employee_id",
                    "match": {"value": employee_id}
                }
            ]
        }
        
        logger.debug(f"Searching for: '{query}' with employee_id={employee_id}, filter={filter_params}")
        
        # Search for similar vectors
        results = vector_store.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k,
            filter_params=filter_params
        )
        
        logger.debug(f"Raw search returned {len(results)} results before filtering")
        
        # Log all scores to check threshold
        if results:
            scores = [f"{r.get('score', 0):.4f}" for r in results]
            logger.debug(f"Result scores: {', '.join(scores)}")
        
        # Filter by score threshold (unless bypassed)
        if bypass_threshold:
            logger.debug("Score threshold check bypassed for debugging")
            filtered_results = results
        else:
            filtered_results = [r for r in results if r.get("score", 0) >= score_threshold]
            logger.debug(f"After threshold filtering: {len(filtered_results)} results remain")
        
        try:
            sorted_results = sorted(
                filtered_results,
                key=lambda hit: datetime.strptime(hit.get("report_date", "1900-01-01"), "%Y-%m-%d"),
                reverse=True
            )
            logger.info(f"Search for '{query}' found {len(sorted_results)} results")
        except Exception as date_err:
            logger.error(f"Error sorting results by date: {date_err}")
            sorted_results = filtered_results  # Fall back to unsorted results if sorting fails
                
        # Log the first result if available for debugging
        if sorted_results:
            logger.debug(f"Top result: {sorted_results[0]}")
        else:
            logger.debug("No results found after processing")
            
        return sorted_results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_report_chunks(report_id: str) -> List[str]:
    """
    Retrieve all chunks for a given report ID.
    """
    try:
        vector_store = get_vector_store()
        db_instance = get_database()
        
        with db_instance.create_session() as session:
            # Get document IDs from mappings table
            result = session.execute(
                text(f"""
                SELECT qdrant_id, chunk_index
                FROM {schema_name}.qdrant_mappings
                WHERE report_id = :report_id
                ORDER BY chunk_index
                """),
                {"report_id": report_id}
            ).fetchall()
            
            # Retrieve chunks from vector store
            chunks = []
            for row in result:
                document_id = str(row[0])
                document = vector_store.retrieve_document(COLLECTION_NAME, document_id)
                if document and "text" in document:
                    chunks.append(document["text"])
            
            logger.info(f"Retrieved {len(chunks)} chunks for report {report_id}")
            return chunks
    except Exception as e:
        logger.error(f"Failed to retrieve chunks: {e}")
        return []
