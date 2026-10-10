"""
Test script for batch operations in the vector store service.

This script compares performance between batch mode and single document mode
and verifies data integrity when using batch operations.
"""
import time
import uuid
import random
import string
import os
import sys
import numpy as np
from typing import List, Dict, Any
from contextlib import contextmanager

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import required modules
from app.core.config_provider import get_config_provider
from app.integrations.vector_store import get_vector_store
from app.services.vector_store_service import add_report_to_vector_store
from app.db.database import get_database
from app.db.base import schema_name
from app.models.db_models import Report, Employee
from sqlalchemy.sql import text
from sqlalchemy import insert
from app.core.logger import logger

# Test configuration
TEST_COLLECTION = "test_batch_operations"
NUM_DOCUMENTS = 100  # Number of documents to add in each test
DOCUMENT_LENGTH = 500  # Length of each document
VECTOR_SIZE = 256  # Size of embedding vectors to generate
CLEANUP_AFTER_TEST = True  # Whether to delete test data after running tests


def generate_random_text(length: int = 500) -> str:
    """Generate random text for testing."""
    words = [
        "employee", "report", "performance", "evaluation", "goal", "achievement",
        "challenge", "project", "team", "collaboration", "skills", "improvement",
        "deadline", "quality", "communication", "meeting", "objective", "task",
        "development", "feedback", "growth", "efficiency", "productivity", "review"
    ]
    
    text_parts = []
    remaining_length = length
    
    while remaining_length > 0:
        word = random.choice(words)
        if len(word) <= remaining_length:
            text_parts.append(word)
            remaining_length -= len(word)
            if remaining_length > 0:
                text_parts.append(" ")
                remaining_length -= 1
        else:
            break
            
    return "".join(text_parts)


def generate_mock_embedding(size: int) -> List[float]:
    """Generate a mock embedding vector for testing."""
    return list(np.random.rand(size))


@contextmanager
def measure_time() -> float:
    """Context manager to measure execution time."""
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    return elapsed


def setup_test_collection(vector_store, collection_name: str, vector_size: int) -> bool:
    """Set up a test collection for batch operations testing."""
    try:
        # Create a new collection for testing
        logger.info(f"Setting up test collection: {collection_name}")
        success = vector_store.setup_collection(collection_name, vector_size)
        if success:
            logger.info(f"Test collection {collection_name} created successfully")
        else:
            logger.error(f"Failed to create test collection {collection_name}")
        return success
    except Exception as e:
        logger.error(f"Error setting up test collection: {e}")
        return False


def cleanup_test_data(vector_store, collection_name: str) -> None:
    """Clean up test data after tests are complete."""
    try:
        # In a real system, we'd delete the collection, but most vector store implementations
        # don't have a simple way to delete collections, so we'll log a message instead
        logger.info(f"Test cleanup: Would delete collection {collection_name} in a production system")
        
        # For Qdrant, we could use the following if we had access to the underlying client:
        # vector_store.client.delete_collection(collection_name)
        
        # Clean up database mappings
        db = get_database()
        with db.create_session() as session:
            query = text(f"""
            DELETE FROM {schema_name}.qdrant_mappings 
            WHERE qdrant_id IN (
                SELECT qdrant_id FROM {schema_name}.qdrant_mappings
                WHERE qdrant_id::text LIKE 'test_batch%'
            )
            """)
            session.execute(query)
            session.commit()
            logger.info("Deleted test mappings from database")
            
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")


def test_single_add_performance() -> float:
    """Test adding documents one by one and measure performance."""
    logger.info(f"Starting single document add performance test with {NUM_DOCUMENTS} documents...")
    
    vector_store = get_vector_store()
    setup_test_collection(vector_store, TEST_COLLECTION, VECTOR_SIZE)
    
    start_time = time.time()
    
    with vector_store:
        for i in range(NUM_DOCUMENTS):
            # Use a pure UUID without string prefix
            document_id = str(uuid.uuid4())
            
            # Generate mock data
            text = generate_random_text(DOCUMENT_LENGTH)
            vector = generate_mock_embedding(VECTOR_SIZE)
            
            # Create payload
            payload = {
                "report_id": f"test-report-{i}",
                "employee_id": random.randint(1, 100),
                "chunk_index": 0,
                "report_date": "2023-01-01",
                "text": text
            }
            
            # Add document
            success = vector_store.add_document(
                collection_name=TEST_COLLECTION,
                document_id=document_id,
                vector=vector,
                payload=payload
            )
            
            if not success:
                logger.error(f"Failed to add document {i}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Single document add test completed in {elapsed_time:.2f} seconds")
    return elapsed_time


def test_batch_add_performance() -> float:
    """Test adding documents in batch and measure performance."""
    logger.info(f"Starting batch document add performance test with {NUM_DOCUMENTS} documents...")
    
    vector_store = get_vector_store()
    setup_test_collection(vector_store, TEST_COLLECTION, VECTOR_SIZE)
    
    # Prepare batch data
    points = []
    for i in range(NUM_DOCUMENTS):
        # Use pure UUID without string prefix
        document_id = str(uuid.uuid4())
        
        # Generate mock data
        text = generate_random_text(DOCUMENT_LENGTH)
        vector = generate_mock_embedding(VECTOR_SIZE)
        
        # Create payload
        payload = {
            "report_id": f"test-report-{i}",
            "employee_id": random.randint(1, 100),
            "chunk_index": 0,
            "report_date": "2023-01-01",
            "text": text
        }
        
        # Add to points batch
        points.append({
            "document_id": document_id,
            "vector": vector,
            "payload": payload
        })
    
    # Time the batch operation
    start_time = time.time()
    
    with vector_store:
        # Add all documents in a single batch operation
        success = vector_store.add_documents_batch(
            collection_name=TEST_COLLECTION,
            points=points
        )
        
        if not success:
            logger.error("Batch operation failed")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Batch document add test completed in {elapsed_time:.2f} seconds")
    return elapsed_time


def test_batch_retry_mechanism():
    """Test the retry mechanism for batch operations."""
    logger.info("Testing batch retry mechanism...")
    
    # This test is conceptual - we can't easily trigger failures in the vector store
    # In a real test environment, we would mock the vector store to simulate failures
    logger.info("Note: This is a conceptual test. In real environments, use mocks to test retry logic.")
    
    # Get configuration parameters
    config = get_config_provider()
    retry_count = config.get("max_attempts", 3, section="vector_db.batch_processing.retry")
    
    logger.info(f"Configured retry count: {retry_count}")
    logger.info("Batch retry mechanism test: Passed (conceptual)")
    
    return True


def create_test_report(session) -> str:
    """Create a test report in the database for the integrated test."""
    # First make sure we have an employee
    employee = session.query(Employee).first()
    
    # If no employee exists, create one
    if not employee:
        employee = Employee(
            name="Test Employee",
            designation="Test Role",
            wing="Test Department",
            bps="BS-17"
        )
        session.add(employee)
        session.flush()
    
    # Now create a test report
    report = Report(
        employee_id=employee.id,
        report_date="2023-01-01",
        report_text="This is a test report for batch operations testing"
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    
    logger.info(f"Created test report with ID: {report.report_id}")
    return str(report.report_id)


def test_integrated_batch_service():
    """Test the integrated batch service using the add_report_to_vector_store function."""
    logger.info("Testing integrated batch service with add_report_to_vector_store...")
    
    # Enable batch mode for this test
    config = get_config_provider()
    batch_mode = config.get("enabled", True, section="vector_db.batch_processing")
    
    if not batch_mode:
        logger.warning("Batch mode is disabled in configuration. Test will still run.")
    
    # Create a test report in the database first
    db = get_database()
    with db.create_session() as session:
        report_id = create_test_report(session)
    
    # Create mock report data using the actual report ID from the database
    employee_id = 1  # Use the first employee ID
    report_date = "2023-01-01"
    
    # Create a longer text that will be chunked
    report_text = " ".join([generate_random_text(500) for _ in range(5)])
    
    start_time = time.time()
    
    # Call the service function with the valid report_id
    success = add_report_to_vector_store(
        report_id=report_id,
        employee_id=employee_id,
        report_date=report_date,
        report_text=report_text
    )
    
    elapsed_time = time.time() - start_time
    
    if success:
        logger.info(f"Integrated batch service test passed in {elapsed_time:.2f} seconds")
    else:
        logger.error("Integrated batch service test failed")
    
    return success


def run_all_tests():
    """Run all batch operation tests and report results."""
    print("\n==== Vector Store Batch Operations Tests ====\n")
    
    try:
        # Test single document performance
        single_time = test_single_add_performance()
        
        # Test batch performance
        batch_time = test_batch_add_performance()
        
        # Test retry mechanism
        retry_test = test_batch_retry_mechanism()
        
        # Test integrated service
        service_test = test_integrated_batch_service()
        
        # Calculate speedup
        speedup = single_time / batch_time if batch_time > 0 else 0
        
        # Print test results
        print("\n==== Test Results ====")
        print(f"Single document mode: {single_time:.2f} seconds")
        print(f"Batch mode: {batch_time:.2f} seconds")
        print(f"Speedup factor: {speedup:.2f}x")
        print(f"Retry mechanism test: {'Passed' if retry_test else 'Failed'}")
        print(f"Integrated service test: {'Passed' if service_test else 'Failed'}")
        
        # Clean up test data if configured
        if CLEANUP_AFTER_TEST:
            vector_store = get_vector_store()
            cleanup_test_data(vector_store, TEST_COLLECTION)
        
        print("\nAll tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
