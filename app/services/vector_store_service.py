from typing import List, Dict, Any, Optional
from datetime import datetime, date
from uuid import NAMESPACE_URL, uuid5
import json
import numpy as np
import time

# Use the proper import from model_host folder
from app.services.embedding_service import get_embedding, get_embeddings

from app.core.logger import logger
from app.integrations.vector_store import get_vector_store
from app.integrations.vector_store import payload_fields as fields
from app.db.database import get_database
from app.repositories import vector_mappings

from app.core.settings import COLLECTION_NAME

from app.core.settings import (
    VECTOR_BATCH_MAX_RETRIES, VECTOR_BATCH_RETRY_BACKOFF_FACTOR, VECTOR_BATCH_RETRY_INITIAL_WAIT_MS,
    VECTOR_UPSERT_BATCH_SIZE,
)
from app.domain.periods import parse_period_date

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

def _probe_embedding_size() -> Optional[int]:
    """Embedding size from a live probe, or None when the embedding service did not answer."""
    try:
        sample_embedding = get_embedding("Test text")
    except Exception as e:
        logger.error(f"Error detecting embedding size: {str(e)}")
        return None
    if not sample_embedding:
        logger.error("Empty embedding returned when detecting embedding size")
        return None
    return len(sample_embedding)

def setup_collection() -> bool:
    """Ensure the vector collection exists with correct settings.

    Never deletes an existing collection. A dimension mismatch, or an embedding
    service that cannot be reached, is reported and returns False so callers stop
    instead of losing stored vectors. Recreating the collection is an operator decision.
    """
    try:
        vector_store = get_vector_store()

        collection_info = {}
        try:
            collection_info = vector_store.get_collection_info(COLLECTION_NAME) or {}
        except Exception as e:
            logger.info(f"Collection '{COLLECTION_NAME}' not found or error checking: {e}")
        current_dimension = collection_info.get('dimension')

        embedding_size = _probe_embedding_size()
        if embedding_size is None:
            logger.error(f"Embedding service unavailable; leaving collection '{COLLECTION_NAME}' untouched")
            return False

        if not current_dimension:
            # Missing, or Qdrant could not describe it (the provider returns {} on any error).
            # The provider's setup_collection only creates the collection when it is missing.
            logger.info(f"Ensuring collection '{COLLECTION_NAME}' exists with dimension {embedding_size}")
            return vector_store.setup_collection(COLLECTION_NAME, embedding_size)

        logger.info(f"Found existing collection '{COLLECTION_NAME}' with dimension {current_dimension}")
        if current_dimension != embedding_size:
            logger.error(
                f"Collection '{COLLECTION_NAME}' has dimension {current_dimension} but the embedding model "
                f"produces {embedding_size}. Leaving it untouched; recreate it deliberately if the model changed."
            )
            return False

        return True  # Collection exists with correct dimensions

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
        vector_mappings.insert_mapping(session, document_id, report_id, chunk_index)
        
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
            vector_mappings.insert_mappings(session, insert_values)
        
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

# Point IDs are derived from (report, chunk), so re-adding a report overwrites its points
_REPORT_CHUNK_NAMESPACE = uuid5(NAMESPACE_URL, "employee-report-analysis/report-chunk")


def report_chunk_point_id(report_id, chunk_index: int) -> str:
    """The vector store point ID of one chunk of a report."""
    return str(uuid5(_REPORT_CHUNK_NAMESPACE, f"{report_id}:{chunk_index}"))


def _remove_stale_report_vectors(vector_store, report_ids, keep_ids, session=None) -> bool:
    """Delete the points and mappings of these reports that are not in keep_ids.

    They are left by an earlier, longer version of a report, or by imports from
    before point IDs were derived from (report, chunk).
    """
    close_session = session is None
    if close_session:
        session = get_database().create_session()
    try:
        stale = [point_id for point_id in vector_mappings.point_ids_for_reports(session, report_ids)
                 if point_id not in keep_ids]
        if not stale:
            return True
        if not vector_store.delete_document(collection_name=COLLECTION_NAME, points_selector=stale):
            logger.error(f"Failed to delete {len(stale)} stale vectors")
            return False
        vector_mappings.delete_mappings(session, stale)
        if close_session:
            session.commit()
        logger.info(f"Removed {len(stale)} stale vectors for {len(report_ids)} reports")
        return True
    except Exception as e:
        logger.error(f"Failed to remove stale vectors: {e}")
        if close_session:
            session.rollback()
        return False
    finally:
        if close_session:
            session.close()


def _report_date_timestamp(report_date) -> float:
    """The timestamp the date filters compare, for a date, datetime or date string."""
    if isinstance(report_date, datetime):
        report_date = report_date.date()
    elif isinstance(report_date, str):
        report_date = parse_period_date(report_date)  # raises ValueError for an unreadable date
    elif not isinstance(report_date, date):
        raise ValueError(f"Unreadable report date: {report_date!r}")
    return datetime.combine(report_date, datetime.min.time()).timestamp()


def _build_points(reports: List[Dict[str, Any]]):
    """
    Chunk and embed reports.

    Returns (points, mappings): one vector store point and one database mapping
    per chunk. A report without text is skipped. Returns None when the embedding
    provider fails; raises ValueError for an unreadable report date.
    """
    chunks = []
    chunk_reports = []  # (report, its date timestamp, chunk index) of each chunk
    for report in reports:
        report_chunks = chunk_text(report["report_text"])
        if not report_chunks:
            logger.warning(f"No chunks were generated from report text for report {report['report_id']}")
            continue
        # Read the date before embedding anything, so an unreadable one costs no embedding calls
        date_ts = _report_date_timestamp(report["report_date"])
        chunks.extend(report_chunks)
        chunk_reports.extend((report, date_ts, index) for index in range(len(report_chunks)))

    if not chunks:
        return [], []

    start_time = time.time()
    logger.info(f"Generating embeddings for {len(chunks)} chunks in batch")
    embeddings = get_embeddings(chunks)
    logger.info(f"Batch embedding generation completed in {time.time() - start_time:.2f}s")
    if not embeddings or len(embeddings) != len(chunks):
        logger.error(f"Failed to generate embeddings: expected {len(chunks)}, got {len(embeddings) if embeddings else 0}")
        return None

    points, mappings = [], []
    for chunk, embedding, (report, date_ts, chunk_index) in zip(chunks, embeddings, chunk_reports):
        report_id = str(report["report_id"])
        # Point ID derived from (report, chunk), so a re-import overwrites it
        document_id = report_chunk_point_id(report_id, chunk_index)
        points.append({
            "document_id": document_id,
            "vector": embedding,
            "payload": {
                fields.REPORT_ID: report_id,
                fields.EMPLOYEE_ID: report["employee_id"],
                fields.CHUNK_INDEX: chunk_index,
                fields.REPORT_DATE: report["report_date"],  # Keep original date for display
                fields.REPORT_DATE_TS: date_ts,  # For date filters
                fields.TEXT: chunk,
            },
        })
        mappings.append({"document_id": document_id, "report_id": report_id, "chunk_index": chunk_index})
    return points, mappings


def _upsert_with_retry(vector_store, points: List[Dict[str, Any]]) -> bool:
    """Upsert points in batches, retrying a failed batch with a growing wait between attempts."""
    attempts = max(1, VECTOR_BATCH_MAX_RETRIES)
    for i in range(0, len(points), VECTOR_UPSERT_BATCH_SIZE):
        batch = points[i:i + VECTOR_UPSERT_BATCH_SIZE]
        wait_seconds = VECTOR_BATCH_RETRY_INITIAL_WAIT_MS / 1000
        for attempt in range(1, attempts + 1):
            if vector_store.add_documents_batch(collection_name=COLLECTION_NAME, points=batch):
                break
            if attempt == attempts:
                logger.error(f"Failed to add batch {i // VECTOR_UPSERT_BATCH_SIZE + 1} after {attempts} attempts")
                return False
            logger.warning(f"Batch insert failed, attempt {attempt}/{attempts}; retrying in {wait_seconds:.1f}s")
            time.sleep(wait_seconds)
            wait_seconds *= VECTOR_BATCH_RETRY_BACKOFF_FACTOR
    return True


def add_report_to_vector_store(report_id=None, employee_id=None, report_date=None, report_text=None, reports=None, session=None) -> bool:
    """
    Add reports to the vector store and record their chunk mappings.

    Args:
        report_id, employee_id, report_date, report_text: one report
        reports: or a list of report dicts with those four keys
        session: Optional SQLAlchemy session for the mapping writes

    A report without text is skipped. Returns True when every report with text
    was added, False otherwise (including an unreadable report date).
    """
    if reports is None:
        reports = [{"report_id": report_id, "employee_id": employee_id,
                    "report_date": report_date, "report_text": report_text}]
    try:
        logger.info(f"Adding {len(reports)} report(s) to vector store")
        vector_store = get_vector_store()
        with vector_store:
            if not setup_collection():
                logger.error("Failed to setup vector collection")
                return False

            built = _build_points(reports)
            if built is None:
                return False
            points, mappings = built
            if not points:
                logger.warning("No chunks were generated from any reports")
                return True  # Not a failure, just nothing to do

            if not _upsert_with_retry(vector_store, points):
                return False
            if not store_mappings_batch(mappings, session):
                logger.error("Failed to store vector mappings in database")
                return False
            if not _remove_stale_report_vectors(
                vector_store, {m["report_id"] for m in mappings}, {m["document_id"] for m in mappings}, session
            ):
                return False

            logger.info(f"Successfully added {len(reports)} report(s) with {len(points)} vectors")
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
                        "key": fields.EMPLOYEE_ID,
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
                        "key": fields.REPORT_DATE_TS,
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
                search_params_dict["group_by"] = fields.REPORT_ID  # String field name, not a dict
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
                    key=lambda hit: datetime.strptime(hit.get(fields.REPORT_DATE, "1900-01-01"), "%Y-%m-%d"),
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
                result = vector_mappings.report_chunk_points(session, report_id)
                
                # Retrieve chunks from vector store
                chunks = []
                for row in result:
                    document_id = str(row[0])
                    document = vector_store.retrieve_document(COLLECTION_NAME, document_id)
                    if document and fields.TEXT in document:
                        chunks.append(document[fields.TEXT])
                
                logger.info(f"Retrieved {len(chunks)} chunks for report {report_id}")
                return chunks
    except Exception as e:
        logger.error(f"Failed to retrieve chunks: {e}")
        return []
