"""
Test script to verify Qdrant date range filtering functionality.
This script will:
1. Create a test collection
2. Insert test data with different dates
3. Run search queries with date filters
4. Verify the filtering works as expected
"""

import sys
import os
from datetime import datetime, date, timedelta
from uuid import uuid4
import numpy as np
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.vector_store import get_vector_store
from app.core.logger import logger

# Constants
TEST_COLLECTION = "date_filter_test"
VECTOR_SIZE = 4  # Small vector size for testing

def create_test_vector(seed=None):
    """Create a simple test vector"""
    if seed is not None:
        np.random.seed(seed)
    return np.random.rand(VECTOR_SIZE).tolist()

def date_to_timestamp(dt):
    """Convert date to timestamp"""
    if isinstance(dt, str):
        dt = datetime.strptime(dt, "%Y-%m-%d")
    elif isinstance(dt, date):
        dt = datetime.combine(dt, datetime.min.time())
    return dt.timestamp()

def setup_test_collection():
    """Create and setup test collection"""
    vector_store = get_vector_store()
    with vector_store:
        # Check if collection exists
        try:
            collections = vector_store.client.get_collections()
            if TEST_COLLECTION in [c.name for c in collections.collections]:
                # Delete existing collection
                logger.info(f"Deleting existing collection '{TEST_COLLECTION}'")
                vector_store.delete_collection(TEST_COLLECTION)
        except Exception as e:
            logger.error(f"Error checking collections: {e}")
        
        # Create new collection
        logger.info(f"Creating test collection '{TEST_COLLECTION}' with dimension {VECTOR_SIZE}")
        success = vector_store.setup_collection(TEST_COLLECTION, VECTOR_SIZE)
        
        if not success:
            logger.error("Failed to create test collection")
            return False
            
        # Create payload index for string date filtering
        try:
            logger.info("Creating payload index on report_date field")
            vector_store.client.create_payload_index(
                collection_name=TEST_COLLECTION,
                field_name="report_date",
                field_schema="keyword"
            )
            logger.info("Payload index created successfully")
        except Exception as e:
            logger.warning(f"Error creating payload index: {e}")
            
        return True

def insert_test_data():
    """Insert test data with different dates"""
    vector_store = get_vector_store()
    with vector_store:
        test_data = [
            {
                "id": str(uuid4()),
                "text": "Report from 2025-01-15",
                "date": "2025-01-15",
                "employee_id": 123
            },
            {
                "id": str(uuid4()),
                "text": "Report from 2025-02-20",
                "date": "2025-02-20", 
                "employee_id": 123
            },
            {
                "id": str(uuid4()),
                "text": "Report from 2025-03-25",
                "date": "2025-03-25",
                "employee_id": 123
            },
            {
                "id": str(uuid4()),
                "text": "Report from 2025-04-30",
                "date": "2025-04-30",
                "employee_id": 123
            },
            {
                "id": str(uuid4()),
                "text": "Report from 2025-05-05",
                "date": "2025-05-05",
                "employee_id": 123
            },
            {
                "id": str(uuid4()),
                "text": "Report from 2025-06-10",
                "date": "2025-06-10",
                "employee_id": 456  # Different employee
            }
        ]
        
        points = []
        for idx, item in enumerate(test_data):
            # Create payload
            payload = {
                "report_id": item["id"],
                "employee_id": item["employee_id"],
                "text": item["text"],
                "report_date": item["date"],
                "report_date_ts": date_to_timestamp(item["date"])
            }
            
            # Add to points batch
            points.append({
                "document_id": item["id"],
                "vector": create_test_vector(seed=idx),
                "payload": payload
            })
            
        # Insert data
        success = vector_store.add_documents_batch(
            collection_name=TEST_COLLECTION,
            points=points
        )
        
        if success:
            logger.info(f"Successfully inserted {len(points)} test documents")
        else:
            logger.error("Failed to insert test data")
            
        return success

def test_string_date_filtering():
    """Test filtering with string date field"""
    vector_store = get_vector_store()
    with vector_store:
        logger.info("\n=== Testing String Date Filtering ===")
        
        # 1. Test earlier than March 25
        filter_params = {
            "must": [
                {
                    "key": "report_date",
                    "range": {"lt": "2025-03-25"}
                }
            ]
        }
        
        logger.info(f"Filter: Earlier than 2025-03-25: {json.dumps(filter_params)}")
        results = vector_store.search(
            collection_name=TEST_COLLECTION,
            query_vector=create_test_vector(),
            limit=10,
            filter_params=filter_params
        )
        
        logger.info(f"Found {len(results)} results:")
        for r in results:
            logger.info(f"  {r.get('report_date')}: {r.get('text')}")
            
        # 2. Test between Feb 1 and April 30
        filter_params = {
            "must": [
                {
                    "key": "report_date",
                    "range": {"gte": "2025-02-01", "lte": "2025-04-30"}
                }
            ]
        }
        
        logger.info(f"\nFilter: Between 2025-02-01 and 2025-04-30: {json.dumps(filter_params)}")
        results = vector_store.search(
            collection_name=TEST_COLLECTION,
            query_vector=create_test_vector(),
            limit=10,
            filter_params=filter_params
        )
        
        logger.info(f"Found {len(results)} results:")
        for r in results:
            logger.info(f"  {r.get('report_date')}: {r.get('text')}")

def test_timestamp_date_filtering():
    """Test filtering with timestamp date field"""
    vector_store = get_vector_store()
    with vector_store:
        logger.info("\n=== Testing Timestamp Date Filtering ===")
        
        # 1. Test earlier than March 25
        cutoff_date = datetime.strptime("2025-03-25", "%Y-%m-%d")
        cutoff_ts = cutoff_date.timestamp()
        
        filter_params = {
            "must": [
                {
                    "key": "report_date_ts",
                    "range": {"lt": cutoff_ts}
                }
            ]
        }
        
        logger.info(f"Filter: Earlier than 2025-03-25 (timestamp): {json.dumps(filter_params)}")
        results = vector_store.search(
            collection_name=TEST_COLLECTION,
            query_vector=create_test_vector(),
            limit=10,
            filter_params=filter_params
        )
        
        logger.info(f"Found {len(results)} results:")
        for r in results:
            logger.info(f"  {r.get('report_date')}: {r.get('text')}")
            
        # 2. Test with employee filter + date filter
        filter_params = {
            "must": [
                {
                    "key": "employee_id",
                    "match": {"value": 123}
                },
                {
                    "key": "report_date_ts",
                    "range": {"lt": cutoff_ts}
                }
            ]
        }
        
        logger.info(f"\nFilter: Employee 123 + Earlier than 2025-03-25: {json.dumps(filter_params)}")
        results = vector_store.search(
            collection_name=TEST_COLLECTION,
            query_vector=create_test_vector(),
            limit=10,
            filter_params=filter_params
        )
        
        logger.info(f"Found {len(results)} results:")
        for r in results:
            logger.info(f"  Employee: {r.get('employee_id')}, Date: {r.get('report_date')}, Text: {r.get('text')}")

def main():
    """Main test function"""
    logger.info("Starting date filtering test")
    
    # Setup
    if not setup_test_collection():
        logger.error("Failed to setup test collection")
        return
        
    # Insert test data
    if not insert_test_data():
        logger.error("Failed to insert test data")
        return
        
    # Run tests
    test_string_date_filtering()
    test_timestamp_date_filtering()
    
    logger.info("Date filtering test completed")

if __name__ == "__main__":
    main()
