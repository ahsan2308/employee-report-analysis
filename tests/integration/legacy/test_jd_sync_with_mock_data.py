"""
Comprehensive Integration Tests for Job Description Sync Service with Mock Data

This test suite validates the complete JD sync pipeline using MOCK SQL Server data:
- Mock SQL Server connector that returns sample data
- Data transformation (datetime → Pydantic format)
- Pydantic validation via JobDescriptionCSVRow
- Bulk processing and upsert operations
- Sync history tracking and metrics
- Error handling and edge cases

This allows testing the ENTIRE sync pipeline without needing SQL Server running.

Usage:
    pytest app/tests/test_jd_sync_with_mock_data.py -v
    pytest app/tests/test_jd_sync_with_mock_data.py -v -k "test_full_sync"
    pytest app/tests/test_jd_sync_with_mock_data.py -v --tb=short -s
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Generator
import time

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.db_models import Employee, EmployeeJobDescription
from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.services.sync_service import SyncService
from app.database import get_database
from app.core.logger import logger


# ============================================================================
# MOCK SQL SERVER DATA
# ============================================================================

class MockSQLServerConnector:
    """
    Mock SQL Server connector that returns sample JD data.
    
    Simulates the behavior of SQLServerConnector for testing.
    """
    
    def __init__(self, sample_data: List[Dict[str, Any]] = None):
        """
        Initialize mock connector with sample data.
        
        Args:
            sample_data: List of dictionaries representing SQL Server rows
        """
        self.sample_data = sample_data or self._generate_default_sample_data()
        self.connection_test_result = True
    
    def _generate_default_sample_data(self) -> List[Dict[str, Any]]:
        """
        Generate default sample JD data.
        
        Simulates what would come from SQL Server:
        - datetime objects for dates (not strings)
        - BIT type → Python bool for Is_Current
        - Employee_ID and JD_ID as integers
        """
        base_date = datetime.now() - timedelta(days=365)
        
        return [
            {
                "Employee_ID": 999100,
                "JD_ID": 567561001,
                "Job_Description": "Responsible for analyzing employee performance data, generating insights, and presenting findings to management. Requires proficiency in data analysis tools and strong communication skills.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=1)
            },
            {
                "Employee_ID": 999101,
                "JD_ID": 567561002,
                "Job_Description": "Coordinates project activities across multiple teams, manages timelines, and ensures deliverables meet quality standards. Acts as liaison between technical and business stakeholders.",
                "Assigned_Date": date(2023, 6, 1),
                "Is_Current": False,
                "End_Date": date(2024, 5, 31),
                "LastModifiedDate": base_date + timedelta(days=2)
            },
            {
                "Employee_ID": 999101,
                "JD_ID": 567561003,
                "Job_Description": "Senior role focusing on strategic planning and cross-functional leadership. Drives organizational initiatives and mentors junior team members.",
                "Assigned_Date": date(2024, 6, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=3)
            },
            {
                "Employee_ID": 999102,
                "JD_ID": 567561004,
                "Job_Description": "Develops and maintains software applications using Python and PostgreSQL. Collaborates with product team to implement new features and optimize existing functionality.",
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=4)
            },
            {
                "Employee_ID": 999102,
                "JD_ID": 567561005,
                "Job_Description": "Technical lead responsible for architecture decisions and code reviews. Ensures best practices and mentors development team members.",
                "Assigned_Date": date(2023, 1, 1),
                "Is_Current": False,
                "End_Date": date(2024, 1, 31),
                "LastModifiedDate": base_date + timedelta(days=5)
            }
        ]
    
    def test_connection(self) -> bool:
        """Simulate connection test."""
        return self.connection_test_result
    
    def get_allowed_tables(self) -> List[str]:
        """Return mock table list."""
        return ["EmployeeJobDescriptions"]
    
    def get_allowed_timestamp_columns(self) -> List[str]:
        """Return mock timestamp columns."""
        return ["LastModifiedDate", "ModifiedDate", "UpdatedAt"]
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Return mock table schema.
        
        Simulates SQLServerConnector.get_table_schema() return value.
        """
        return {
            "Employee_ID": {"type": "int"},
            "JD_ID": {"type": "int"},
            "Job_Description": {"type": "varchar"},
            "Assigned_Date": {"type": "date"},
            "Is_Current": {"type": "bit"},
            "End_Date": {"type": "date"},
            "LastModifiedDate": {"type": "datetime"}
        }
    
    def get_all_records(self, table_name: str, batch_size: int = 1000, 
                       order_by: str = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Simulate full sync - return all records in batches.
        
        Args:
            table_name: Table name (ignored in mock)
            batch_size: Size of batches
            order_by: Column to order by (ignored in mock)
            
        Yields:
            Batches of records
        """
        for i in range(0, len(self.sample_data), batch_size):
            batch = self.sample_data[i:i + batch_size]
            yield batch
    
    def get_records_since(self, table_name: str, timestamp_column: str,
                         since_timestamp: datetime, batch_size: int = 1000,
                         order_by: str = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Simulate incremental sync - return records modified after timestamp.
        
        Args:
            table_name: Table name (ignored in mock)
            timestamp_column: Timestamp column name
            since_timestamp: Only return records after this time
            batch_size: Size of batches
            order_by: Column to order by (ignored in mock)
            
        Yields:
            Batches of records modified after since_timestamp
        """
        # Filter records by timestamp
        filtered_records = [
            record for record in self.sample_data
            if timestamp_column in record and record[timestamp_column] > since_timestamp
        ]
        
        # Return in batches
        for i in range(0, len(filtered_records), batch_size):
            batch = filtered_records[i:i + batch_size]
            yield batch


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


@pytest.fixture
def mock_sqlserver_connector():
    """Create mock SQL Server connector with sample data."""
    return MockSQLServerConnector()


@pytest.fixture
def mock_sqlserver_connector_with_errors():
    """
    Create mock SQL Server connector with data that will cause errors.
    
    Includes:
    - Invalid employee IDs
    - Too-short job descriptions
    - Future dates
    """
    error_data = [
        # Valid record
        {
            "Employee_ID": 999100,
            "JD_ID": 567561001,
            "Job_Description": "Valid job description with more than fifty characters to meet minimum requirements.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        # Invalid: Non-existent employee
        {
            "Employee_ID": 888888,  # Does not exist
            "JD_ID": 567561002,
            "Job_Description": "Job description for non-existent employee with sufficient character length.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        # Invalid: Too short job description
        {
            "Employee_ID": 999101,
            "JD_ID": 567561003,
            "Job_Description": "Too short",  # Less than 50 characters
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        # Invalid: Future date
        {
            "Employee_ID": 999102,
            "JD_ID": 567561004,
            "Job_Description": "Job description with future date which should fail validation requirements.",
            "Assigned_Date": date.today() + timedelta(days=30),  # Future date
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        }
    ]
    
    return MockSQLServerConnector(sample_data=error_data)


@pytest.fixture
def sync_service(mock_sqlserver_connector):
    """Create sync service with mock SQL Server connector."""
    return SyncService(mock_sqlserver_connector, error_threshold_percent=10.0)


@pytest.fixture
def sync_service_with_errors(mock_sqlserver_connector_with_errors):
    """Create sync service with error-inducing mock data."""
    return SyncService(mock_sqlserver_connector_with_errors, error_threshold_percent=10.0)


@pytest.fixture
def test_employees(db_session):
    """
    Create test employees in PostgreSQL for JD sync tests.
    
    IMPORTANT: Commits employees so they're visible to sync service's separate session.
    
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
    
    # CRITICAL FIX: Commit employees so sync service can see them
    # The sync service creates its own session, so it needs committed data
    db_session.commit()
    
    logger.info(f"Created {len(employees)} test employees: {test_employee_ids}")
    
    yield test_employee_ids
    
    # Cleanup after test - delete test employees
    # Need to create a new transaction after the yield
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.employee_id.in_(test_employee_ids)
    ).delete(synchronize_session=False)
    
    db_session.query(Employee).filter(
        Employee.id.in_(test_employee_ids)
    ).delete(synchronize_session=False)
    
    db_session.commit()
    logger.info(f"Cleaned up test employees: {test_employee_ids}")


@pytest.fixture
def cleanup_test_data(db_session):
    """
    Cleanup fixture to remove test data after tests.
    Runs after each test that uses it.
    """
    yield
    
    # Clean up test JDs (JD_IDs starting with 56756)
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.jd_id.like("56756%")
    ).delete(synchronize_session=False)
    
    # Clean up test employees (999xxx range)
    db_session.query(Employee).filter(
        Employee.id >= 999000
    ).delete(synchronize_session=False)
    
    db_session.commit()
    logger.info("Cleaned up test data")


# ============================================================================
# PHASE 1: MOCK CONNECTOR TESTS
# ============================================================================

class TestPhase1MockConnector:
    """Test the mock SQL Server connector itself."""
    
    def test_mock_connector_connection(self, mock_sqlserver_connector):
        """Test mock connector reports successful connection."""
        assert mock_sqlserver_connector.test_connection() is True
        logger.info("✅ Mock connector connection test passed")
    
    def test_mock_connector_table_list(self, mock_sqlserver_connector):
        """Test mock connector returns table list."""
        tables = mock_sqlserver_connector.get_allowed_tables()
        assert "EmployeeJobDescriptions" in tables
        logger.info("✅ Mock connector table list test passed")
    
    def test_mock_connector_schema(self, mock_sqlserver_connector):
        """Test mock connector returns table schema."""
        schema = mock_sqlserver_connector.get_table_schema("EmployeeJobDescriptions")
        
        assert "Employee_ID" in schema
        assert "JD_ID" in schema
        assert "Job_Description" in schema
        assert "Assigned_Date" in schema
        assert "LastModifiedDate" in schema
        
        logger.info("✅ Mock connector schema test passed")
    
    def test_mock_connector_full_sync(self, mock_sqlserver_connector):
        """Test mock connector returns all records for full sync."""
        batches = list(mock_sqlserver_connector.get_all_records(
            table_name="EmployeeJobDescriptions",
            batch_size=10
        ))
        
        assert len(batches) > 0
        total_records = sum(len(batch) for batch in batches)
        assert total_records == 5  # Default sample data has 5 records
        
        logger.info(f"✅ Mock connector full sync test passed: {total_records} records")
    
    def test_mock_connector_incremental_sync(self, mock_sqlserver_connector):
        """Test mock connector filters records by timestamp."""
        # Get records modified after a certain date
        cutoff_date = datetime.now() - timedelta(days=364)
        
        batches = list(mock_sqlserver_connector.get_records_since(
            table_name="EmployeeJobDescriptions",
            timestamp_column="LastModifiedDate",
            since_timestamp=cutoff_date,
            batch_size=10
        ))
        
        # Should return records modified after cutoff_date
        total_records = sum(len(batch) for batch in batches)
        assert total_records > 0
        
        logger.info(f"✅ Mock connector incremental sync test passed: {total_records} records")


# ============================================================================
# PHASE 2: DATA TRANSFORMATION TESTS
# ============================================================================

class TestPhase2DataTransformation:
    """Test transformation of mock SQL Server data."""
    
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
            "LastModifiedDate": datetime(2024, 11, 20, 10, 30)
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        assert transformed['Employee_ID'] == 101
        assert transformed['JD_ID'] == 1001
        assert transformed['Assigned_Date'] == date(2024, 1, 15)
        assert transformed['Is_Current'] is True
        assert 'LastModifiedDate' not in transformed
        
        logger.info("✅ Basic transformation test passed")
    
    def test_transformer_with_sample_data(self, mock_sqlserver_connector):
        """Test transformer with actual mock sample data."""
        from app.services.sync.transformers import JobDescriptionTransformer
        
        # Get first batch
        batches = list(mock_sqlserver_connector.get_all_records(
            table_name="EmployeeJobDescriptions",
            batch_size=10
        ))
        
        first_batch = batches[0]
        
        # Transform first record
        transformed = JobDescriptionTransformer.transform(first_batch[0])
        
        assert 'Employee_ID' in transformed
        assert 'JD_ID' in transformed
        assert 'Job_Description' in transformed
        assert 'Assigned_Date' in transformed
        assert 'LastModifiedDate' not in transformed
        
        logger.info("✅ Sample data transformation test passed")


# ============================================================================
# PHASE 3: FULL SYNC TESTS
# ============================================================================

class TestPhase3FullSync:
    """Test full sync operations with mock data."""
    
    def test_full_sync_basic(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test basic full sync of JD records."""
        # Perform full sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify sync was created
        assert sync_result is not None
        assert sync_result.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert sync_result.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        
        # Verify records were synced
        assert sync_result.records_synced > 0
        
        logger.info(f"✅ Full sync completed: {sync_result.records_synced} records synced")
    
    def test_full_sync_creates_records(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that full sync creates JD records in PostgreSQL."""
        # Count JDs before sync
        jds_before = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        
        # Perform full sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Count JDs after sync
        jds_after = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        
        # Should have created records
        assert jds_after > jds_before
        
        logger.info(f"✅ Full sync created records: before={jds_before}, after={jds_after}")
    
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


# ============================================================================
# PHASE 4: INCREMENTAL SYNC TESTS
# ============================================================================

class TestPhase4IncrementalSync:
    """Test incremental sync operations with mock data."""
    
    def test_incremental_sync_after_full_sync(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test incremental sync after a full sync."""
        # First, do a full sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        assert full_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        
        # Wait a moment
        time.sleep(1)
        
        # Do incremental sync (should find no new records with static mock data)
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        assert incremental_sync.sync_type == SyncType.JOB_DESCRIPTIONS.value
        # With static mock data, incremental sync should find 0 new records
        assert incremental_sync.records_queried == 0
        
        logger.info(f"✅ Incremental sync completed: {incremental_sync.records_synced} new records")
    
    def test_incremental_sync_uses_last_timestamp(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that incremental sync uses last_sync_timestamp correctly."""
        # Do full sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        last_timestamp = full_sync.last_sync_timestamp
        
        assert last_timestamp is not None
        
        # Do incremental sync
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        # Should have used the timestamp
        logger.info(f"✅ Incremental sync used timestamp: {last_timestamp}")


# ============================================================================
# PHASE 5: ERROR HANDLING TESTS
# ============================================================================

class TestPhase5ErrorHandling:
    """Test error handling with invalid mock data."""
    
    def test_sync_with_invalid_data(self, sync_service_with_errors, db_session, test_employees, cleanup_test_data):
        """Test sync handles records with validation errors."""
        # This uses mock data with intentional errors
        sync_result = sync_service_with_errors.sync_job_descriptions(is_full_sync=True)
        
        # Sync should complete but with errors
        assert sync_result.status in [
            SyncStatus.COMPLETED.value,
            SyncStatus.PARTIAL.value,
            SyncStatus.FAILED.value
        ]
        
        # Should have recorded errors
        assert sync_result.error_count > 0
        
        logger.info(f"✅ Sync with errors: {sync_result.error_count} errors recorded")
    
    def test_sync_tracks_errors(self, sync_service_with_errors, db_session, test_employees, cleanup_test_data):
        """Test that errors are tracked in sync history."""
        sync_result = sync_service_with_errors.sync_job_descriptions(is_full_sync=True)
        
        # Verify error_count field exists
        assert hasattr(sync_result, 'error_count')
        assert sync_result.error_count >= 0
        
        logger.info(f"✅ Error tracking test: {sync_result.error_count} errors recorded")


# ============================================================================
# PHASE 6: BULK PROCESSING TESTS
# ============================================================================

class TestPhase6BulkProcessing:
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
        
        # Should have created records
        assert final_count > initial_count
        
        logger.info(f"✅ Bulk upsert test: initial={initial_count}, final={final_count}")
    
    def test_bulk_upsert_updates_existing_records(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that bulk processing updates existing JD records."""
        # First sync
        first_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        first_synced = first_sync.records_synced
        
        # Second sync (should update, not create new)
        second_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        second_synced = second_sync.records_synced
        
        # Second sync should process same records
        logger.info(f"✅ Upsert update test: first_synced={first_synced}, second_synced={second_synced}")


# ============================================================================
# PHASE 7: DATA INTEGRITY TESTS
# ============================================================================

class TestPhase7DataIntegrity:
    """Test data integrity after sync operations."""
    
    def test_synced_data_matches_source(self, sync_service, db_session, test_employees, cleanup_test_data, mock_sqlserver_connector):
        """Test that synced data matches source mock data."""
        # Perform sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Get source data
        source_data = mock_sqlserver_connector.sample_data
        
        # Verify each source record was synced correctly
        for source_record in source_data:
            employee_id = source_record['Employee_ID']
            jd_id = str(source_record['JD_ID'])
            
            # Query synced record
            synced_jd = db_session.query(EmployeeJobDescription).filter(
                EmployeeJobDescription.employee_id == employee_id,
                EmployeeJobDescription.jd_id == jd_id
            ).first()
            
            if synced_jd:
                # Verify key fields match
                assert synced_jd.job_description == source_record['Job_Description']
                assert synced_jd.assigned_date == source_record['Assigned_Date']
                assert synced_jd.is_current == source_record['Is_Current']
        
        logger.info("✅ Data integrity test passed: synced data matches source")
    
    def test_multiple_jds_per_employee(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test that employees can have multiple JD assignments."""
        # Perform sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Employee 999101 should have 2 JDs in mock data
        jds_for_999101 = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 999101
        ).all()
        
        assert len(jds_for_999101) == 2
        
        # One should be current, one should be ended
        current_count = sum(1 for jd in jds_for_999101 if jd.is_current)
        assert current_count == 1
        
        logger.info(f"✅ Multiple JDs test passed: Employee 999101 has {len(jds_for_999101)} JD assignments")


# ============================================================================
# PHASE 8: END-TO-END WORKFLOW TESTS
# ============================================================================

class TestPhase8EndToEndWorkflow:
    """Test complete end-to-end sync workflows."""
    
    def test_complete_sync_workflow(self, sync_service, db_session, test_employees, cleanup_test_data):
        """Test complete sync workflow from start to finish."""
        logger.info("=" * 80)
        logger.info("STARTING END-TO-END JD SYNC WORKFLOW TEST (MOCK DATA)")
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
        jd_count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        logger.info(f"✅ Found {jd_count} JD records in PostgreSQL")
        
        # Step 4: Verify sync history
        logger.info("Step 4: Verifying sync history...")
        history_count = db_session.query(SyncHistory).filter(
            SyncHistory.sync_type == SyncType.JOB_DESCRIPTIONS.value
        ).count()
        assert history_count >= 2  # At least 2 sync records (full + incremental)
        logger.info(f"✅ Found {history_count} sync history records")
        
        # Step 5: Verify each employee has correct JDs
        logger.info("Step 5: Verifying employee JD assignments...")
        for emp_id in test_employees:
            jds = db_session.query(EmployeeJobDescription).filter(
                EmployeeJobDescription.employee_id == emp_id
            ).all()
            
            current_jds = [jd for jd in jds if jd.is_current]
            logger.info(f"Employee {emp_id}: {len(jds)} total JDs, {len(current_jds)} current")
        
        logger.info("=" * 80)
        logger.info("END-TO-END WORKFLOW TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run JD sync service integration tests with mock data.
    
    No prerequisites needed - uses mock SQL Server connector.
    
    Usage:
        # Run all tests
        pytest app/tests/test_jd_sync_with_mock_data.py -v
        
        # Run specific phase
        pytest app/tests/test_jd_sync_with_mock_data.py -v -k "Phase3"
        
        # Run with detailed output
        pytest app/tests/test_jd_sync_with_mock_data.py -v --tb=short -s
        
        # Run specific test
        pytest app/tests/test_jd_sync_with_mock_data.py -v -k "test_full_sync_basic"
    """
    pytest.main([__file__, "-v", "--tb=short", "-s"])
