from typing import Optional
from app.utils.env_loader import load_env_from_file

from app.integrations.vector_store.base import BaseVectorStore
from app.integrations.vector_store.qdrant import QdrantProvider
from app.core.logger import logger  # Import logger for proper debugging

# Load environment variables
load_env_from_file()


# Get Vector Store settings with priority: env vars > config file > defaults
from app.core.settings import VECTOR_STORE_HOST, VECTOR_STORE_MODE, VECTOR_STORE_PATH, VECTOR_STORE_PORT, VECTOR_STORE_TYPE

# Replace print with logger
logger.info(f"Vector Store Path: {VECTOR_STORE_PATH}")
logger.info(f"Vector Store Host: {VECTOR_STORE_HOST}")
logger.info(f"Vector Store Port: {VECTOR_STORE_PORT}")
logger.info(f"Vector Store Mode: {VECTOR_STORE_MODE}")

def get_vector_store(store_type: Optional[str] = None, **kwargs) -> BaseVectorStore:
    """
    Factory function to get a vector store provider instance.
    
    Args:
        store_type: Type of vector store ("qdrant", "pinecone", etc.)
        **kwargs: Additional arguments to pass to the provider constructor
    
    Returns:
        An instance of BaseVectorStore
    """
    # Use parameter, environment variable, or default
    if store_type is None:
        store_type = VECTOR_STORE_TYPE
    
    # Get mode from kwargs or environment
    mode = kwargs.pop("mode", VECTOR_STORE_MODE)
    logger.info(f"Creating vector store with type={store_type}, mode={mode}")
    
    if store_type.lower() == "qdrant":
        if mode.lower() == "local":
            # For local mode, only use path
            if "path" not in kwargs and VECTOR_STORE_PATH:
                kwargs["path"] = VECTOR_STORE_PATH
            # Remove server connection params if present
            kwargs.pop("host", None)
            kwargs.pop("port", None)
            
            # Ensure path is provided and valid
            if not kwargs.get("path"):
                error_msg = "No valid path provided for local mode. Check your configuration."
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Using local mode with path: {kwargs.get('path')}")
                
        elif mode.lower() == "server":
            # For server mode, only use host/port
            if "host" not in kwargs and VECTOR_STORE_HOST:
                kwargs["host"] = VECTOR_STORE_HOST
            if "port" not in kwargs:
                if isinstance(VECTOR_STORE_PORT, int):
                    kwargs["port"] = VECTOR_STORE_PORT
                elif isinstance(VECTOR_STORE_PORT, str) and VECTOR_STORE_PORT.isdigit():
                    kwargs["port"] = int(VECTOR_STORE_PORT)
            # Remove local path param if present
            kwargs.pop("path", None)
            
            # Ensure host and port are provided
            if not kwargs.get("host") or not kwargs.get("port"):
                error_msg = "Host and port must be provided for server mode. Check your configuration."
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Using server mode with host: {kwargs.get('host')}, port: {kwargs.get('port')}")
        
        # Log final parameters being passed
        logger.info(f"Final parameters for QdrantProvider: {kwargs}")
        
        # Get QdrantProvider instance and explicitly connect
        provider = QdrantProvider(**kwargs)
        try:
            provider.connect()  # Explicitly connect
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise
        return provider
    # Add more providers as needed
    else:
        raise ValueError(f"Unsupported vector store provider: {store_type}")
