from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseVectorStore(ABC):
    """
    Abstract base class for vector store operations.
    Implement this class for each vector database provider you want to support.
    """
    
    @abstractmethod
    def setup_collection(self, collection_name: str, vector_size: int) -> bool:
        """
        Ensure a collection exists with the specified parameters.
        
        Args:
            collection_name: Name of the collection to create/verify
            vector_size: Size of vectors in the collection
            
        Returns:
            True if setup was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_document(self, collection_name: str, document_id: str, vector: List[float], payload: Dict[str, Any]) -> bool:
        """
        Add a document with its vector embedding to the store.
        
        Args:
            collection_name: Name of the collection
            document_id: Unique ID for the document
            vector: Vector embedding of the document
            payload: Additional metadata for the document
            
        Returns:
            True if document was added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def search(self, collection_name: str, query_vector: List[float], limit: int, filter_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the store.
        
        Args:
            collection_name: Name of the collection to search
            query_vector: Vector to search for
            limit: Maximum number of results to return
            filter_params: Additional filtering parameters
            
        Returns:
            List of results with payloads and similarity scores
        """
        pass
    
    @abstractmethod
    def retrieve_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.
        
        Args:
            collection_name: Name of the collection
            document_id: ID of the document to retrieve
            
        Returns:
            Document with payload if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document by its ID.
        
        Args:
            collection_name: Name of the collection
            document_id: ID of the document to delete
            
        Returns:
            True if document was deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection information
        """
        pass
