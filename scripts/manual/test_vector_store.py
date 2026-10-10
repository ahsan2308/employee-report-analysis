import sys
import os
import uuid
import time
from datetime import datetime

from qdrant_client.models import Filter, FieldCondition, MatchValue

# Add the project root to the path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import from the new modules instead of the deprecated one
from app.services.vector_store_service import (
    chunk_text,
    setup_collection,
    add_report_to_vector_store,
    search_reports,
    get_report_chunks,
    get_embedding_size,
    COLLECTION_NAME
)
from app.services.embedding_service import get_embedding
from app.vector_store import get_vector_store
from app.core.logger import logger
from app.database import get_database
from app.models.db_models import Report, Employee

# Get vector store and collection name
qdrant = get_vector_store()

def test_qdrant_connection():
    """Test if Qdrant server is reachable."""
    print("\n===== Testing Qdrant Connection =====")
    try:
        with qdrant:  # Use context manager for proper connection handling
            qdrant.connect()
            print("Qdrant connection successful")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant server: {e}")
        return False

def test_collection_management():
    """Test collection creation, deletion, and dimension handling."""
    print("\n===== Testing Collection Management =====")
    
    # 1. Test get_embedding_size
    print("Testing embedding size detection...")
    embedding_size = get_embedding_size()
    print(f"Detected embedding size: {embedding_size}")
    
    # 2. Delete collection if it exists (testing delete_collection functionality)
    print(f"Testing delete_collection for '{COLLECTION_NAME}'...")
    with qdrant:
        try:
            collection_exists = False
            try:
                info = qdrant.get_collection_info(COLLECTION_NAME)
                if info:
                    collection_exists = True
                    old_dimension = info.get('dimension', 0)
                    print(f"Found existing collection with dimension: {old_dimension}")
            except Exception:
                print(f"Collection '{COLLECTION_NAME}' does not exist yet")
                
            # If collection exists, test deletion
            if collection_exists:
                delete_success = qdrant.delete_collection(COLLECTION_NAME)
                print(f"Collection deletion result: {'Success' if delete_success else 'Failed'}")
                time.sleep(1)  # Give time for deletion to complete
                
                # Verify collection is deleted
                try:
                    qdrant.get_collection_info(COLLECTION_NAME)
                    print("ERROR: Collection still exists after deletion")
                except Exception:
                    print("Collection successfully deleted (verified)")
        except Exception as e:
            print(f"Error during collection deletion test: {e}")
    
    # 3. Test setup_collection (should create with correct dimensions)
    print("\nTesting setup_collection...")
    setup_success = setup_collection()
    print(f"Collection setup: {'Success' if setup_success else 'Failed'}")
    
    # 4. Verify collection was created with correct dimensions
    with qdrant:
        try:
            info = qdrant.get_collection_info(COLLECTION_NAME)
            if info:
                print(f"Collection info: {info}")
                # Check if dimensions match what we detected
                if info.get('dimension') == embedding_size:
                    print("✅ Collection has correct dimension")
                else:
                    print(f"❌ Dimension mismatch: expected {embedding_size}, got {info.get('dimension')}")
        except Exception as e:
            print(f"Error verifying collection info: {e}")

def test_chunk_text():
    """Test text chunking functionality."""
    print("\n===== Testing Text Chunking =====")
    
    test_texts = [
        "This is a short text that shouldn't be chunked.",
        "This is a longer text that should be split into multiple chunks. " * 20,
        "",
        None
    ]
    
    for i, text in enumerate(test_texts):
        print(f"\nText {i+1}:")
        chunks = chunk_text(text, max_chunk_size=100)
        print(f"Generated {len(chunks)} chunks.")
        if chunks:
            print(f"First chunk: {chunks[0][:50]}...")
            if len(chunks) > 1:
                print(f"Last chunk: {chunks[-1][:50]}...")

def test_add_report():
    """Test adding a report to Qdrant."""
    print("\n===== Testing Add Report to Vector Store =====")
    
    # Create a test employee and report in the database first
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Create or find a test employee
        test_employee_id = 9999  # Use a high number unlikely to exist in real data
        employee = session.query(Employee).filter(Employee.id == test_employee_id).first()
        if not employee:
            # Create a test employee if it doesn't exist
            employee = Employee(id=test_employee_id, name="Test Employee", wing="Test Wing", position="Test Position")
            session.add(employee)
            session.flush()  # Flush to get the ID
        
        # Create a test report
        test_report_date = datetime.now().strftime("%Y-%m-%d")
        test_report_text = ("This is a test report for employee performance evaluation. "
                          "The employee has shown great progress in the last quarter. "
                          "They completed all assigned tasks on time and collaborated well with the team. "
                          "Areas for improvement include documentation and time management. "
                          "Overall, their performance has been above average.") * 3  # Make it longer to test chunking
        
        test_report = Report(
            employee_id=test_employee_id,
            report_date=datetime.now().date(),
            report_text=test_report_text
        )
        session.add(test_report)
        session.commit()
        
        test_report_id = test_report.report_id
    
    print(f"Test Report ID: {test_report_id}")
    print(f"Adding report for employee ID: {test_employee_id}")
    
    # Now that the report exists in the database, add it to vector store
    add_report_to_vector_store(test_report_id, test_employee_id, test_report_date, test_report_text)
    
    return test_report_id, test_employee_id

def test_search_reports(employee_id):
    """Test searching for reports."""
    print("\n===== Testing Search Reports =====")
    
    search_queries = [
        "performance",
        "improvement",
        "collaboration",
        "efh eiihnouivfhsuivg"  # Should not match anything
    ]
    
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        results = search_reports(query, employee_id, top_k=3, bypass_threshold=False)
        print(f"Found {len(results)} results")
        # Add score information to verify relevance
        for i, result in enumerate(results):
            print(f"Result {i+1}:")
            print(f"  Date: {result.get('report_date')}")
            print(f"  Score: {result.get('score', 'N/A')}")
            print(f"  Text: {result.get('text')[:100]}...")

def test_get_report_chunks(report_id):
    """Test retrieving chunks for a report."""
    print("\n===== Testing Get Report Chunks =====")
    
    print(f"Getting chunks for report: {report_id}")
    chunks = get_report_chunks(report_id)
    print(f"Retrieved {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk[:100]}...")
    
    # Test with invalid UUID
    print("\nTesting with invalid UUID:")
    invalid_chunks = get_report_chunks("not-a-uuid")
    print(f"Retrieved {len(invalid_chunks)} chunks (expected 0)")
    
    # Test with non-existent UUID
    print("\nTesting with non-existent UUID:")
    non_existent_chunks = get_report_chunks(uuid.uuid4())
    print(f"Retrieved {len(non_existent_chunks)} chunks (expected 0)")

def cleanup_test_data(employee_id):
    """Clean up test data to avoid cluttering the database."""
    print("\n===== Cleaning Up Test Data =====")
    
    try:
        # Define the filter to match documents with our test employee ID
        filter_params = {
            "must": [
                {
                    "key": "employee_id",
                    "match": {"value": employee_id}
                }
            ]
        }
        
        # Filter object for the delete operation
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="employee_id",
                    match=MatchValue(value=employee_id)
                )
            ]
        )
        
        # Delete test points from vector store using context manager
        with qdrant:
            # Delete test points from vector store
            delete_result = qdrant.delete_document(
                collection_name=COLLECTION_NAME,
                points_selector=delete_filter
            )
            
            # Verify deletion was successful
            deletion_verified = qdrant.verify_deletion(
                collection_name=COLLECTION_NAME, 
                filter_params=filter_params
            )
        
        if delete_result and deletion_verified:
            print(f"Successfully deleted test data for employee ID: {employee_id} (verified)")
        else:
            print(f"Deletion operation completed, but verification failed for employee ID: {employee_id}")
        
        # Also clean up from the database
        db_instance = get_database()
        with db_instance.create_session() as session:
            # Delete the test report
            session.query(Report).filter(Report.employee_id == employee_id).delete()
            # Delete the test employee
            session.query(Employee).filter(Employee.id == employee_id).delete()
            session.commit()
            print(f"Deleted test data from database for employee ID: {employee_id}")
    except Exception as e:
        print(f"Error cleaning up test data: {e}")

def test_embedding_stability():
    """Test the stability and consistency of embeddings."""
    print("\n===== Testing Embedding Stability =====")
    
    test_text = "This is a test text for checking embedding consistency."
    
    # Generate multiple embeddings for the same text
    print("Generating multiple embeddings for the same text...")
    embedding1 = get_embedding(test_text)
    embedding2 = get_embedding(test_text)
    
    # Check dimensions
    print(f"Embedding dimensions: {len(embedding1)}")
    
    # Check consistency (not exact equality due to potential randomness)
    import numpy as np
    similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
    print(f"Cosine similarity between two embeddings of same text: {similarity:.6f}")
    
    # Test embedding for query vs document
    print("\nTesting query vs document embedding differences:")
    doc_embedding = get_embedding(test_text, is_query=False)
    query_embedding = get_embedding(test_text, is_query=True)
    
    # Check if query preprocessing is being applied
    doc_query_similarity = np.dot(doc_embedding, query_embedding) / (np.linalg.norm(doc_embedding) * np.linalg.norm(query_embedding))
    print(f"Cosine similarity between document and query embedding: {doc_query_similarity:.6f}")
    

if __name__ == "__main__":
    # Run all tests in sequence
    logger.info("Starting vector store test script")
    
    # Test basic connection and setup
    test_qdrant_connection()
    
    # Test the new collection management functionality
    test_collection_management()
    
    # Test embedding stability
    test_embedding_stability()
    
    # Test text chunking (doesn't require database)
    test_chunk_text()
    
    # Test adding, searching, and retrieving reports
    test_report_id, test_employee_id = test_add_report()
    test_search_reports(test_employee_id)
    test_get_report_chunks(test_report_id)
    
    # Clean up test data
    cleanup_test_data(test_employee_id)
    
    print("\n===== All Tests Completed =====")
    logger.info("Vector store test script completed")
