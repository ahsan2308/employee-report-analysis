from typing import List, Dict, Any, Optional
import os
import psutil
import threading
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from qdrant_client.models import FieldCondition, MatchValue

from app.base.base_vector_store import BaseVectorStore
from app.core.logger import logger

class QdrantProvider(BaseVectorStore):
    """
    Vector store implementation using Qdrant.
    """
    
    # Class variables to implement singleton pattern
    _instance = None
    _initialized = False
    _instances = 0
    _client = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            logger.info("Creating first QdrantProvider instance (singleton)")
            cls._instance = super(QdrantProvider, cls).__new__(cls)
        else:
            logger.info("Returning existing QdrantProvider singleton instance")
        return cls._instance
    
    def __init__(self, 
                 host: Optional[str] = None, 
                 port: Optional[int] = None, 
                 path: Optional[str] = None):
        """
        Initialize the Qdrant provider.
        
        Args:
            host: Qdrant server host (None for embedded mode)
            port: Qdrant server port (None for embedded mode)
            path: Path to local storage (for embedded mode)
        """
        # Skip initialization if already done
        if QdrantProvider._initialized:
            logger.info("Skipping initialization of QdrantProvider, already initialized")
            return
            
        # Log diagnostic information
        QdrantProvider._instances += 1
        current_process = psutil.Process(os.getpid())
        current_thread = threading.current_thread()
        
        logger.info(f"Initializing QdrantProvider instance #{QdrantProvider._instances}")
        logger.info(f"Process ID: {os.getpid()}, Process name: {current_process.name()}")
        logger.info(f"Thread ID: {current_thread.ident}, Thread name: {current_thread.name}")
        
        if path:
            # Log if the storage path exists and is locked
            full_path = os.path.abspath(path)
            logger.info(f"Storage path: {full_path}")
            logger.info(f"Storage path exists: {os.path.exists(full_path)}")
            
            # Print details about other processes that might be using this folder
            logger.info("Looking for processes that might be accessing Qdrant storage...")
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = " ".join(process.info['cmdline'] or [])
                    if path in cmdline and process.info['pid'] != os.getpid():
                        logger.info(f"Process {process.info['pid']} ({process.info['name']}) might be accessing the storage: {cmdline[:100]}...")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        # Initialize client with appropriate settings
        if host and port and isinstance(port, int):
            QdrantProvider._client = QdrantClient(host=host, port=port)
            logger.info(f"Using on-premise Qdrant server at {host}:{port}")
        elif path:
            try:
                QdrantProvider._client = QdrantClient(path=path)
                logger.info(f"Using local embedded Qdrant storage at {path}")
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant client: {e}")
                # Try to give more diagnostic information
                if "already accessed by another instance" in str(e):
                    logger.error("This error suggests another process or thread is using the Qdrant storage.")
                    logger.error("Consider using server mode instead of embedded mode for concurrent access.")
                raise
        else:
            raise ValueError("Either host+port or path must be provided")
        
        self.client = QdrantProvider._client
        QdrantProvider._initialized = True
    
    def __del__(self):
        """Ensure proper cleanup when the object is garbage collected."""
        # Only close the client when the class variable is being deleted, not each instance
        if QdrantProvider._client is not None and QdrantProvider._instances <= 1:
            try:
                QdrantProvider._client.close()
                logger.info(f"Closed Qdrant client for singleton instance")
                QdrantProvider._client = None
                QdrantProvider._initialized = False
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")
        
        if QdrantProvider._instances > 0:
            QdrantProvider._instances -= 1

    def setup_collection(self, collection_name: str, vector_size: int) -> bool:
        """Ensure a collection exists with the specified parameters."""
        try:
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
    
    def search(self, collection_name: str, query_vector: List[float], limit: int, filter_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in the store."""
        try:
            # Convert dictionary filter to Qdrant Filter object
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
            
            # Convert to standardized format
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
            # If document_id is provided, use it
            if document_id is not None and document_id != "":
                points_selector = [document_id]
            
            # Validate points_selector
            if points_selector is None:
                raise ValueError("Either document_id or points_selector must be provided")
            
            # Delete the points
            self.client.delete(
                collection_name=collection_name,
                points_selector=points_selector
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False
    
    # Add a compatibility method that delegates to delete_document
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
            response = self.client.get_collection(collection_name)

            return {
                "name": collection_name,  # Qdrant does not return collection name, so we add it manually
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
            # Convert dictionary filter to Qdrant Filter object
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
            
            # We don't need an actual query vector for count operation
            # Using a simple count operation to see if any matching documents exist
            count_result = self.client.count(
                collection_name=collection_name,
                count_filter=query_filter
            )
            
            # If count is 0, deletion was successful
            return count_result.count == 0
        except Exception as e:
            logger.error(f"Error verifying deletion in collection '{collection_name}': {e}")
            return False
