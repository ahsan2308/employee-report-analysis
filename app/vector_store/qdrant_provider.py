from typing import List, Dict, Any, Optional
import os
import threading
import psutil
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from qdrant_client.models import FieldCondition, MatchValue

from app.base.base_vector_store import BaseVectorStore
from app.core.logger import logger

class QdrantProvider(BaseVectorStore):
    """
    Vector store implementation using Qdrant with improved connection management.
    """
    
    # Class variables for thread safety
    _instance = None
    _lock = threading.RLock()  # Reentrant lock for thread safety
    
    # Connection state tracking
    _conn_state = {
        "initialized": False,
        "connected": False,
        "client": None,
        "host": None,
        "port": None,
        "path": None
    }
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern with proper thread safety."""
        with cls._lock:
            if cls._instance is None:
                logger.info("Creating QdrantProvider singleton instance")
                cls._instance = super(QdrantProvider, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, 
                 host: Optional[str] = None, 
                 port: Optional[int] = None, 
                 path: Optional[str] = None):
        """
        Initialize the Qdrant provider with connection parameters.
        
        Args:
            host: Qdrant server host (None for embedded mode)
            port: Qdrant server port (None for embedded mode)
            path: Path to local storage (for embedded mode)
        """
        with self._lock:
            # Store connection parameters
            self._conn_state["host"] = host
            self._conn_state["port"] = port
            self._conn_state["path"] = path
            
            # Don't initialize client here - will be done in connect()
            self.client = None
    
    def connect(self) -> bool:
        """
        Explicitly connect to Qdrant.
        Returns True if connection was successful, False otherwise.
        """
        with self._lock:
            # If already connected, return True
            if self._conn_state["connected"] and self._conn_state["client"] is not None:
                logger.info("Already connected to Qdrant")
                self.client = self._conn_state["client"]
                return True
            
            # Connection parameters
            host = self._conn_state["host"]
            port = self._conn_state["port"]
            path = self._conn_state["path"]
            
            # Log diagnostic information
            current_process = psutil.Process(os.getpid())
            current_thread = threading.current_thread()
            logger.info(f"Connecting to Qdrant from process {os.getpid()} ({current_process.name()})")
            logger.info(f"Thread ID: {current_thread.ident}, Thread name: {current_thread.name}")
            
            try:
                # For server mode - need host and port
                if host and port and isinstance(port, int):
                    logger.info(f"Connecting to Qdrant server at {host}:{port}")
                    client = QdrantClient(host=host, port=port)
                    logger.info(f"Connected to Qdrant server at {host}:{port}")
                
                # For embedded mode - need path
                elif path:
                    # Check if path exists and log details
                    full_path = os.path.abspath(path)
                    logger.info(f"Connecting to local Qdrant at {full_path}")
                    logger.info(f"Path exists: {os.path.exists(full_path)}")
                    
                    # Skip lengthy process scanning as it's slow and not always helpful
                    logger.info("Connecting to local embedded Qdrant...")
                    
                    # Create the client with the storage path
                    client = QdrantClient(path=path)
                    logger.info(f"Connected to local Qdrant at {full_path}")
                else:
                    raise ValueError("Either host+port or path must be provided")
                
                # Store client and update connection state
                self._conn_state["client"] = client
                self._conn_state["connected"] = True
                self._conn_state["initialized"] = True
                self.client = client
                
                # Test connection with a simple API call
                _ = client.get_collections()
                logger.info("Qdrant connection verified successfully")
                return True
                
            except Exception as e:
                self._conn_state["client"] = None
                self._conn_state["connected"] = False
                logger.error(f"Failed to connect to Qdrant: {str(e)}")
                
                # Provide better diagnostics for common errors
                if "already accessed by another instance" in str(e):
                    logger.error("This error indicates another process has locked the Qdrant storage folder.")
                    logger.error("Consider running in server mode or ensuring all previous connections are closed.")
                
                # Re-raise the exception
                raise
    
    def disconnect(self) -> bool:
        """
        Explicitly disconnect from Qdrant.
        Returns True if disconnection was successful, False otherwise.
        """
        with self._lock:
            if not self._conn_state["connected"] or self._conn_state["client"] is None:
                logger.info("Not connected to Qdrant - nothing to disconnect")
                return True
            
            try:
                # Close the client
                self._conn_state["client"].close()
                logger.info("Closed Qdrant connection")
                
                # Update connection state
                self._conn_state["client"] = None
                self._conn_state["connected"] = False
                self.client = None
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from Qdrant: {str(e)}")
                return False
    
    def _ensure_connected(self):
        """Ensure connection is established before operations."""
        if not self._conn_state["connected"] or self._conn_state["client"] is None:
            self.connect()
    
    # Context manager support for automated cleanup
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.disconnect()
        return False  # Re-raise any exceptions
        
    # Existing methods updated to use connection management
    
    def setup_collection(self, collection_name: str, vector_size: int) -> bool:
        """Ensure a collection exists with the specified parameters."""
        try:
            self._ensure_connected()
            collections = self.client.get_collections()
            if collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                logger.info(f"Collection '{collection_name}' created with vector size {vector_size}")
            return True
        except Exception as e:
            logger.error(f"Error setting up collection '{collection_name}': {e}")
            return False

    def add_document(self, collection_name: str, document_id: str, vector: List[float], payload: Dict[str, Any]) -> bool:
        """Add a document with its vector embedding to the store."""
        try:
            self._ensure_connected()
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=document_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Error adding document to collection '{collection_name}': {e}")
            return False

    def add_documents_batch(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        """
        Add multiple documents with their vector embeddings to the store in a single operation.
        
        Args:
            collection_name: Name of the collection
            points: List of point dictionaries, each containing:
                - document_id: Unique ID for the document
                - vector: Vector embedding of the document
                - payload: Additional metadata for the document
                
        Returns:
            True if all documents were added successfully, False otherwise
        """
        if not points:
            logger.warning("No points provided to add_documents_batch")
            return True  # Nothing to do
            
        try:
            self._ensure_connected()
            
            # Convert dictionary format to PointStruct objects
            point_structs = [
                PointStruct(
                    id=point["document_id"],
                    vector=point["vector"],
                    payload=point["payload"]
                ) for point in points
            ]
            
            # Perform batch upsert
            self.client.upsert(
                collection_name=collection_name,
                points=point_structs
            )
            
            logger.info(f"Successfully added batch of {len(points)} documents to collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error adding documents batch to collection '{collection_name}': {e}")
            return False

    def search(self, collection_name: str, query_vector: List[float], limit: int, filter_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in the store."""
        try:
            self._ensure_connected()
            query_filter = None
            if filter_params:
                if "must" in filter_params:
                    must_conditions = []
                    for condition in filter_params["must"]:
                        if "key" in condition and "match" in condition:
                            must_conditions.append(
                                FieldCondition(
                                    key=condition["key"],
                                    match=MatchValue(value=condition["match"]["value"])
                                )
                            )
                    query_filter = Filter(must=must_conditions)
            
            response = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
            
            results = []
            for point in response:
                result = point.payload.copy()
                result["score"] = point.score
                result["id"] = point.id
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error searching collection '{collection_name}': {e}")
            return []
    
    def retrieve_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        try:
            self._ensure_connected()
            response = self.client.retrieve(
                collection_name=collection_name,
                ids=[document_id]
            )
            
            if response and len(response) > 0:
                result = response[0].payload.copy()
                result["id"] = response[0].id
                return result
            return None
        except Exception as e:
            logger.error(f"Error retrieving document '{document_id}': {e}")
            return None
    
    def delete_document(self, collection_name: str, document_id: str = None, points_selector = None) -> bool:
        """
        Delete a document or documents by ID or filter.
        
        Args:
            collection_name: Name of the collection
            document_id: Single document ID (legacy parameter)
            points_selector: Either a list of IDs or a Filter object
        """
        try:
            self._ensure_connected()
            if document_id is not None and document_id != "":
                points_selector = [document_id]
            
            if points_selector is None:
                raise ValueError("Either document_id or points_selector must be provided")
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=points_selector
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False
    
    def delete(self, collection_name: str, points_selector: List[str]) -> bool:
        """
        Compatibility method for legacy code that calls delete directly.
        Delegates to delete_document method.
        """
        logger.warning("The 'delete' method is deprecated. Please use 'delete_document' instead.")
        if isinstance(points_selector, list) and len(points_selector) > 0:
            return self.delete_document(collection_name, points_selector[0])
        else:
            logger.error("Invalid points_selector format for delete method")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection."""
        try:
            self._ensure_connected()
            response = self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "vectors_count": response.vectors_count,
                "points_count": response.points_count,
                "dimension": response.config.params.vectors.size,
                "distance": response.config.params.vectors.distance
            }
        except Exception as e:
            logger.error(f"Error getting info for collection '{collection_name}': {e}")
            return {}

    def verify_deletion(self, collection_name: str, filter_params: dict) -> bool:
        """
        Verify that documents matching the filter criteria have been deleted.
        
        Args:
            collection_name: Name of the collection
            filter_params: Dictionary with filter parameters
            
        Returns:
            bool: True if no documents match the filter criteria (deletion successful)
        """
        try:
            self._ensure_connected()
            query_filter = None
            if filter_params and "must" in filter_params:
                must_conditions = []
                for condition in filter_params["must"]:
                    if "key" in condition and "match" in condition:
                        must_conditions.append(
                            FieldCondition(
                                key=condition["key"],
                                match=MatchValue(value=condition["match"]["value"])
                            )
                        )
                query_filter = Filter(must=must_conditions)
            
            count_result = self.client.count(
                collection_name=collection_name,
                count_filter=query_filter
            )
            
            return count_result.count == 0
        except Exception as e:
            logger.error(f"Error verifying deletion in collection '{collection_name}': {e}")
            return False
