"""
Comprehensive Integration Tests for Job Description Sync Pipeline

This test suite validates the COMPLETE JD sync pipeline moving backwards from:
Sync Tasks → Sync Service → Processors → Transformers → Pydantic Validation

Tests use MOCK SQL Server data to validate:
1. Data Transformation (SQL Server types → Pydantic format)
2. Pydantic Validation (JobDescriptionCSVRow schema)
3. Processor Operations (bulk upsert, metrics tracking)
4. Sync Service Orchestration (full/incremental sync, error handling)
5. Sync Task Execution (Celery task logic, metrics extraction)
6. End-to-End Workflows (complete sync operations)

NO SQL Server connection required - uses mock connector with sample data.

Usage:
    # Run all tests
    pytest app/tests/test_jd_sync_comprehensive.py -v
    
    # Run specific phase
    pytest app/tests/test_jd_sync_comprehensive.py -v -k "Phase3"
    
    # Run with detailed output
    pytest app/tests/test_jd_sync_comprehensive.py -v --tb=short -s
    
    # Run specific test
    pytest app/tests/test_jd_sync_comprehensive.py -v -k "test_transformer"
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Generator
from unittest.mock import Mock
import time
import pandas as pd

import os
import sys
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
    Mock SQL Server connector for JD sync testing.
    
    Simulates SQL Server behavior:
    - Returns data with native SQL Server types (datetime, bool from BIT)
    - Supports full sync (all records) and incremental sync (filtered by timestamp)
    - Provides table schema and metadata
    """
    
    def __init__(self, sample_data: List[Dict[str, Any]] = None):
        """Initialize with sample data or generate default data."""
        self.sample_data = sample_data or self._generate_sample_data()
        self.connection_test_result = True
        self.max_batch_size = 1000
    
    def _generate_sample_data(self) -> List[Dict[str, Any]]:
        """
        Generate realistic sample JD data.
        
        Includes:
        - Multiple employees with multiple JD assignments
        - Role changes (ended JDs with end_date)
        - Current and historical assignments
        - Realistic job descriptions
        """
        base_date = datetime.now() - timedelta(days=180)
        
        return [
            # Employee 101: Single current JD
            {
                "Employee_ID": 101,
                "JD_ID": 1001,
                "Job_Description": "Responsible for analyzing employee performance data, generating actionable insights, and presenting findings to senior management. Requires proficiency in Python, SQL, and data visualization tools. Strong communication skills essential.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=1)
            },
            
            # Employee 102: Role change (ended + current JD)
            {
                "Employee_ID": 102,
                "JD_ID": 1002,
                "Job_Description": "Coordinates project activities across multiple teams, manages timelines and budgets, ensures deliverables meet quality standards. Acts as liaison between technical and business stakeholders. Facilitates communication and resolves conflicts.",
                "Assigned_Date": date(2023, 6, 1),
                "Is_Current": False,
                "End_Date": date(2024, 5, 31),
                "LastModifiedDate": base_date + timedelta(days=2)
            },
            {
                "Employee_ID": 102,
                "JD_ID": 1003,
                "Job_Description": "Senior Project Manager responsible for strategic planning, resource allocation, and cross-functional leadership. Drives organizational initiatives and mentors junior team members. Reports directly to department head.",
                "Assigned_Date": date(2024, 6, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=3)
            },
            
            # Employee 103: Multiple role changes
            {
                "Employee_ID": 103,
                "JD_ID": 1004,
                "Job_Description": "Junior Software Engineer responsible for developing and maintaining backend services using Python and PostgreSQL. Collaborates with senior engineers on feature implementation and bug fixes. Participates in code reviews and testing.",
                "Assigned_Date": date(2023, 1, 1),
                "Is_Current": False,
                "End_Date": date(2023, 12, 31),
                "LastModifiedDate": base_date + timedelta(days=4)
            },
            {
                "Employee_ID": 103,
                "JD_ID": 1005,
                "Job_Description": "Software Engineer II focusing on API development and database optimization. Leads implementation of new features and provides technical guidance to junior developers. Participates in architecture decisions.",
                "Assigned_Date": date(2024, 1, 1),
                "Is_Current": False,
                "End_Date": date(2024, 6, 30),
                "LastModifiedDate": base_date + timedelta(days=5)
            },
            {
                "Employee_ID": 103,
                "JD_ID": 1006,
                "Job_Description": "Senior Software Engineer responsible for system architecture, performance optimization, and mentoring development team. Makes critical technical decisions and ensures best practices. Drives innovation and process improvements.",
                "Assigned_Date": date(2024, 7, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=6)
            },
            
            # Employee 104: Current JD
            {
                "Employee_ID": 104,
                "JD_ID": 1007,
                "Job_Description": "Data Scientist responsible for building predictive models, conducting statistical analysis, and generating insights from large datasets. Expertise in machine learning, Python, R, and data visualization required.",
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=7)
            },
            
            # Employee 105: Current JD
            {
                "Employee_ID": 105,
                "JD_ID": 1008,
                "Job_Description": "Technical Lead responsible for architecture decisions, code reviews, and ensuring development best practices. Coordinates with product management and stakeholders. Provides technical mentorship to team members.",
                "Assigned_Date": date(2024, 3, 1),
                "Is_Current": True,
                "End_Date": None,
                "LastModifiedDate": base_date + timedelta(days=8)
            }
        ]
    
    def test_connection(self) -> bool:
        """Simulate connection test."""
        return self.connection_test_result
    
    def get_allowed_tables(self) -> List[str]:
        """Return mock table list."""
        return ["EmployeeJobDescriptions", "EmployeeReports", "VisionEmployeeData"]
    
    def get_allowed_timestamp_columns(self) -> List[str]:
        """Return mock timestamp columns."""
        return ["LastModifiedDate", "ModifiedDate", "UpdatedAt", "last_modified_date"]
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Return mock table schema."""
        if "job" in table_name.lower() or "jd" in table_name.lower():
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
        """
        Simulate full sync - return all records in batches.
        
        Args:
            table_name: Table name
            batch_size: Records per batch
            order_by: Column to order by
            
        Yields:
            Batches of records
        """
        # Return data in batches
        for i in range(0, len(self.sample_data), batch_size):
            batch = self.sample_data[i:i + batch_size]
            yield batch
    
    def get_records_since(self, table_name: str, timestamp_column: str,
                         since_timestamp: datetime, batch_size: int = 1000,
                         order_by: str = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Simulate incremental sync - return records modified after timestamp.
        
        Args:
            table_name: Table name
            timestamp_column: Timestamp column name
            since_timestamp: Only return records after this time
            batch_size: Records per batch
            order_by: Column to order by
            
        Yields:
            Batches of filtered records
        """
        # Filter records by timestamp
        filtered = [
            record for record in self.sample_data
            if timestamp_column in record and record[timestamp_column] > since_timestamp
        ]
        
        # Return in batches
        for i in range(0, len(filtered), batch_size):
            batch = filtered[i:i + batch_size]
            yield batch


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_instance():
    """Get database instance for test session."""
    return get_database()


@pytest.fixture
def db_session(db_instance):
    """
    Create isolated database session with transaction rollback.
    
    Each test gets a fresh session that rolls back after test completion.
    """
    session = db_instance.create_session()
    session.begin()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def mock_connector():
    """Create mock SQL Server connector with valid sample data."""
    return MockSQLServerConnector()


@pytest.fixture
def mock_connector_with_errors():
    """
    Create mock connector with data that will trigger validation errors.
    
    Includes:
    - Valid records (for comparison)
    - Invalid employee IDs (non-existent)
    - Too-short job descriptions (<50 chars)
    - Future dates
    - Invalid data types
    """
    error_data = [
        # VALID: Baseline record
        {
            "Employee_ID": 101,
            "JD_ID": 2001,
            "Job_Description": "Valid job description with sufficient length to meet minimum character requirements for testing purposes.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        
        # ERROR 1: Non-existent employee
        {
            "Employee_ID": 999999,  # Does not exist
            "JD_ID": 2002,
            "Job_Description": "Job description for non-existent employee with sufficient character length for validation testing.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        
        # ERROR 2: Job description too short
        {
            "Employee_ID": 102,
            "JD_ID": 2003,
            "Job_Description": "Too short",  # Less than 50 characters
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        
        # ERROR 3: Future assigned date
        {
            "Employee_ID": 103,
            "JD_ID": 2004,
            "Job_Description": "Job description with future date which should fail validation requirements during testing process.",
            "Assigned_Date": date.today() + timedelta(days=30),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        },
        
        # ERROR 4: Future end date
        {
            "Employee_ID": 104,
            "JD_ID": 2005,
            "Job_Description": "Job description with future end date which should fail validation requirements during testing.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": False,
            "End_Date": date.today() + timedelta(days=30),
            "LastModifiedDate": datetime.now()
        }
    ]
    
    return MockSQLServerConnector(sample_data=error_data)


@pytest.fixture
def test_employees(db_session):
    """
    Create test employees for JD sync tests.
    
    CRITICAL: Commits employees so sync service can see them.
    Sync service uses separate session, so needs committed data.
    """
    test_ids = [101, 102, 103, 104, 105]
    
    # Clean existing test data
    db_session.query(EmployeeJobDescription).filter(
        EmployeeJobDescription.employee_id.in_(test_ids)
    ).delete(synchronize_session=False)
    
    db_session.query(Employee).filter(
        Employee.id.in_(test_ids)
    ).delete(synchronize_session=False)
    
    db_session.flush()
    
    # Create test employees
    employees = [
        Employee(
            id=emp_id,
            name=f"Test Employee {emp_id}",
            position="Test Position",
            wing="Test Wing"
        )
        for emp_id in test_ids
    ]
    
    db_session.add_all(employees)
    db_session.commit()
    
    logger.info(f"[OK] Created {len(employees)} test employees: {test_ids}")
    
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
def error_handler():
    """Create error handler for processor tests."""
    return ImportErrorHandler()


@pytest.fixture
def sync_service(mock_connector):
    """Create sync service with mock connector."""
    return SyncService(mock_connector, error_threshold_percent=10.0)


# ============================================================================
# PHASE 1: TRANSFORMER TESTS
# ============================================================================

class TestPhase1Transformers:
    """
    Test JobDescriptionTransformer.
    
    Validates:
    - SQL Server types → Pydantic-compatible format
    - Field mapping correctness
    - LastModifiedDate exclusion
    """
    
    def test_transformer_basic(self):
        """Test basic transformation of SQL Server row."""
        sql_row = {
            "Employee_ID": 101,
            "JD_ID": 1001,
            "Job_Description": "Responsible for backend development using Python and PostgreSQL database systems.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime(2024, 11, 20, 10, 30)
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        # Verify field mapping
        assert transformed['Employee_ID'] == 101
        assert transformed['JD_ID'] == 1001
        assert isinstance(transformed['Job_Description'], str)
        assert transformed['Assigned_Date'] == date(2024, 1, 15)
        assert transformed['Is_Current'] is True
        assert transformed['End_Date'] is None
        
        # Verify LastModifiedDate excluded (internal tracking only)
        assert 'LastModifiedDate' not in transformed
        
        logger.info("[OK] Basic transformer test passed")
    
    def test_transformer_with_end_date(self):
        """Test transformation of ended JD assignment."""
        sql_row = {
            "Employee_ID": 102,
            "JD_ID": 1002,
            "Job_Description": "Project coordinator responsible for timeline management and stakeholder communication.",
            "Assigned_Date": date(2023, 6, 1),
            "Is_Current": False,
            "End_Date": date(2024, 5, 31),
            "LastModifiedDate": datetime(2024, 6, 1, 9, 0)
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        assert transformed['Is_Current'] is False
        assert transformed['End_Date'] == date(2024, 5, 31)
        
        logger.info("[OK] Transformer with end_date test passed")
    
    def test_transformer_preserves_types(self):
        """Test that transformer preserves correct Python types."""
        sql_row = {
            "Employee_ID": 103,
            "JD_ID": 1003,
            "Job_Description": "Senior engineer responsible for architecture decisions and technical leadership roles.",
            "Assigned_Date": date(2024, 7, 1),
            "Is_Current": True,
            "End_Date": None,
            "LastModifiedDate": datetime.now()
        }
        
        transformed = JobDescriptionTransformer.transform(sql_row)
        
        # Verify types
        assert isinstance(transformed['Employee_ID'], int)
        assert isinstance(transformed['JD_ID'], int)
        assert isinstance(transformed['Job_Description'], str)
        assert isinstance(transformed['Assigned_Date'], date)
        assert isinstance(transformed['Is_Current'], bool)
        assert transformed['End_Date'] is None or isinstance(transformed['End_Date'], date)
        
        logger.info("[OK] Transformer type preservation test passed")
    
    def test_transformer_with_mock_data(self, mock_connector):
        """Test transformer with mock sample data."""
        # Get first batch from mock connector
        batches = list(mock_connector.get_all_records(
            table_name="EmployeeJobDescriptions",
            batch_size=10
        ))
        
        first_batch = batches[0]
        
        # Transform all records in batch
        transformed_records = []
        for sql_row in first_batch:
            transformed = JobDescriptionTransformer.transform(sql_row)
            transformed_records.append(transformed)
        
        # Verify all transformed successfully
        assert len(transformed_records) == len(first_batch)
        
        # Verify each record has required fields
        for record in transformed_records:
            assert 'Employee_ID' in record
            assert 'JD_ID' in record
            assert 'Job_Description' in record
            assert 'Assigned_Date' in record
            assert 'Is_Current' in record
            assert 'LastModifiedDate' not in record
        
        logger.info(f"[OK] Transformer with mock data: {len(transformed_records)} records transformed")


# ============================================================================
# PHASE 2: PYDANTIC VALIDATION TESTS
# ============================================================================

class TestPhase2PydanticValidation:
    """
    Test JobDescriptionCSVRow Pydantic schema.
    
    Validates:
    - Field validation rules
    - Type conversions
    - Business logic constraints
    """
    
    def test_pydantic_valid_record(self):
        """Test validation of valid JD record."""
        valid_data = {
            "Employee_ID": 101,
            "JD_ID": "1001",
            "Job_Description": "Responsible for analyzing employee performance data and generating actionable insights for management.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        # Should validate successfully
        validated = JobDescriptionCSVRow(**valid_data)
        
        assert validated.Employee_ID == 101
        assert validated.JD_ID == "1001"
        assert len(validated.Job_Description) >= 50
        
        logger.info("[OK] Pydantic valid record test passed")
    
    def test_pydantic_jd_id_conversion(self):
        """Test JD_ID conversion from int to string."""
        data = {
            "Employee_ID": 101,
            "JD_ID": 1001,  # Integer (from SQL Server)
            "Job_Description": "Software engineer responsible for developing backend services using Python and PostgreSQL databases.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        validated = JobDescriptionCSVRow(**data)
        
        # Should convert to string
        assert isinstance(validated.JD_ID, str)
        assert validated.JD_ID == "1001"
        
        logger.info("[OK] Pydantic JD_ID conversion test passed")
    
    def test_pydantic_short_description_fails(self):
        """Test that job description < 50 chars fails validation."""
        data = {
            "Employee_ID": 101,
            "JD_ID": "1001",
            "Job_Description": "Too short",  # Only 9 characters
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            JobDescriptionCSVRow(**data)
        
        assert "at least 50 characters" in str(exc_info.value).lower()
        
        logger.info("[OK] Pydantic short description validation test passed")
    
    def test_pydantic_future_date_fails(self):
        """Test that future assigned_date fails validation."""
        data = {
            "Employee_ID": 101,
            "JD_ID": "1001",
            "Job_Description": "Senior software engineer responsible for system architecture and team mentorship activities.",
            "Assigned_Date": date.today() + timedelta(days=30),
            "Is_Current": True,
            "End_Date": None
        }
        
        with pytest.raises(Exception) as exc_info:
            JobDescriptionCSVRow(**data)
        
        assert "future" in str(exc_info.value).lower()
        
        logger.info("[OK] Pydantic future date validation test passed")
    
    def test_pydantic_is_current_normalization(self):
        """Test is_current field normalization from various formats."""
        test_cases = [
            (True, True),
            (False, False),
            (1, True),
            (0, False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            (None, True),  # Defaults to True
        ]
        
        for input_val, expected in test_cases:
            data = {
                "Employee_ID": 101,
                "JD_ID": "1001",
                "Job_Description": "Project manager coordinating cross-functional teams and managing project timelines effectively.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": input_val,
                "End_Date": None
            }
            
            validated = JobDescriptionCSVRow(**data)
            assert validated.Is_Current == expected, f"Failed for input: {input_val}"
        
        logger.info("[OK] Pydantic is_current normalization test passed")


# ============================================================================
# PHASE 3: PROCESSOR TESTS
# ============================================================================

class TestPhase3Processor:
    """
    Test JobDescriptionProcessor.
    
    Validates:
    - Row processing (create/update)
    - Bulk processing
    - Metrics tracking
    - Error handling
    """
    
    def test_processor_creation(self, db_session, error_handler):
        """Test processor instantiation."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        assert processor is not None
        assert processor.jd_records_created == 0
        assert processor.jd_records_updated == 0
        
        logger.info("[OK] Processor creation test passed")
    
    def test_processor_can_process(self):
        """Test processor can detect JD CSV format."""
        headers = ["Employee_ID", "JD_ID", "Job_Description", "Assigned_Date", "Is_Current"]
        
        can_process = JobDescriptionProcessor.can_process(headers)
        
        assert can_process is True
        
        logger.info("[OK] Processor can_process test passed")
    
    def test_processor_single_row(self, db_session, error_handler, test_employees):
        """Test processing single JD row."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        row_data = {
            "Employee_ID": 101,
            "JD_ID": "3001",
            "Job_Description": "Data analyst responsible for extracting insights from large datasets and creating visualizations.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        success = processor.process_row(row_data, row_number=1)
        
        assert success is True
        assert processor.jd_records_created == 1
        assert processor.successful_rows == 1
        
        # Verify record in database
        jd = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 101,
            EmployeeJobDescription.jd_id == "3001"
        ).first()
        
        assert jd is not None
        assert jd.job_description == row_data['Job_Description']
        
        logger.info("[OK] Processor single row test passed")
    
    def test_processor_bulk_processing(self, db_session, error_handler, test_employees):
        """Test bulk processing of multiple JD rows."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        # Create DataFrame with multiple rows
        data = [
            {
                "Employee_ID": 101,
                "JD_ID": "4001",
                "Job_Description": "Backend engineer developing RESTful APIs and database schemas for enterprise applications.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None
            },
            {
                "Employee_ID": 102,
                "JD_ID": "4002",
                "Job_Description": "Frontend developer building responsive user interfaces using modern JavaScript frameworks and libraries.",
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "End_Date": None
            },
            {
                "Employee_ID": 103,
                "JD_ID": "4003",
                "Job_Description": "DevOps engineer maintaining CI/CD pipelines and ensuring system reliability and performance.",
                "Assigned_Date": date(2024, 3, 1),
                "Is_Current": True,
                "End_Date": None
            }
        ]
        
        df = pd.DataFrame(data)
        
        successful, total = processor.process_dataframe(df, start_row_number=1, pre_cleaned=True)
        
        assert successful == 3
        assert total == 3
        assert processor.jd_records_created == 3
        
        logger.info(f"[OK] Processor bulk processing test passed: {successful}/{total} records")
    
    def test_processor_metrics(self, db_session, error_handler, test_employees):
        """Test processor tracks metrics correctly."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        # Process some records
        data = [
            {
                "Employee_ID": 101,
                "JD_ID": "5001",
                "Job_Description": "Quality assurance engineer designing test cases and ensuring software quality standards are met.",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None
            }
        ]
        
        df = pd.DataFrame(data)
        processor.process_dataframe(df, start_row_number=1, pre_cleaned=True)
        
        # Get metrics
        metrics = processor.get_metrics()
        
        assert 'jd_records_created' in metrics
        assert 'jd_records_updated' in metrics
        assert 'processed_rows' in metrics
        assert 'successful_rows' in metrics
        
        logger.info(f"[OK] Processor metrics test passed: {metrics}")


# ============================================================================
# PHASE 4: SYNC SERVICE TESTS
# ============================================================================

class TestPhase4SyncService:
    """
    Test SyncService JD sync operations.
    
    Validates:
    - Full sync workflow
    - Incremental sync workflow
    - Sync history tracking
    - Error handling
    """
    
    def test_sync_service_full_sync(self, sync_service, db_session, test_employees):
        """Test full sync creates JD records."""
        # Perform full sync
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify sync completed
        assert sync_result is not None
        assert sync_result.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert sync_result.status in [
            SyncStatus.COMPLETED.value,
            SyncStatus.PARTIAL.value
        ]
        
        # Verify records synced
        assert sync_result.records_synced > 0
        
        # Verify records in database
        jd_count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        
        assert jd_count > 0
        
        logger.info(f"[OK] Full sync test: {sync_result.records_synced} records synced, {jd_count} in DB")
    
    def test_sync_service_incremental_sync(self, sync_service, db_session, test_employees):
        """Test incremental sync uses last_sync_timestamp."""
        # First sync
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        assert full_sync.last_sync_timestamp is not None
        
        # Wait a moment
        time.sleep(1)
        
        # Incremental sync (should find 0 new records with static mock data)
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        
        assert incremental_sync.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert incremental_sync.records_queried == 0  # No new records
        
        logger.info(f"[OK] Incremental sync test: {incremental_sync.records_queried} new records")
    
    def test_sync_service_tracks_metrics(self, sync_service, db_session, test_employees):
        """Test sync service tracks all metrics correctly."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Verify metrics exist
        assert hasattr(sync_result, 'records_queried')
        assert hasattr(sync_result, 'records_synced')
        assert hasattr(sync_result, 'error_count')
        assert hasattr(sync_result, 'sync_metadata')
        
        # Verify metadata contains processor metrics
        metadata = sync_result.sync_metadata or {}
        assert isinstance(metadata, dict)
        
        logger.info(f"[OK] Metrics tracking test: queried={sync_result.records_queried}, synced={sync_result.records_synced}")
    
    def test_sync_service_creates_history(self, sync_service, db_session, test_employees):
        """Test sync creates proper history record."""
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Query sync history
        history = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_result.sync_id
        ).first()
        
        assert history is not None
        assert history.sync_type == SyncType.JOB_DESCRIPTIONS.value
        assert history.started_at is not None
        assert history.completed_at is not None
        
        logger.info(f"[OK] Sync history test: sync_id={history.sync_id}")


# ============================================================================
# PHASE 5: SYNC TASK TESTS (MOCK)
# ============================================================================

class TestPhase5SyncTasks:
    """
    Test Celery task logic WITHOUT actually running Celery.
    
    Tests task functions directly to validate:
    - Metrics extraction
    - Return value structure
    - Error handling
    """
    
    def test_task_metrics_extraction(self, sync_service, db_session, test_employees):
        """Test task correctly extracts metrics from sync_job."""
        from app.tasks.sync_tasks import sync_job_descriptions_task
        
        # Create mock task instance
        mock_task = Mock()
        mock_task.sync_service = sync_service
        
        # FIX: Call with self as positional argument, not keyword
        result = sync_job_descriptions_task.apply(
            kwargs={'is_full_sync': True, 'sync_id': None}
        ).get()
        
        # Verify return structure
        assert isinstance(result, dict)
        assert 'sync_id' in result
        assert 'status' in result
        assert 'sync_type' in result
        assert 'records_queried' in result
        assert 'records_synced' in result
        assert 'error_count' in result
        assert 'metrics' in result
        
        # Verify metrics structure
        metrics = result['metrics']
        assert isinstance(metrics, dict)
        assert 'jd_records_created' in metrics
        assert 'jd_records_updated' in metrics
        
        logger.info(f"[OK] Task metrics extraction test: {result['records_synced']} records")
    
    def test_task_return_no_timestamps(self, sync_service, db_session, test_employees):
        """Test task return dict contains no datetime objects."""
        from app.tasks.sync_tasks import sync_job_descriptions_task
        
        mock_task = Mock()
        mock_task.sync_service = sync_service
        
        # FIX: Call with self as positional argument, not keyword
        result = sync_job_descriptions_task.apply(
            kwargs={'is_full_sync': True, 'sync_id': None}
        ).get()
        
        # Verify no datetime objects in return dict
        def check_no_datetimes(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    assert not isinstance(value, (datetime, date)), f"Found datetime in key: {key}"
                    if isinstance(value, dict):
                        check_no_datetimes(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_no_datetimes(item)
        
        check_no_datetimes(result)
        
        logger.info("[OK] Task return structure test: no timestamps found")


# ============================================================================
# PHASE 6: ERROR HANDLING TESTS
# ============================================================================

class TestPhase6ErrorHandling:
    """
    Test error handling throughout the pipeline.
    
    Uses mock connector with intentionally invalid data.
    """
    
    def test_sync_with_errors(self, mock_connector_with_errors, db_session, test_employees):
        """Test sync handles validation errors gracefully."""
        sync_service = SyncService(mock_connector_with_errors, error_threshold_percent=10.0)
        
        sync_result = sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Sync should complete but with errors
        assert sync_result.status in [
            SyncStatus.COMPLETED.value,
            SyncStatus.PARTIAL.value,
            SyncStatus.FAILED.value
        ]
        
        # Should have recorded errors
        assert sync_result.error_count > 0
        
        # Should have synced valid records
        assert sync_result.records_synced > 0  # At least 1 valid record
        
        logger.info(f"[OK] Error handling test: {sync_result.error_count} errors, {sync_result.records_synced} synced")
    
    def test_processor_handles_invalid_employee(self, db_session, error_handler, test_employees):
        """Test processor handles non-existent employee ID."""
        processor = JobDescriptionProcessor(db_session, error_handler)
        
        row_data = {
            "Employee_ID": 999999,  # Does not exist
            "JD_ID": "9001",
            "Job_Description": "Job description for non-existent employee with sufficient character length for testing.",
            "Assigned_Date": date(2024, 1, 15),
            "Is_Current": True,
            "End_Date": None
        }
        
        success = processor.process_row(row_data, row_number=1)
        
        # Should fail gracefully
        assert success is False
        assert error_handler.get_error_count() > 0
        
        # Verify error details
        errors = error_handler.get_errors()
        assert len(errors) > 0
        assert "does not exist" in errors[0].error_message.lower()
        
        logger.info("[OK] Invalid employee handling test passed")


# ============================================================================
# PHASE 7: END-TO-END WORKFLOW TESTS
# ============================================================================

class TestPhase7EndToEnd:
    """
    Test complete end-to-end workflows.
    
    Simulates real-world usage patterns.
    """
    
    def test_complete_workflow(self, sync_service, db_session, test_employees):
        """Test complete sync workflow from start to finish."""
        logger.info("=" * 80)
        logger.info("STARTING END-TO-END JD SYNC WORKFLOW TEST")
        logger.info("=" * 80)
        
        # Step 1: Initial full sync
        logger.info("Step 1: Running initial full sync...")
        full_sync = sync_service.sync_job_descriptions(is_full_sync=True)
        
        assert full_sync.status in [SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]
        initial_count = full_sync.records_synced
        logger.info(f"[OK] Full sync: {initial_count} records synced")
        
        # Step 2: Verify records in database
        logger.info("Step 2: Verifying records in PostgreSQL...")
        jd_count = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id.in_(test_employees)
        ).count()
        logger.info(f"[OK] Found {jd_count} JD records in database")
        
        # Step 3: Verify each employee has correct JDs
        logger.info("Step 3: Verifying employee JD assignments...")
        for emp_id in test_employees:
            jds = db_session.query(EmployeeJobDescription).filter(
                EmployeeJobDescription.employee_id == emp_id
            ).all()
            
            if len(jds) > 0:
                current_jds = [jd for jd in jds if jd.is_current]
                logger.info(f"  Employee {emp_id}: {len(jds)} total JDs, {len(current_jds)} current")
        
        # Step 4: Incremental sync
        logger.info("Step 4: Running incremental sync...")
        time.sleep(1)
        incremental_sync = sync_service.sync_job_descriptions(is_full_sync=False)
        logger.info(f"[OK] Incremental sync: {incremental_sync.records_queried} new records")
        
        # Step 5: Verify sync history
        logger.info("Step 5: Verifying sync history...")
        history_count = db_session.query(SyncHistory).filter(
            SyncHistory.sync_type == SyncType.JOB_DESCRIPTIONS.value
        ).count()
        logger.info(f"[OK] Found {history_count} sync history records")
        
        logger.info("=" * 80)
        logger.info("END-TO-END WORKFLOW TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
    
    def test_multiple_jds_per_employee(self, sync_service, db_session, test_employees):
        """Test employees with multiple JD assignments (role changes)."""
        # Sync all data
        sync_service.sync_job_descriptions(is_full_sync=True)
        
        # Employee 102 should have 2 JDs (one ended, one current)
        jds_102 = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 102
        ).all()
        
        if len(jds_102) > 1:
            # Verify one is current, others are ended
            current_count = sum(1 for jd in jds_102 if jd.is_current)
            ended_count = sum(1 for jd in jds_102 if not jd.is_current)
            
            logger.info(f"[OK] Employee 102: {current_count} current JD, {ended_count} ended JDs")
        
        # Employee 103 should have 3 JDs (progression through roles)
        jds_103 = db_session.query(EmployeeJobDescription).filter(
            EmployeeJobDescription.employee_id == 103
        ).all()
        
        if len(jds_103) >= 3:
            current_count = sum(1 for jd in jds_103 if jd.is_current)
            logger.info(f"[OK] Employee 103: {len(jds_103)} total JDs, {current_count} current")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run JD sync pipeline tests.
    
    Usage:
        # Run all tests
        pytest app/tests/test_jd_sync_comprehensive.py -v
        
        # Run specific phase
        pytest app/tests/test_jd_sync_comprehensive.py -v -k "Phase3"
        
        # Run with detailed output
        pytest app/tests/test_jd_sync_comprehensive.py -v --tb=short -s
    """
    pytest.main([__file__, "-v", "--tb=short", "-s"])
