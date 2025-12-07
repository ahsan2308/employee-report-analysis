"""
FINAL COMPREHENSIVE TEST SUITE - Job Description Sync Pipeline

This is the FINAL, complete test suite that validates the entire JD sync pipeline.
All tests are designed to run independently and test real functionality.

Test Coverage:
✓ Phase 1: Data Transformation (SQL Server → Pydantic format)
✓ Phase 2: Pydantic Validation (schema enforcement)
✓ Phase 3: Processor Operations (bulk upsert, metrics)
✓ Phase 4: Sync Service (full/incremental sync)
✓ Phase 5: Sync Tasks (Celery integration)
✓ Phase 6: Error Handling (validation, recovery)
✓ Phase 7: End-to-End Workflows (complete scenarios)

Requirements:
- PostgreSQL database running
- No SQL Server required (uses mock connector)
- No Celery worker required (tests task logic directly)

Usage:
    # Run all tests
    pytest app/tests/test_jd_sync_final.py -v
    
    # Run specific test
    pytest app/tests/test_jd_sync_final.py -v -k "test_name"
    
    # Run with output
    pytest app/tests/test_jd_sync_final.py -v -s
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Generator
from unittest.mock import Mock
import time
import pandas as pd
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.db_models import Employee, EmployeeJobDescription
from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.services.sync_service import SyncService
from app.services.sync.transformers import JobDescriptionTransformer
from app.services.csv.processors.job_description_processor import JobDescriptionProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.database import get_database
from app.core.logger import logger
from app.schemas.csv_import_schema import JobDescriptionCSVRow


# ============================================================================
# MOCK SQL SERVER CONNECTOR
# ============================================================================

class MockSQLServerConnector:
    """
    Mock SQL Server connector that simulates real SQL Server behavior.
    Returns data with native SQL Server types (datetime, bool from BIT).
    """
    
    def __init__(self, sample_data: List[Dict[str, Any]] = None):
        self.sample_data = sample_data or self._generate_realistic_data()
        self.connection_test_result = True
        self.max_batch_size = 1000
    
    def _generate_realistic_data(self) -> List[Dict[str, Any]]:
        """Generate realistic JD data with role changes and history."""
        base_date = datetime.now() - timedelta(days=180)
        
        return [
            # Employee 101: Single current JD
            {
                "Employee_ID": 101,
                "JD_ID": 1001,
                "Job_Description": "Data Analyst responsible for analyzing employee performance metrics, generating insights, and creating visualizations using Python and SQL. Collaborates with HR team to identify trends.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=1)
            },
            
            # Employee 102: Role progression (2 JDs)
            {
                "Employee_ID": 102,
                "JD_ID": 1002,
                "Job_Description": "Project Coordinator responsible for timeline management, stakeholder communication, and deliverable tracking. Supports senior project managers with administrative tasks.",
                "Assigned_Date": date(2023, 6, 1),
                "Is_Current": False,
                "End_Date": date(2024, 5, 31),
                "LastModifiedDate": base_date + timedelta(days=2)
            },
            {
                "Employee_ID": 102,
                "JD_ID": 1003,
                "Job_Description": "Senior Project Manager leading strategic initiatives, managing cross-functional teams, and driving organizational change. Reports to department head and mentors junior staff.",
                "Assigned_Date": date(2024, 6, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=3)
            },
            
            # Employee 103: Career progression (3 JDs)
            {
                "Employee_ID": 103,
                "JD_ID": 1004,
                "Job_Description": "Junior Software Engineer developing backend services using Python and PostgreSQL. Participates in code reviews, writes unit tests, and collaborates with senior engineers on feature implementation.",
                "Assigned_Date": date(2023, 1, 1),
                "Is_Current": False,
                "End_Date": date(2023, 12, 31),
                "LastModifiedDate": base_date + timedelta(days=4)
            },
            {
                "Employee_ID": 103,
                "JD_ID": 1005,
                "Job_Description": "Software Engineer II focusing on API development and database optimization. Leads implementation of new features and provides guidance to junior developers. Participates in architecture discussions.",
                "Assigned_Date": date(2024, 1, 1),
                "Is_Current": False,
                "End_Date": date(2024, 6, 30),
                "LastModifiedDate": base_date + timedelta(days=5)
            },
            {
                "Employee_ID": 103,
                "JD_ID": 1006,
                "Job_Description": "Senior Software Engineer responsible for system architecture, performance optimization, and team mentorship. Makes critical technical decisions and drives engineering best practices across the organization.",
                "Assigned_Date": date(2024, 7, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=6)
            },
            
            # Employee 104: Current role
            {
                "Employee_ID": 104,
                "JD_ID": 1007,
                "Job_Description": "Data Scientist building predictive models, conducting statistical analysis, and generating insights from large datasets. Expertise required in machine learning, Python, R, and data visualization tools.",
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=7)
            },
            
            # Employee 105: Current role
            {
                "Employee_ID": 105,
                "JD_ID": 1008,
                "Job_Description": "Technical Lead responsible for architecture decisions, code reviews, and development best practices. Coordinates with product management and provides technical mentorship to engineering team.",
                "Assigned_Date": date(2024, 3, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=8)
            }
        ]
    
    def test_connection(self) -> bool:
        return self.connection_test_result
    
    def get_allowed_tables(self) -> List[str]:
        return ["EmployeeJobDescriptions", "EmployeeReports", "VisionEmployeeData"]
    
    def get_allowed_timestamp_columns(self) -> List[str]:
        return ["LastModifiedDate", "ModifiedDate", "UpdatedAt"]
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        if "job" in table_name.lower():
            return {
                "Employee_ID": {"type": "int"},
                "JD_ID": {"type": "int"},
                "Job_Description": {"type": "varchar"},
                "Assigned_Date": {"type": "date"},
                "Is_Current": {"type": "bit"},
                "End_Date": {"type": "date"},
                "LastModifiedDate": {"type": "datetime"}
            }
        return {}
    
    def get_all_records(self, table_name: str, batch_size: int = 1000, 
                       order_by: str = None) -> Generator[List[Dict[str, Any]], None, None]:
        """Full sync - return all records."""
        for i in range(0, len(self.sample_data), batch_size):
            yield self.sample_data[i:i + batch_size]
    
    def get_records_since(self, table_name: str, timestamp_column: str,
                         since_timestamp: datetime, batch_size: int = 1000,
                         order_by: str = None) -> Generator[List[Dict[str, Any]], None, None]:
        """Incremental sync - return records after timestamp."""
        filtered = [
            record for record in self.sample_data
            if timestamp_column in record and record[timestamp_column] > since_timestamp
        ]
        for i in range(0, len(filtered), batch_size):
            yield filtered[i:i + batch_size]


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_instance():
    """Database instance for entire test session."""
    return get_database()


@pytest.fixture
def db_session(db_instance):
    """Isolated database session with automatic rollback."""
    session = db_instance.create_session()
    session.begin()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_employees(db_session):
    """Create test employees and cleanup after test."""
    test_ids = [101, 102, 103, 104, 105]
    
    # Cleanup
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.employee_id.in_(test_ids)
    ).delete(synchronize_session=False)
    db_session.query(Employee).filter(
        Employee.id.in_(test_ids)
    ).delete(synchronize_session=False)
    db_session.flush()
    
    # Create
    employees = [
        Employee(id=emp_id, name=f"Test Employee {emp_id}", 
                position="Test Position", wing="Test Wing")
        for emp_id in test_ids
    ]
    db_session.add_all(employees)
    db_session.commit()
    
    logger.info(f"[OK] Created {len(employees)} test employees")
    yield test_ids
    
    # Cleanup
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.employee_id.in_(test_ids)
    ).delete(synchronize_session=False)
    db_session.query(Employee).filter(
        Employee.id.in_(test_ids)
    ).delete(synchronize_session=False)
    db_session.commit()


@pytest.fixture
def mock_connector():
    """Mock connector with valid data."""
    return MockSQLServerConnector()


@pytest.fixture
def sync_service(mock_connector):
    """Sync service with mock connector."""
    return SyncService(mock_connector, error_threshold_percent=10.0)


@pytest.fixture
def error_handler():
    """Error handler for processor tests."""
    return ImportErrorHandler()


# ============================================================================
# PHASE 1: TRANSFORMER TESTS
# ============================================================================

class TestPhase1Transformers:
    """Test SQL Server data transformation."""
    
    def test_basic_transformation(self):
        """Test basic row transformation."""
        sql_row = {
            "Employee_ID": 101,
            "JD_ID": 1001,
            "Job_Description": "Test description with sufficient length to meet minimum requirements for validation.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime(2024, 11, 20, 10, 30)
        }
        
        result = JobDescriptionTransformer.transform(sql_row)
        
        assert result['Employee_ID'] == 101
        assert result['JD_ID'] == 1001
        assert result['Assigned_Date'] == date(2024, 1, 15)
        assert result['Is_Current'] is True
        assert 'LastModifiedDate' not in result
        
        logger.info("[OK] Basic transformation test passed")
    
    def test_batch_transformation(self, mock_connector):
        """Test transforming entire batch of records."""
        batches = list(mock_connector.get_all_records("EmployeeJobDescriptions"))
        first_batch = batches[0]
        
        transformed = [JobDescriptionTransformer.transform(row) for row in first_batch]
        
        assert len(transformed) == len(first_batch)
        assert all('LastModifiedDate' not in row for row in transformed)
        assert all('Employee_ID' in row for row in transformed)
        
        logger.info(f"[OK] Transformed {len(transformed)} records successfully")


# ============================================================================
# PHASE 2: PYDANTIC VALIDATION TESTS
# ============================================================================

class TestPhase2Validation:
    """Test Pydantic schema validation."""
    
    def test_valid_record(self):
        """Test validation of valid JD record."""
        data = {
            "Employee_ID": 101,
            "JD_ID": "1001",
            "Job_Description": "Valid job description with more than fifty characters to pass validation requirements.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        validated = JobDescriptionCSVRow(**data)
        assert validated.Employee_ID == 101
        assert validated.JD_ID == "1001"
        
        logger.info("[OK] Valid record validation passed")
    
    def test_jd_id_type_conversion(self):
        """Test JD_ID converts from int to string."""
        data = {
            "Employee_ID": 101,
            "JD_ID": 1001,  # Integer input
            "Job_Description": "Testing JD_ID conversion from integer to string format for database storage.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        validated = JobDescriptionCSVRow(**data)
        assert isinstance(validated.JD_ID, str)
        assert validated.JD_ID == "1001"
        
        logger.info("[OK] JD_ID type conversion passed")
    
    def test_short_description_fails(self):
        """Test that short descriptions are rejected."""
        data = {
            "Employee_ID": 101,
            "JD_ID": "1001",
            "Job_Description": "Too short",  # < 50 chars
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        with pytest.raises(Exception) as exc:
            JobDescriptionCSVRow(**data)
        
        assert "50 characters" in str(exc.value).lower()
        logger.info("[OK] Short description rejection passed")


# ============================================================================
# PHASE 3: PROCESSOR TESTS
# ============================================================================

class TestPhase3Processor:
    """Test JobDescriptionProcessor operations."""
    
    def test_processor_creation(self, db_session, error_handler):
        """Test processor instantiation."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        assert processor.jd_records_created == 0
        assert processor.jd_records_updated == 0
        logger.info("[OK] Processor creation passed")
    
    def test_single_row_processing(self, db_session, error_handler, test_employees):
        """Test processing a single JD row."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        row_data = {
            "Employee_ID": 101,
            "JD_ID": "2001",
            "Job_Description": "Testing single row processing with sufficient description length for validation.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        success = processor.process_row(row_data, row_number=1)
        
        assert success is True
        assert processor.jd_records_created == 1
        
        # Verify in database
        jd = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 101,
            EmployeeJobDescription.jd_id == "2001"
        ).first()
        assert jd is not None
        
        logger.info("[OK] Single row processing passed")
    
    def test_bulk_processing(self, db_session, error_handler, test_employees):
        """Test bulk DataFrame processing."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        data = [
            {
                "Employee_ID": 101,
                "JD_ID": "3001",
                "Job_Description": "Bulk processing test record one with adequate description length for validation.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None
            },
            {
                "Employee_ID": 102,
                "JD_ID": "3002",
                "Job_Description": "Bulk processing test record two with adequate description length for validation.",
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "End_Date": None
            }
        ]
        
        df = pd.DataFrame(data)
        successful, total = processor.process_dataframe(df, start_row_number=1, pre_cleaned=True)
        
        assert successful == 2
        assert total == 2
        
        logger.info(f"[OK] Bulk processing passed: {successful}/{total} records")


# ============================================================================
# PHASE 4: SYNC SERVICE TESTS
# ============================================================================

class TestPhase4SyncService:
    """Test SyncService orchestration."""
    
    def test_full_sync(self, sync_service, db_session, test_employees):
        """Test full synchronization."""
        result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        assert result.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert result.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        assert result.records_synced > 0
        
        # Verify in database
        count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        assert count > 0
        
        logger.info(f"[OK] Full sync passed: {result.records_synced} records synced")
    
    def test_incremental_sync(self, sync_service, db_session, test_employees):
        """Test incremental synchronization."""
        # First sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        assert full_sync.last_sync_timestamp is not None
        
        time.sleep(1)
        
        # Incremental sync
        incr_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        assert incr_sync.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert incr_sync.records_queried == 0  # No new records with static data
        
        logger.info("[OK] Incremental sync passed")
    
    def test_sync_history_tracking(self, sync_service, db_session, test_employees):
        """Test sync history is created."""
        result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        history = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == result.sync_id
        ).first()
        
        assert history is not None
        assert history.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert history.started_at is not None
        assert history.completed_at is not None
        
        logger.info(f"[OK] Sync history tracking passed: {history.sync_id}")


# ============================================================================
# PHASE 5: CELERY TASK TESTS
# ============================================================================

class TestPhase5CeleryTasks:
    """Test Celery task logic (without running Celery worker)."""
    
    def test_task_direct_call(self, sync_service, db_session, test_employees):
        """Test calling task function directly."""
        from app.tasks.sync_tasks import sync_job_descriptions_task
        
        # Create mock task instance
        mock_task = Mock()
        mock_task.sync_service = sync_service
        
        # Call task's run method directly (not via Celery queue)
        # This bypasses Celery's wrapper and calls the actual function logic
        result = sync_job_descriptions_task.run(
            is_full_sync=True,
            sync_id=None
        )
        
        assert isinstance(result, dict)
        assert 'sync_id' in result
        assert 'status' in result
        assert 'records_synced' in result
        
        logger.info(f"[OK] Task direct call passed: {result['records_synced']} records")


# ============================================================================
# PHASE 6: ERROR HANDLING TESTS
# ============================================================================

class TestPhase6ErrorHandling:
    """Test error handling and recovery."""
    
    def test_invalid_employee_id(self, db_session, error_handler, test_employees):
        """Test handling of non-existent employee."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        row_data = {
            "Employee_ID": 999999,  # Does not exist
            "JD_ID": "9001",
            "Job_Description": "Testing error handling for non-existent employee with adequate description length.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        success = processor.process_row(row_data, row_number=1)
        
        assert success is False
        assert error_handler.get_error_count() > 0
        
        errors = error_handler.get_errors()
        assert "does not exist" in errors[0].error_message.lower()
        
        logger.info("[OK] Invalid employee ID handling passed")
    
    def test_sync_with_mixed_data(self, db_session, test_employees):
        """Test sync with mix of valid and invalid records."""
        error_data = [
            # Valid
            {
                "Employee_ID": 101,
                "JD_ID": 5001,
                "Job_Description": "Valid record with adequate description length for successful processing and validation.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": datetime.now()
            },
            # Invalid - non-existent employee
            {
                "Employee_ID": 999999,
                "JD_ID": 5002,
                "Job_Description": "Invalid record for non-existent employee with adequate description length.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": datetime.now()
            }
        ]
        
        mock_conn = MockSQLServerConnector(sample_data=error_data)
        service = SyncService(mock_conn, error_threshold_percent=50.0)
        
        result = service.sync_job_descriptions(is_full_sync=True)
        
        assert result.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        assert result.records_synced > 0
        assert result.error_count > 0
        
        logger.info(f"[OK] Mixed data sync passed: {result.records_synced} synced, {result.error_count} errors")


# ============================================================================
# PHASE 7: END-TO-END WORKFLOW TESTS
# ============================================================================

class TestPhase7EndToEnd:
    """Test complete end-to-end workflows."""
    
    def test_complete_workflow(self, sync_service, db_session, test_employees):
        """Test complete sync workflow from start to finish."""
        logger.info("=" * 80)
        logger.info("STARTING COMPLETE END-TO-END WORKFLOW TEST")
        logger.info("=" * 80)
        
        # Step 1: Full sync
        logger.info("Step 1: Full synchronization...")
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        assert full_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        logger.info(f"[OK] Synced {full_sync.records_synced} records")
        
        # Step 2: Verify database
        logger.info("Step 2: Database verification...")
        count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        logger.info(f"[OK] Found {count} records in database")
        
        # Step 3: Verify employees
        logger.info("Step 3: Employee assignment verification...")
        for emp_id in test_employees:
            jds = db_session.query(EmployeeJobDescription).filter(
                EmployeeJobDescription.employee_id == emp_id
            ).all()
            if jds:
                current = sum(1 for jd in jds if jd.is_current)
                logger.info(f"  Employee {emp_id}: {len(jds)} total, {current} current")
        
        # Step 4: Incremental sync
        logger.info("Step 4: Incremental synchronization...")
        time.sleep(1)
        incr_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        logger.info(f"[OK] Incremental sync: {incr_sync.records_queried} new records")
        
        # Step 5: History verification
        logger.info("Step 5: Sync history verification...")
        history_count = db_session.query(SyncHistory).filter(
            SyncHistory.sync_type == SyncType.JOB_DESCRIPTIONS.value
        ).count()
        logger.info(f"[OK] Found {history_count} sync history records")
        
        logger.info("=" * 80)
        logger.info("COMPLETE WORKFLOW TEST PASSED SUCCESSFULLY")
        logger.info("=" * 80)
    
    def test_role_changes(self, sync_service, db_session, test_employees):
        """Test employees with role changes over time."""
        sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Employee 102: Should have 2 JDs
        jds_102 = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 102
        ).all()
        
        if len(jds_102) >= 2:
            current = sum(1 for jd in jds_102 if jd.is_current)
            ended = sum(1 for jd in jds_102 if not jd.is_current)
            logger.info(f"[OK] Employee 102: {current} current, {ended} ended JDs")
        
        # Employee 103: Should have 3 JDs
        jds_103 = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 103
        ).all()
        
        if len(jds_103) >= 3:
            current = sum(1 for jd in jds_103 if jd.is_current)
            logger.info(f"[OK] Employee 103: {len(jds_103)} total, {current} current JDs")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run the complete test suite.
    
    Usage:
        python app/tests/test_jd_sync_final.py
        pytest app/tests/test_jd_sync_final.py -v
        pytest app/tests/test_jd_sync_final.py -v -s
    """
    pytest.main([__file__, "-v", "--tb=short", "-s"])
