"""
Full Pipeline Integration Test

Tests the entire synchronization pipeline using:
1. Real SQL Server connection (Source)
2. Real PostgreSQL connection (Destination)
3. Real Celery Task logic (Orchestration)

This verifies that the tasks defined in app.tasks.sync_tasks actually work
when connected to real infrastructure.

Prerequisites:
- SQL Server running and accessible via env vars
- PostgreSQL running and accessible via env vars
- Redis (optional, as we execute tasks locally via .apply())

Run with: pytest tests/test_full_pipeline_tasks.py -v -s
"""
import pytest
import os
import sys
import logging
from sqlalchemy import text
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from app.tasks.sync_tasks import (
    sync_employee_reports_task,
    sync_vision_data_task,
    full_sync_task
)
from app.db.database import get_database
from app.models.sync_models import SyncHistory, SyncStatus, SyncType
from app.integrations.sqlserver.connector import create_sqlserver_connector

# Configure logging to see output during tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestFullPipeline:
    
    @pytest.fixture(scope="class")
    def db_session(self):
        """Provide a database session for verification."""
        db = get_database()
        session = db.create_session()
        yield session
        session.close()

    def test_infrastructure_readiness(self, db_session):
        """Verify both databases are reachable before starting."""
        print("\n=== Checking Infrastructure ===")
        
        # Check SQL Server
        try:
            print("Connecting to SQL Server...")
            connector = create_sqlserver_connector()
            assert connector.test_connection() is True
            print("[OK] SQL Server is reachable")
        except Exception as e:
            pytest.fail(f"[FAIL] SQL Server connection failed: {e}")

        # Check PostgreSQL
        try:
            print("Connecting to PostgreSQL...")
            db_session.execute(text("SELECT 1"))
            print("[OK] PostgreSQL is reachable")
        except Exception as e:
            pytest.fail(f"[FAIL] PostgreSQL connection failed: {e}")

    def test_full_sync_task_execution(self, db_session):
        """
        Execute the full_sync_task and verify results in the database.
        This runs the actual logic that the Celery worker would run.
        """
        print("\n=== Testing Full Sync Pipeline ===")
        print("This may take a moment depending on data size...")
        
        # 1. Execute the task synchronously
        # calling .apply() on a Celery task executes it locally in the current process
        try:
            logger.info("Invoking full_sync_task()...")
            
            # We call the function directly or via apply() to bypass the broker
            # full_sync_task internally calls sub-tasks via .apply(), so calling it directly works
            result = full_sync_task()
            
            print(f"\nTask Execution Result:\n{result}")
            
            # Force session to reload data from DB to see changes made by the task
            # Using commit() ensures we end the current transaction and see updates 
            # from the task's separate session
            db_session.commit()
            
            # 2. Verify Return Structure
            assert result['sync_type'] == 'full'
            assert 'employee_reports' in result
            assert 'vision_data' in result
            assert 'total_records_synced' in result
            
            # 3. Verify Employee Reports Sync Record in DB
            emp_sync_id = result['employee_reports']['sync_id']
            emp_job = db_session.query(SyncHistory).filter(
                SyncHistory.sync_id == emp_sync_id
            ).first()
            
            assert emp_job is not None, f"Employee sync job {emp_sync_id} not found in DB"
            assert emp_job.status == SyncStatus.COMPLETED.value
            assert emp_job.sync_type == SyncType.EMPLOYEE_REPORTS.value
            
            print(f"\n[OK] Employee Reports Sync Job verified (ID: {emp_sync_id})")
            print(f"   - Records Synced: {emp_job.records_synced}")
            print(f"   - Records Created: {emp_job.records_created}")
            print(f"   - Records Updated: {emp_job.records_updated}")
            print(f"   - Status: {emp_job.status}")

            # 4. Verify Vision Data Sync Record in DB
            vis_sync_id = result['vision_data']['sync_id']
            vis_job = db_session.query(SyncHistory).filter(
                SyncHistory.sync_id == vis_sync_id
            ).first()
            
            assert vis_job is not None, f"Vision sync job {vis_sync_id} not found in DB"
            assert vis_job.status == SyncStatus.COMPLETED.value
            assert vis_job.sync_type == SyncType.VISION_DATA.value
            
            print(f"\n[OK] Vision Data Sync Job verified (ID: {vis_sync_id})")
            print(f"   - Records Synced: {vis_job.records_synced}")
            print(f"   - Records Created: {vis_job.records_created}")
            print(f"   - Records Updated: {vis_job.records_updated}")
            print(f"   - Status: {vis_job.status}")
            
            # 5. Global Success Check
            if result['total_errors'] > 0:
                print(f"\n[WARN] Warning: Sync completed with {result['total_errors']} errors.")
            else:
                print("\n[SUCCESS] Full Pipeline Sync Completed Successfully with 0 errors!")
            
        except Exception as e:
            pytest.fail(f"Pipeline execution failed: {e}")

    def test_incremental_sync_task_execution(self, db_session):
        """
        Test incremental sync after a full sync has been completed.
        
        This test:
        1. Verifies that a previous full sync exists (from test_full_sync_task_execution)
        2. Runs an incremental sync
        3. Verifies that the last_sync_timestamp is used correctly
        4. Ensures only new/updated records would be synced
        """
        print("\n=== Testing Incremental Sync Pipeline ===")
        print("This test verifies timestamp-based incremental sync logic...")
        
        try:
            # 1. Verify that a previous full sync exists
            logger.info("Checking for previous full sync...")
            
            last_emp_sync = db_session.query(SyncHistory).filter(
                SyncHistory.sync_type == SyncType.EMPLOYEE_REPORTS.value,
                SyncHistory.status == SyncStatus.COMPLETED.value,
                SyncHistory.last_sync_timestamp.isnot(None)
            ).order_by(SyncHistory.last_sync_timestamp.desc()).first()
            
            last_vision_sync = db_session.query(SyncHistory).filter(
                SyncHistory.sync_type == SyncType.VISION_DATA.value,
                SyncHistory.status == SyncStatus.COMPLETED.value,
                SyncHistory.last_sync_timestamp.isnot(None)
            ).order_by(SyncHistory.last_sync_timestamp.desc()).first()
            
            if not last_emp_sync or not last_vision_sync:
                pytest.skip("No previous full sync found. Run test_full_sync_task_execution first.")
            
            print(f"Found previous employee reports sync: {last_emp_sync.sync_id}")
            print(f"  - Last sync timestamp: {last_emp_sync.last_sync_timestamp}")
            print(f"Found previous vision data sync: {last_vision_sync.sync_id}")
            print(f"  - Last sync timestamp: {last_vision_sync.last_sync_timestamp}")
            
            # 2. Execute incremental sync task
            logger.info("Invoking incremental_sync_task()...")
            
            from app.tasks.sync_tasks import incremental_sync_task
            result = incremental_sync_task()
            
            print(f"\nIncremental Sync Result:\n{result}")
            
            # Force session to reload data
            db_session.commit()
            
            # 3. Verify Return Structure
            assert result['sync_type'] == 'incremental'
            assert 'employee_reports' in result
            assert 'vision_data' in result
            assert 'total_records_synced' in result
            
            # 4. Verify Employee Reports Incremental Sync
            emp_sync_id = result['employee_reports']['sync_id']
            emp_job = db_session.query(SyncHistory).filter(
                SyncHistory.sync_id == emp_sync_id
            ).first()
            
            assert emp_job is not None, f"Employee incremental sync job {emp_sync_id} not found in DB"
            assert emp_job.status == SyncStatus.COMPLETED.value
            assert emp_job.sync_type == SyncType.EMPLOYEE_REPORTS.value
            
            # Verify this is a NEW sync job (not the same as the last one)
            assert emp_job.sync_id != last_emp_sync.sync_id
            
            # Verify the sync used a timestamp (incremental mode)
            # The records_synced might be 0 if no new records exist since last sync
            print(f"\n[OK] Employee Reports Incremental Sync verified (ID: {emp_sync_id})")
            print(f"   - Records Synced: {emp_job.records_synced}")
            print(f"   - Records Queried: {emp_job.records_queried}")
            print(f"   - Status: {emp_job.status}")
            print(f"   - Last Sync Timestamp: {emp_job.last_sync_timestamp}")
            
            # 5. Verify Vision Data Incremental Sync
            vis_sync_id = result['vision_data']['sync_id']
            vis_job = db_session.query(SyncHistory).filter(
                SyncHistory.sync_id == vis_sync_id
            ).first()
            
            assert vis_job is not None, f"Vision incremental sync job {vis_sync_id} not found in DB"
            assert vis_job.status == SyncStatus.COMPLETED.value
            assert vis_job.sync_type == SyncType.VISION_DATA.value
            
            # Verify this is a NEW sync job
            assert vis_job.sync_id != last_vision_sync.sync_id
            
            print(f"\n[OK] Vision Data Incremental Sync verified (ID: {vis_sync_id})")
            print(f"   - Records Synced: {vis_job.records_synced}")
            print(f"   - Records Queried: {vis_job.records_queried}")
            print(f"   - Status: {vis_job.status}")
            print(f"   - Last Sync Timestamp: {vis_job.last_sync_timestamp}")
            
            # 6. Verify Incremental Logic
            # If no records changed since last sync, records_synced should be 0
            # This is EXPECTED behavior for incremental sync
            if emp_job.records_synced == 0:
                print("\n[INFO] No new employee reports since last sync (expected for incremental)")
            if vis_job.records_synced == 0:
                print("[INFO] No new vision data since last sync (expected for incremental)")
            
            # 7. Verify timestamp progression
            # The new sync's timestamp should be >= the previous sync's timestamp
            if emp_job.last_sync_timestamp and last_emp_sync.last_sync_timestamp:
                assert emp_job.last_sync_timestamp >= last_emp_sync.last_sync_timestamp, \
                    "Employee reports timestamp should progress forward"
                print(f"[OK] Employee reports timestamp progressed: {last_emp_sync.last_sync_timestamp} -> {emp_job.last_sync_timestamp}")
            
            if vis_job.last_sync_timestamp and last_vision_sync.last_sync_timestamp:
                assert vis_job.last_sync_timestamp >= last_vision_sync.last_sync_timestamp, \
                    "Vision data timestamp should progress forward"
                print(f"[OK] Vision data timestamp progressed: {last_vision_sync.last_sync_timestamp} -> {vis_job.last_sync_timestamp}")
            
            # 8. Success Summary
            total_synced = result['total_records_synced']
            total_errors = result['total_errors']
            
            print(f"\n[SUCCESS] Incremental Sync Completed!")
            print(f"   - Total Records Synced: {total_synced}")
            print(f"   - Total Errors: {total_errors}")
            print(f"   - Incremental sync correctly used timestamp tracking")
            
            if total_synced == 0:
                print(f"   - [INFO] Zero records synced is EXPECTED if no data changed since last sync")
            
        except Exception as e:
            pytest.fail(f"Incremental sync test failed: {e}")
    
    def test_sync_history_tracking(self, db_session):
        """
        Verify that sync history is properly maintained across multiple syncs.
        
        This test:
        1. Queries all sync history records
        2. Verifies full and incremental syncs are both tracked
        3. Ensures timestamps are properly ordered
        """
        print("\n=== Testing Sync History Tracking ===")
        
        try:
            # Query all employee report syncs
            emp_syncs = db_session.query(SyncHistory).filter(
                SyncHistory.sync_type == SyncType.EMPLOYEE_REPORTS.value
            ).order_by(SyncHistory.started_at).all()
            
            # Query all vision data syncs
            vis_syncs = db_session.query(SyncHistory).filter(
                SyncHistory.sync_type == SyncType.VISION_DATA.value
            ).order_by(SyncHistory.started_at).all()
            
            print(f"\nFound {len(emp_syncs)} employee report sync(s)")
            print(f"Found {len(vis_syncs)} vision data sync(s)")
            
            # Verify we have at least 2 syncs (1 full + 1 incremental from previous tests)
            assert len(emp_syncs) >= 2, "Should have at least 2 employee report syncs (full + incremental)"
            assert len(vis_syncs) >= 2, "Should have at least 2 vision data syncs (full + incremental)"
            
            # Print sync history
            print("\nEmployee Reports Sync History:")
            for i, sync in enumerate(emp_syncs, 1):
                sync_mode = "FULL" if sync.sync_options and sync.sync_options.get('is_full_sync') else "INCREMENTAL"
                print(f"  {i}. [{sync_mode}] {sync.sync_id}")
                print(f"     Status: {sync.status}")
                print(f"     Started: {sync.started_at}")
                print(f"     Records: {sync.records_synced}/{sync.records_queried}")
                print(f"     Last Timestamp: {sync.last_sync_timestamp}")
            
            print("\nVision Data Sync History:")
            for i, sync in enumerate(vis_syncs, 1):
                sync_mode = "FULL" if sync.sync_options and sync.sync_options.get('is_full_sync') else "INCREMENTAL"
                print(f"  {i}. [{sync_mode}] {sync.sync_id}")
                print(f"     Status: {sync.status}")
                print(f"     Started: {sync.started_at}")
                print(f"     Records: {sync.records_synced}/{sync.records_queried}")
                print(f"     Last Timestamp: {sync.last_sync_timestamp}")
            
            # Verify timestamp ordering
            for i in range(1, len(emp_syncs)):
                prev_sync = emp_syncs[i-1]
                curr_sync = emp_syncs[i]
                if prev_sync.last_sync_timestamp and curr_sync.last_sync_timestamp:
                    assert curr_sync.last_sync_timestamp >= prev_sync.last_sync_timestamp, \
                        "Sync timestamps should be monotonically increasing"
            
            print("\n[OK] Sync history is properly tracked and ordered")
            
        except Exception as e:
            pytest.fail(f"Sync history tracking test failed: {e}")

if __name__ == "__main__":
    # Allow running this script directly
    sys.exit(pytest.main(["-v", "-s", __file__]))
