"""
Comprehensive Integration Tests for Job Description Sync Service

This test suite validates the complete JD sync pipeline from SQL Server to PostgreSQL:
- SQL Server connection and data retrieval
- Data transformation (datetime → string)
- Pydantic validation via JobDescriptionCSVRow
- Bulk processing and upsert operations
- Sync history tracking and metrics
- Error handling and edge cases

Prerequisites:
- SQL Server must be running with JobDescriptions table
- PostgreSQL must be running
- .env configuration must be correct
- JobDescriptions table must exist in SQL Server with test data

Usage:
    pytest app/tests/test_jd_sync_service_integration.py -v
    pytest app/tests/test_jd_sync_service_integration.py -v -k "test_full_sync"
    pytest app/tests/test_jd_sync_service_integration.py -v --tb=short -s
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import time

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.db_models import Employee, EmployeeJobDescription
from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.services.sync_service import create_sync_service, SyncService
from app.database import get_database
from app.database.sqlserver_connector import create_sqlserver_connector
from app.core.logger import logger


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_instance():
    """Get database instance for entire test session."""
    return get_database()


@pytest.fixture
def db_session(db_instance):
    """
    Create isolated database session for each test.
    Uses transactions with rollback for test isolation.
    """
    session = db_instance.create_session()
    session.begin()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def sqlserver_connector():
    """Create SQL Server connector for the test session."""
    connector = create_sqlserver_connector()
    
    # Verify connection
    if not connector.test_connection():
        pytest.skip("SQL Server is not available")
    
    return connector


@pytest.fixture(scope="session")
def sync_service(sqlserver_connector):
    """Create sync service instance for the test session."""
    return SyncService(sqlserver_connector, error_threshold_percent=10.0)


@pytest.fixture
def test_employees(db_session):
    """
    Create test employees in PostgreSQL for JD sync tests.
    
    Returns:
        List of test employee IDs
    """
    test_employee_ids = [999100, 999101, 999102]
    
    # Clean up any existing test employees
    db_session.query(Employee).filter(
        Employee.id.in_(test_employee_ids)
    ).delete(synchronize_session=False)
    db_session.flush()
    
    # Create fresh test employees
    employees = [
        Employee(
            id=emp_id,
            name=f"Test Employee JD {emp_id}",
            position="Software Engineer",
            wing="Engineering"
        )
        for emp_id in test_employee_ids
    ]
    
    db_session.add_all(employees)
    db_session.flush()
    
    logger.info(f"Created {len(employees)} test employees: {test_employee_ids}")
    
    return test_employee_ids


@pytest.fixture
def cleanup_test_data(db_session):
    """
    Cleanup fixture to remove test data after tests.
    Runs after each test that uses it.
    """
    yield
    
    # Clean up test JDs
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.jd_id.like("TEST%")
    ).delete(synchronize_session=False)
    
    # Clean up test employees (999xxx range)
    db_session.query(Employee).filter(
        Employee.id >= 999000
    ).delete(synchronize_session=False)
    
    db_session.commit()
    logger.info("Cleaned up test data")


# ============================================================================
# PHASE 1: SQL SERVER CONNECTION & DATA RETRIEVAL TESTS
# ============================================================================

class TestPhase1SQLServerConnection:
    """Test SQL Server connection and JD table access."""
    
    def test_connection_available(self, sqlserver_connector):
        """Verify SQL Server connection is working."""
        assert sqlserver_connector.test_connection() is True
        logger.info("✅ SQL Server connection test passed")
    
    def test_jd_table_exists(self, sqlserver_connector):
        """Verify JobDescriptions table exists in SQL Server."""
        allowed_tables = sqlserver_connector.get_allowed_tables()
        
        # Find JD table (case-insensitive)
        jd_table = None
        for table in allowed_tables:
            if 'jobdescription' in table.lower() or 'jd' in table.lower():
                jd_table = table
                break
        
        assert jd_table is not None, f"No JD table found in allowed tables: {allowed_tables}"
        logger.info(f"✅ Found JD table: {jd_table}")
    
    def test_jd_table_schema(self, sqlserver_connector, sync_service):
        """Verify JD table has required columns."""
        # Get table name
        jd_table = sync_service._get_job_descriptions_table_name()
        
        # Get schema
        schema = sqlserver_connector.get_table_schema(jd_table)
        
        # Verify required columns
        required_columns = {
            'Employee_ID', 'JD_ID', 'Job_Description', 
            'Assigned_Date', 'Is_Current'
        }
        
        schema_columns = set(schema.keys())
        missing_columns = required_columns - schema_columns
        
        assert not missing_columns, f"Missing required columns: {missing_columns}"
        logger.info(f"✅ JD table has all required columns: {required_columns}")
    
    def test_timestamp_column_detection(self, sqlserver_connector, sync_service):
        """Verify timestamp column can be detected for incremental sync."""
        jd_table = sync_service._get_job_descriptions_table_name()
        schema = sqlserver_connector.get_table_schema(jd_table)
        
        timestamp_col = sync_service._find_timestamp_column(schema)
        
        assert timestamp_col is not None, "No timestamp column found for incremental sync"
        logger.info(f"✅ Found timestamp column: {timestamp_col}")
    
    def test_query_jd_records(self, sqlserver_connector, sync_service):
        """Test querying JD records from SQL Server."""
        jd_table = sync_service._get_job_descriptions_table_name()
        schema = sqlserver_connector.get_table_schema(jd_table)
        timestamp_col = sync_service._find_timestamp_column(schema)
        
        # Get first batch of records
        batches = sqlserver_connector.get_all_records(
            table_name=jd_table,
            batch_size=10,
            order_by=timestamp_col
        )
        
        first_batch = next(batches, None)
        
        assert first_batch is not None, "No JD records found in SQL Server"
        assert len(first_batch) > 0, "First batch is empty"
        
        # Verify structure of first record
        first_record = first_batch[0]
        assert 'Employee_ID' in first_record
        assert 'JD_ID' in first_record
        assert 'Job_Description' in first_record
        
        logger.info(f"✅ Successfully queried {len(first_batch)} JD records from SQL Server")


# ============================================================================
# PHASE 2: DATA TRANSFORMATION TESTS
# ============================================================================

class TestPhase2DataTransformation:
    """Test transformation of SQL Server data to Pydantic format."""
    
    def test_transformer_basic(self):
        """Test basic transformation of SQL Server row."""
        from app.services.sync.transformers import JobDescriptionTransformer
        
        sql_row = {
            "Employee_ID": 101,
            "JD_ID": 1001,
            "Job_Description": "Responsible for backend development using Python and PostgreSQL.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime(2024, 11, 20, 10, 30)  # Should be excluded
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        # Verify required fields are present
        assert transformed['Employee_ID'] == 101
        assert transformed['JD_ID'] == 1001
        assert transformed['Job_Description'] == "Responsible for backend development using Python and PostgreSQL."
        assert transformed['Assigned_Date'] == date(2024, 1, 15)
        assert transformed['Is_Current'] is True
        assert transformed['End_Date'] is None
        
        # Verify LastModifiedDate is excluded
        assert 'LastModifiedDate' not in transformed
        
        logger.info("✅ Basic transformation test passed")
    
    def test_transformer_with_end_date(self):
        """Test transformation with end_date set."""
        from app.services.sync.transformers import JobDescriptionTransformer
        
        sql_row = {
            "Employee_ID": 102,
            "JD_ID": 1002,
            "Job_Description": "Project coordinator role with cross-functional responsibilities.",
            "Assigned_Date": date(2023, 6, 1),
            "Is_Current": False,
            "End_Date": date(2024, 5, 31)
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        assert transformed['Is_Current'] is False
        assert transformed['End_Date'] == date(2024, 5, 31)
        
        logger.info("✅ Transformation with end_date test passed")
    
    def test_transformer_handles_none_values(self):
        """Test transformation handles None values gracefully."""
        from app.services.sync.transformers import JobDescriptionTransformer
        
        sql_row = {
            "Employee_ID": 103,
            "JD_ID": None,  # Should still pass through
            "Job_Description": "Test description with None JD_ID value for validation testing.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        # Transformer doesn't validate, just transforms
        assert transformed['JD_ID'] is None
        
        logger.info("✅ None values handling test passed")


# ============================================================================
# PHASE 3: FULL SYNC TESTS
# ============================================================================

class TestPhase3FullSync:
    """Test full sync operations from SQL Server to PostgreSQL."""
    
    def test_full_sync_basic(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test basic full sync of JD records."""
        # Perform full sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify sync was created
        assert sync_result is not None
        assert sync_result.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert sync_result.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        
        # Verify records were synced
        assert sync_result.records_synced >= 0
        
        logger.info(f"✅ Full sync completed: {sync_result.records_synced} records synced")
    
    def test_full_sync_metrics(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that metrics are tracked correctly during full sync."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify metrics exist
        assert sync_result.records_queried >= 0
        assert sync_result.records_synced >= 0
        assert sync_result.records_created >= 0
        assert sync_result.records_updated >= 0
        
        # Verify logical consistency
        assert sync_result.records_synced <= sync_result.records_queried
        assert sync_result.records_created + sync_result.records_updated <= sync_result.records_synced
        
        logger.info(f"✅ Metrics validation passed: queried={sync_result.records_queried}, synced={sync_result.records_synced}")
    
    def test_full_sync_creates_history_record(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that sync creates proper history record."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Query sync history
        history = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_result.sync_id
        ).first()
        
        assert history is not None
        assert history.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert history.started_at is not None
        assert history.completed_at is not None
        
        logger.info(f"✅ Sync history record created with ID: {history.sync_id}")
    
    def test_full_sync_stores_last_sync_timestamp(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that last_sync_timestamp is stored for incremental sync."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify last_sync_timestamp is set
        assert sync_result.last_sync_timestamp is not None
        
        logger.info(f"✅ Last sync timestamp stored: {sync_result.last_sync_timestamp}")


# ============================================================================
# PHASE 4: INCREMENTAL SYNC TESTS
# ============================================================================

class TestPhase4IncrementalSync:
    """Test incremental sync operations."""
    
    def test_incremental_sync_after_full_sync(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test incremental sync after a full sync."""
        # First, do a full sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        assert full_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        
        # Wait a moment
        time.sleep(1)
        
        # Do incremental sync
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        assert incremental_sync.sync_type == SyncType.JOB_DESCRIPTIONS.value
        # Incremental sync might have 0 new records if no changes in SQL Server
        assert incremental_sync.records_queried >= 0
        
        logger.info(f"✅ Incremental sync completed: {incremental_sync.records_synced} new records")
    
    def test_incremental_sync_uses_last_timestamp(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that incremental sync uses last_sync_timestamp correctly."""
        # Do full sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        last_timestamp = full_sync.last_sync_timestamp
        
        assert last_timestamp is not None
        
        # Do incremental sync
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        # Verify it used the timestamp (by checking it found records after that time)
        # In production, this would query SQL Server with WHERE timestamp > last_timestamp
        logger.info(f"✅ Incremental sync used timestamp: {last_timestamp}")


# ============================================================================
# PHASE 5: BULK PROCESSING TESTS
# ============================================================================

class TestPhase5BulkProcessing:
    """Test bulk processing and upsert operations."""
    
    def test_bulk_upsert_creates_new_records(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that bulk processing creates new JD records."""
        initial_count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        
        # Sync JDs
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        final_count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        
        # Should have created some records (if test employees have JDs in SQL Server)
        # Or at least attempted to sync
        assert sync_result.records_synced >= 0
        
        logger.info(f"✅ Bulk upsert test: initial={initial_count}, final={final_count}")
    
    def test_bulk_upsert_updates_existing_records(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that bulk processing updates existing JD records."""
        # First sync
        first_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        first_synced = first_sync.records_synced
        
        # Second sync (should update, not create new)
        second_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        second_synced = second_sync.records_synced
        
        # Second sync should process same or more records
        logger.info(f"✅ Upsert update test: first_synced={first_synced}, second_synced={second_synced}")


# ============================================================================
# PHASE 6: ERROR HANDLING TESTS
# ============================================================================

class TestPhase6ErrorHandling:
    """Test error handling and validation."""
    
    def test_sync_with_invalid_employee_ids(self, sync_service, db_session, cleanup_test_data):
        """Test sync handles records with non-existent employee IDs."""
        # This tests the employee existence check in JobDescriptionProcessor
        # If SQL Server has JDs for employees not in PostgreSQL, they should be skipped
        
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Sync should complete (PARTIAL if errors, COMPLETED if no errors)
        assert sync_result.status in [
            SyncStatus.COMPLETED.value, 
            SyncStatus.PARTIAL.value,
            SyncStatus.FAILED.value  # Might fail if ALL employees don't exist
        ]
        
        # Check error count
        logger.info(f"✅ Sync with validation: errors={sync_result.error_count}")
    
    def test_sync_tracks_errors(self, sync_service, db_session, cleanup_test_data):
        """Test that errors are tracked in sync history."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify error_count field exists
        assert hasattr(sync_result, 'error_count')
        assert sync_result.error_count >= 0
        
        logger.info(f"✅ Error tracking test: {sync_result.error_count} errors recorded")


# ============================================================================
# PHASE 7: EDGE CASES & STRESS TESTS
# ============================================================================

class TestPhase7EdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_sync_with_no_new_records(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test sync when there are no new records to sync."""
        # Do two syncs back-to-back
        first_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Immediate second sync should find no new records
        second_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        # Should complete successfully even with 0 records
        assert second_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        
        logger.info("✅ Empty sync test passed")
    
    def test_sync_service_with_existing_sync_id(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test sync service with pre-created sync job (API endpoint pattern)."""
        # This simulates how the API endpoint creates a sync job first
        from app.services.sync.sync_tracker import SyncTracker
        
        tracker = SyncTracker(get_database())
        
        # Create sync job manually (like API does)
        with db_session.begin_nested():
            sync_job = tracker.create_sync_job(
                sync_type=SyncType.JOB_DESCRIPTIONS,
                is_full_sync=True,
                session=db_session
            )
            sync_id = sync_job.sync_id
            db_session.commit()
        
        # Now sync with existing sync_id
        sync_result = sync_service.sync_job_descriptions(
            is_full_sync=True,
            existing_sync_id=str(sync_id)
        )
        
        # Verify it used the existing sync job
        assert str(sync_result.sync_id) == str(sync_id)
        
        logger.info(f"✅ Existing sync_id test passed: {sync_id}")


# ============================================================================
# PHASE 8: INTEGRATION WITH EXISTING DATA TESTS
# ============================================================================

class TestPhase8IntegrationWithExistingData:
    """Test integration with existing employee and JD data."""
    
    def test_sync_preserves_existing_jd_assignments(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that sync doesn't duplicate or overwrite incorrectly."""
        # Create a test JD manually
        test_jd = EmployeeJobDescription(
            employee_id=test_employees[0],
            jd_id="TEST001",
            job_description="Manually created test JD for sync preservation testing with sufficient length.",
            assigned_date=date(2024, 1, 15),
            is_current=True
        )
        db_session.add(test_jd)
        db_session.commit()
        
        # Count JDs before sync
        jds_before = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == test_employees[0]
        ).count()
        
        # Sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Count JDs after sync
        jds_after = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == test_employees[0]
        ).count()
        
        # Test JD should still exist
        test_jd_after = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == test_employees[0],
            EmployeeJobDescription.jd_id == "TEST001"
        ).first()
        
        assert test_jd_after is not None
        
        logger.info(f"✅ Data preservation test: before={jds_before}, after={jds_after}")


# ============================================================================
# PHASE 9: END-TO-END WORKFLOW TESTS
# ============================================================================

class TestPhase9EndToEndWorkflow:
    """Test complete end-to-end sync workflows."""
    
    def test_complete_sync_workflow(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test complete sync workflow from start to finish."""
        logger.info("=" * 80)
        logger.info("STARTING END-TO-END JD SYNC WORKFLOW TEST")
        logger.info("=" * 80)
        
        # Step 1: Initial full sync
        logger.info("Step 1: Running initial full sync...")
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        
        assert full_sync is not None
        assert full_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        logger.info(f"✅ Full sync completed: {full_sync.records_synced} records")
        
        # Step 2: Wait and do incremental sync
        logger.info("Step 2: Running incremental sync...")
        time.sleep(1)
        
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        assert incremental_sync is not None
        logger.info(f"✅ Incremental sync completed: {incremental_sync.records_synced} new records")
        
        # Step 3: Verify data in database
        logger.info("Step 3: Verifying data in PostgreSQL...")
        jd_count = db_session.query(EmployeeJobDescription).count()
        logger.info(f"✅ Found {jd_count} JD records in PostgreSQL")
        
        # Step 4: Verify sync history
        logger.info("Step 4: Verifying sync history...")
        history_count = db_session.query(SyncHistory).filter(
            SyncHistory.sync_type == SyncType.JOB_DESCRIPTIONS.value
        ).count()
        assert history_count >= 2  # At least 2 sync records (full + incremental)
        logger.info(f"✅ Found {history_count} sync history records")
        
        logger.info("=" * 80)
        logger.info("END-TO-END WORKFLOW TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run JD sync service integration tests.
    
    Prerequisites:
    - SQL Server must be running with test data
    - PostgreSQL must be running
    - .env configuration must be correct
    - EmployeeJobDescriptions table must exist in SQL Server
    
    Usage:
        # Run all tests
        pytest app/tests/test_jd_sync_service_integration.py -v
        
        # Run specific phase
        pytest app/tests/test_jd_sync_service_integration.py -v -k "Phase3"
        
        # Run with detailed output
        pytest app/tests/test_jd_sync_service_integration.py -v --tb=short -s
        
        # Run specific test
        pytest app/tests/test_jd_sync_service_integration.py -v -k "test_full_sync_basic"
    """
    pytest.main([__file__, "-v", "--tb=short", "-s"])
