from typing import List, Dict, Any, Optional
from datetime import datetime, date
from uuid import uuid4
import json
import numpy as np
import time

# Use the proper import from model_host folder
from app.services.embedding_service import get_embedding, get_embeddings

from app.core.logger import logger
from app.vector_store import get_vector_store
from app.database import get_database
from app.models.base import schema_name
from app.core.config_provider import get_config_provider
from sqlalchemy.sql import text

# Get configuration
config = get_config_provider()
COLLECTION_NAME = config.get("collection_name", "employee_reports", section="vector_db")

# Get batch processing configuration using the config provider pattern
VECTOR_BATCH_MODE = config.get("enabled", True, section="vector_db.batch_processing")
VECTOR_EMBEDDING_BATCH_SIZE = config.get("embedding_batch_size", 256, section="vector_db.batch_processing")
VECTOR_UPSERT_BATCH_SIZE = config.get("upsert_batch_size", 1000, section="vector_db.batch_processing")
VECTOR_BATCH_MAX_RETRIES = config.get("max_attempts", 3, section="vector_db.batch_processing.retry")

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
    try:
        sample_text = "Test text"
        sample_embedding = get_embedding(sample_text)
        
        # Add additional logging and validation
        if not sample_embedding or len(sample_embedding) == 0:
            logger.error("Empty embedding returned when detecting embedding size")
            # Default to 1024 for bge-m3 as fallback
            logger.warning("Falling back to default size 1024 for bge-m3")
            return 1024
            
        embedding_size = len(sample_embedding)
        logger.info(f"Detected embedding size: {embedding_size}")
        return embedding_size
    except Exception as e:
        logger.error(f"Error detecting embedding size: {str(e)}")
        # Default to 1024 for bge-m3 as fallback
        logger.warning("Error occurred, falling back to default size 1024 for bge-m3")
        return 1024

def setup_collection() -> bool:
    """Ensure the vector collection exists with correct settings."""
    try:
        vector_store = get_vector_store()
        
        # Check if collection already exists
        try:
            collection_info = vector_store.get_collection_info(COLLECTION_NAME)
            current_dimension = collection_info.get('dimension', 0)
            logger.info(f"Found existing collection '{COLLECTION_NAME}' with dimension {current_dimension}")
            
            # Get the expected dimension for current model
            embedding_size = get_embedding_size()
            
            # If dimensions don't match, delete and recreate
            if current_dimension != embedding_size:
                logger.warning(f"Collection dimension mismatch: found {current_dimension}, expected {embedding_size}")
                logger.info(f"Recreating collection '{COLLECTION_NAME}' with correct dimension {embedding_size}")
                
                # Additional logging for debugging
                logger.debug(f"Current collection info: {collection_info}")
                
                # Delete the collection using the new method
                if not vector_store.delete_collection(COLLECTION_NAME):
                    logger.error(f"Failed to delete collection '{COLLECTION_NAME}'")
                    return False
                
                # Create new collection with correct dimensions
                logger.info(f"Creating new collection '{COLLECTION_NAME}' with dimension {embedding_size}")
                return vector_store.setup_collection(COLLECTION_NAME, embedding_size)
            
            return True  # Collection exists with correct dimensions
            
        except Exception as e:
            # Collection likely doesn't exist, create it
            logger.info(f"Collection '{COLLECTION_NAME}' not found or error checking: {e}")
            embedding_size = get_embedding_size()
            logger.info(f"Creating new collection '{COLLECTION_NAME}' with dimension {embedding_size}")
            return vector_store.setup_collection(COLLECTION_NAME, embedding_size)
            
    except Exception as e:
        logger.error(f"Error setting up vector collection: {e}")
        return False

def store_mapping(document_id: str, report_id: str, chunk_index: int, session=None) -> bool:
    """Stores the vector store mapping in the database."""

    db_instance = get_database()
    # Use provided session if available, otherwise create a new one
    close_session = False
    if session is None:
        session = db_instance.create_session()
        close_session = True  # Flag to close the session after use

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
        
        # Only commit if we created the session
        if close_session:
            session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to store mapping: {e}")
        if close_session:
            session.rollback()
        return False
    finally:
        # Only close if we created the session
        if close_session and session:
            session.close()

def store_mappings_batch(mappings: List[Dict], session=None) -> bool:
    """
    Store multiple vector store mappings in a single database transaction.
    
    Args:
        mappings: List of mapping dictionaries, each containing:
            - document_id: Unique vector store document ID
            - report_id: Report ID
            - chunk_index: Chunk index
        session: Optional SQLAlchemy session
    """
    db_instance = get_database()
    close_session = False
    if session is None:
        session = db_instance.create_session()
        close_session = True
    
    try:
        # Prepare for bulk insert
        insert_values = []
        for mapping in mappings:
            insert_values.append({
                "qdrant_id": mapping["document_id"],
                "report_id": mapping["report_id"],
                "chunk_index": mapping["chunk_index"]
            })
        
        # Execute bulk insert if we have any mappings
        if insert_values:
            session.execute(
                text(f"INSERT INTO {schema_name}.qdrant_mappings (qdrant_id, report_id, chunk_index) VALUES (:qdrant_id, :report_id, :chunk_index)"),
                insert_values
            )
        
        # Only commit if we created the session
        if close_session:
            session.commit()
            
        logger.info(f"Successfully stored {len(mappings)} mappings in batch")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store mappings batch: {e}")
        if close_session:
            session.rollback()
        return False
        
    finally:
        if close_session and session:
            session.close()

def add_report_to_vector_store(report_id=None, employee_id=None, report_date=None, report_text=None, reports=None, session=None) -> bool:
    """
    Adds a report or multiple reports to the vector store.
    
    Args:
        report_id: ID of the report (for single report mode)
        employee_id: Employee ID (for single report mode)
        report_date: Report date as string (for single report mode)
        report_text: Report text content (for single report mode)
        reports: List of report dictionaries for batch mode, each containing:
            - report_id: ID of the report
            - employee_id: Employee ID
            - report_date: Report date as string
            - report_text: Report text content
        session: Optional SQLAlchemy session to use for database operations
            
    Returns:
        True if all operations were successful, False otherwise
    """
    try:
        # Helper function to convert date to timestamp for Qdrant storage
        def date_to_timestamp(date_str):
            if isinstance(date_str, str):
                try:
                    # Convert ISO format string to timestamp
                    return datetime.strptime(date_str, "%Y-%m-%d").timestamp()
                except:
                    logger.warning(f"Could not parse date string: {date_str}, using current time")
                    return datetime.now().timestamp()
            elif isinstance(date_str, (datetime, date)):
                # Convert date/datetime object to timestamp
                return datetime.combine(date_str, datetime.min.time()).timestamp()
            else:
                logger.warning(f"Unknown date format: {date_str}, using current time")
                return datetime.now().timestamp()
            
        # Check if we're in batch mode
        if reports:
            logger.info(f"Adding {len(reports)} reports to vector store in batch")
            
            # Get vector store and use context manager for proper cleanup
            vector_store = get_vector_store()
            
            # Use context manager pattern for automatic cleanup
            with vector_store:
                # Ensure collection exists
                if not setup_collection():
                    logger.error("Failed to setup vector collection")
                    return False
                    
                # Pre-process all reports to generate chunks and embeddings
                all_points = []
                all_mappings = []
                all_chunks = []
                chunk_metadata = []  # Track which report/index each chunk belongs to
                
                # First, collect all chunks and their metadata
                for report_idx, report in enumerate(reports):
                    report_id = report["report_id"]
                    employee_id = report["employee_id"]
                    report_date = report["report_date"]
                    report_text = report["report_text"]
                    
                    # Chunk the text
                    chunks = chunk_text(report_text)
                    if not chunks:
                        logger.warning(f"No chunks were generated from report text for report {report_id}")
                        continue
                    
                    # Add chunks to the batch list
                    for chunk_idx, chunk in enumerate(chunks):
                        all_chunks.append(chunk)
                        chunk_metadata.append({
                            "report_idx": report_idx,
                            "report_id": report_id,
                            "employee_id": employee_id,
                            "chunk_idx": chunk_idx,
                            "report_date": report_date
                        })
                
                if not all_chunks:
                    logger.warning("No chunks were generated from any reports")
                    return True  # Not a failure, just nothing to do
                
                # Generate all embeddings in a single batch operation
                start_time = time.time()
                logger.info(f"Generating embeddings for {len(all_chunks)} chunks in batch")
                all_embeddings = get_embeddings(all_chunks)
                logger.info(f"Batch embedding generation completed in {time.time() - start_time:.2f}s")
                
                if not all_embeddings or len(all_embeddings) != len(all_chunks):
                    logger.error(f"Failed to generate embeddings: expected {len(all_chunks)}, got {len(all_embeddings) if all_embeddings else 0}")
                    return False
                
                # Create points and mappings using the generated embeddings
                for i, embedding in enumerate(all_embeddings):
                    chunk = all_chunks[i]
                    meta = chunk_metadata[i]
                    
                    # Generate unique ID for each vector document
                    document_id = str(uuid4())
                    
                    # Create payload - convert date to timestamp
                    payload = {
                        "report_id": str(meta["report_id"]),
                        "employee_id": meta["employee_id"],
                        "chunk_index": meta["chunk_idx"],
                        "report_date": meta["report_date"],  # Keep original date for display
                        "report_date_ts": date_to_timestamp(meta["report_date"]),  # Add timestamp for filtering
                        "text": chunk
                    }
                    
                    # Add to points batch
                    all_points.append({
                        "document_id": document_id,
                        "vector": embedding,
                        "payload": payload
                    })
                    
                    # Collect mapping for database
                    all_mappings.append({
                        "document_id": document_id,
                        "report_id": str(meta["report_id"]),
                        "chunk_index": meta["chunk_idx"]
                    })
                
                # Process in sub-batches if necessary
                if not all_points:
                    logger.warning("No points to add to vector store")
                    return True  # Not a failure, just nothing to do
                    
                # Process points in batches
                for i in range(0, len(all_points), VECTOR_UPSERT_BATCH_SIZE):
                    batch = all_points[i:i + VECTOR_UPSERT_BATCH_SIZE]
                    
                    # Try to add the batch with retries
                    success = False
                    retries = 0
                    
                    while not success and retries < VECTOR_BATCH_MAX_RETRIES:
                        success = vector_store.add_documents_batch(
                            collection_name=COLLECTION_NAME,
                            points=batch
                        )
                        
                        if not success:
                            retries += 1
                            logger.warning(f"Batch insert failed, retry {retries}/{VECTOR_BATCH_MAX_RETRIES}")
                    
                    if not success:
                        logger.error(f"Failed to add batch {i//VECTOR_UPSERT_BATCH_SIZE + 1} after {VECTOR_BATCH_MAX_RETRIES} retries")
                        return False
                
                # Store all mappings in database
                if not store_mappings_batch(all_mappings, session):
                    logger.error("Failed to store vector mappings in database")
                    return False
                    
                logger.info(f"Successfully added {len(reports)} reports with total {len(all_points)} vectors")
                return True
                
        else:
            # Original single-report mode
            logger.info(f"Adding report to vector store: {report_id}")
            
            # Get vector store and use context manager for proper cleanup
            vector_store = get_vector_store()
            
            # Use context manager pattern for automatic cleanup
            with vector_store:
                # Ensure collection exists
                if not setup_collection():
                    logger.error("Failed to setup vector collection")
                    return False
                    
                # Chunk the text
                chunks = chunk_text(report_text)
                if not chunks:
                    logger.warning("No chunks were generated from the report text")
                    return False
                    
                logger.info(f"Generated {len(chunks)} chunks from report text")
                
                # Batch process mode
                if VECTOR_BATCH_MODE:
                    # Prepare batches for processing
                    points = []
                    mappings = []
                    
                    # Generate all embeddings in a single batch operation
                    start_time = time.time()
                    logger.debug(f"Generating embeddings for {len(chunks)} chunks in batch")
                    chunk_embeddings = get_embeddings(chunks)
                    logger.debug(f"Batch embedding generation completed in {time.time() - start_time:.2f}s")
                    
                    if not chunk_embeddings or len(chunk_embeddings) != len(chunks):
                        logger.error(f"Failed to generate embeddings: expected {len(chunks)}, got {len(chunk_embeddings) if chunk_embeddings else 0}")
                        return False
                    
                    # Create points and mappings using the generated embeddings
                    for chunk_index, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                        # Generate unique ID for each vector document
                        document_id = str(uuid4())
                        
                        # Create payload with timestamp for filtering
                        payload = {
                            "report_id": str(report_id),
                            "employee_id": employee_id,
                            "chunk_index": chunk_index,
                            "report_date": report_date,  # Keep original date for display
                            "report_date_ts": date_to_timestamp(report_date),  # Add timestamp for filtering
                            "text": chunk
                        }
                        
                        # Add to points batch
                        points.append({
                            "document_id": document_id,
                            "vector": embedding,
                            "payload": payload
                        })
                        
                        # Collect mapping for database
                        mappings.append({
                            "document_id": document_id,
                            "report_id": str(report_id),
                            "chunk_index": chunk_index
                        })
                    
                    # Process in sub-batches if necessary
                    for i in range(0, len(points), VECTOR_UPSERT_BATCH_SIZE):
                        batch = points[i:i + VECTOR_UPSERT_BATCH_SIZE]
                        
                        # Try to add the batch with retries
                        success = False
                        retries = 0
                        
                        while not success and retries < VECTOR_BATCH_MAX_RETRIES:
                            success = vector_store.add_documents_batch(
                                collection_name=COLLECTION_NAME,
                                points=batch
                            )
                            
                            if not success:
                                retries += 1
                                logger.warning(f"Batch insert failed, retry {retries}/{VECTOR_BATCH_MAX_RETRIES}")
                        
                        if not success:
                            logger.error(f"Failed to add batch {i//VECTOR_UPSERT_BATCH_SIZE + 1} after {VECTOR_BATCH_MAX_RETRIES} retries")
                            return False
                    
                    # Store all mappings in one database operation
                    if not store_mappings_batch(mappings, session):
                        logger.error("Failed to store vector mappings in database")
                        return False
                    
                    logger.info(f"Successfully added report {report_id} with {len(chunks)} chunks in batch mode")
                    
                else:
                    # Legacy non-batch mode - process each chunk individually
                    mappings = []
                    
                    for chunk_index, chunk in enumerate(chunks):
                        # Generate unique ID for each vector document
                        document_id = str(uuid4())
                        
                        # Generate embedding
                        embedding = get_embedding(chunk)
                        
                        # Create payload with timestamp for filtering
                        payload = {
                            "report_id": str(report_id),
                            "employee_id": employee_id,
                            "chunk_index": chunk_index,
                            "report_date": report_date,  # Keep original date for display
                            "report_date_ts": date_to_timestamp(report_date),  # Add timestamp for filtering
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
                            # Collect mapping for batch insert
                            mappings.append({
                                "document_id": document_id,
                                "report_id": str(report_id),
                                "chunk_index": chunk_index
                            })
                        else:
                            logger.error(f"Failed to add chunk {chunk_index} to vector store")
                            return False
                    
                    # Store mappings in batch
                    store_mappings_batch(mappings, session)
                    
                    logger.info(f"Report added with {len(chunks)} chunks in single mode")
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to add report to vector store: {str(e)}")
        return False

def search_reports(query: str, employee_id: int, top_k: int = 5, score_threshold: float = 0.3, 
                   bypass_threshold: bool = False, group_by_report: bool = False,
                   cutoff_date: Optional[date] = None, search_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Searches for the most relevant reports based on the query.
    
    Args:
        query: The search query text
        employee_id: ID of the employee to filter reports for
        top_k: Maximum number of results to return
        score_threshold: Minimum similarity score (0-1) for results
        bypass_threshold: If True, ignores the score threshold (for debugging)
        group_by_report: If True, returns at most one chunk per unique report_id
        cutoff_date: If provided, only returns reports older than this date
        search_params: Optional search parameters (e.g., {"hnsw_ef": 128})
    """
    try:
        # Get vector store and use context manager pattern for proper cleanup
        vector_store = get_vector_store()
        
        # Use context manager pattern for automatic cleanup
        with vector_store:
            # Add debug logging for embedding generation
            logger.debug(f"Generating embedding for query: '{query}'")
            query_embedding = get_embedding(query, is_query=True)  # Set is_query=True for search queries
            
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
            
            # Add date filter if provided
            if cutoff_date:
                # Convert cutoff_date to timestamp for range filtering
                if isinstance(cutoff_date, date):
                    # Convert to datetime at midnight
                    cutoff_datetime = datetime.combine(cutoff_date, datetime.min.time())
                    cutoff_ts = cutoff_datetime.timestamp()
                elif isinstance(cutoff_date, datetime):
                    cutoff_ts = cutoff_date.timestamp()
                else:
                    logger.error(f"Unsupported cutoff_date type: {type(cutoff_date)}")
                    cutoff_ts = None
                
                logger.debug(f"DEBUG: Using cutoff date timestamp: {cutoff_ts} for {cutoff_date}")
                
                # Use timestamp field for filtering
                if cutoff_ts:
                    filter_params["must"].append({
                        "key": "report_date_ts",
                        "range": {"lt": cutoff_ts}
                    })
                
                # Also log the complete filter
                logger.info(f"DEBUG: Complete filter: {json.dumps(filter_params)}")
            
            logger.debug(f"Searching for: '{query}' with employee_id={employee_id}, filter={filter_params}")
            
            # Define search parameters
            search_params_dict = {
                "collection_name": COLLECTION_NAME,
                "query_vector": query_embedding,
                "limit": top_k,
                "filter_params": filter_params
            }
            
            # Add group_by parameter if enabled - corrected to match Qdrant API (v1.11.0+)
            if group_by_report:
                search_params_dict["group_by"] = "report_id"  # String field name, not a dict
                search_params_dict["group_size"] = 1  # Get only the top-scoring chunk per report
                logger.debug("Using group_by='report_id', group_size=1 to deduplicate results by report")
            
            # Add search parameters if provided
            if search_params:
                search_params_dict["search_params"] = search_params
                logger.debug(f"Using custom search parameters: {search_params}")
        
            # Search for similar vectors
            results = vector_store.search(**search_params_dict)
            
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
        # Get vector store and use context manager pattern for proper cleanup
        vector_store = get_vector_store()
        
        # Use context manager pattern for automatic cleanup
        with vector_store:
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
