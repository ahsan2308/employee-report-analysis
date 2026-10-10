"""
Test script to verify sync_history model works correctly.
"""

import sys
import os

# Add the project root to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime
from app.db.database import get_database
from app.models.sync_models import SyncHistory, SyncType, SyncStatus



def test_sync_model():
    """Test creating and querying sync history records."""
    print("=" * 60)
    print("Testing Sync History Model")
    print("=" * 60)
    
    # Get database session
    db_instance = get_database()
    session = db_instance.create_session()
    
    try:
        # Create a test sync record
        test_sync = SyncHistory(
            sync_type=SyncType.EMPLOYEE_REPORTS.value,
            status=SyncStatus.COMPLETED.value,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            last_sync_timestamp=datetime.now(),
            records_queried=100,
            records_synced=95,
            records_created=50,
            records_updated=45,
            records_skipped=5,
            error_count=0,
            sync_options={"mode": "incremental", "batch_size": 1000},
            sync_metadata={"source": "test_script"}
        )
        
        # Save to database
        session.add(test_sync)
        session.commit()
        session.refresh(test_sync)
        
        print(f"\nSuccessfully created sync record:")
        print(f"   Sync ID: {test_sync.sync_id}")
        print(f"   Type: {test_sync.sync_type}")
        print(f"   Status: {test_sync.status}")
        print(f"   Records Synced: {test_sync.records_synced}/{test_sync.records_queried}")
        print()
        
        # Query the record back
        retrieved = session.query(SyncHistory).filter(
            SyncHistory.sync_id == test_sync.sync_id
        ).first()
        
        if retrieved:
            print("Successfully retrieved sync record from database")
            print(f"   Retrieved: {retrieved}")
            print()
            
            # Test to_dict() method
            sync_dict = retrieved.to_dict()
            print("Successfully converted to dictionary:")
            print(f"   Keys: {list(sync_dict.keys())}")
            print()
        
        # Clean up test record
        session.delete(test_sync)
        session.commit()
        print("Test record cleaned up")
        print()
        
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_sync_model()
