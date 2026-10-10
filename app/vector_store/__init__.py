"""Compatibility re-exports; the implementation lives in app.integrations.vector_store."""
from app.integrations.vector_store import (  # noqa: F401
    VECTOR_STORE_HOST,
    VECTOR_STORE_MODE,
    VECTOR_STORE_PATH,
    VECTOR_STORE_PORT,
    VECTOR_STORE_TYPE,
    BaseVectorStore,
    QdrantProvider,
    get_vector_store,
)
