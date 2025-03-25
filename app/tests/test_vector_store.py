import sys
import os
import uuid
from datetime import datetime
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Add the project root to the path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import functions to test
from app.core.vector_store import (
    chunk_text,
    setup_qdrant_collection,
    add_report_to_qdrant,
    search_reports,
    get_report_chunks,
    check_qdrant_connection,
    check_collection_size,
    qdrant,
    COLLECTION_NAME
)
from app.core.logger import logger
from app.database import get_database
from app.models.db_models import Report, Employee

def test_qdrant_connection():
    """Test if Qdrant server is reachable."""
    print("\n===== Testing Qdrant Connection =====")
    check_qdrant_connection()

def test_setup_collection():
    """Test creating/accessing the collection."""
    print("\n===== Testing Collection Setup =====")
    setup_qdrant_collection()
    check_collection_size()

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
    print("\n===== Testing Add Report to Qdrant =====")
    
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
    
    # Now that the report exists in the database, add it to Qdrant
    add_report_to_qdrant(test_report_id, test_employee_id, test_report_date, test_report_text)
    
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
        results = search_reports(query, employee_id, top_k=3)
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
        # Delete test points from Qdrant using the correct API
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="employee_id",
                        match=MatchValue(value=employee_id)
                    )
                ]
            )
        )
        print(f"Deleted test data for employee ID: {employee_id}")
        
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

if __name__ == "__main__":
    # Run all tests in sequence
    logger.info("Starting vector store test script")
    
    # Test basic connection and setup
    test_qdrant_connection()
    test_setup_collection()
    
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
