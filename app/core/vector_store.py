import chromadb
from chromadb.utils import embedding_functions

import sys
import os

# Get the project root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.core.embeddings import get_embedding

# Initialize ChromaDB locally
chroma_client = chromadb.PersistentClient(path="../vector_db")
collection = chroma_client.get_or_create_collection(name="employee_reports")

def add_to_vector_store(doc_id: str, text: str):
    """
    Adds a document to the vector store with its embedding.
    
    :param doc_id: Unique identifier for the document
    :param text: The document content
    """
    embedding = get_embedding(text)
    collection.add(ids=[doc_id], embeddings=[embedding], documents=[text])

def search_reports(query: str, top_k: int = 5):
    """
    Searches for the most relevant reports based on the query.
    
    :param query: The search query
    :param top_k: Number of top results to return
    :return: List of relevant report texts
    """
    query_embedding = get_embedding(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results["documents"]

if __name__ == "__main__":
    # Test storing & searching
    add_to_vector_store("report_1", "Employee John Doe exceeded targets this quarter.")
    print(search_reports("high-performing employee"))
