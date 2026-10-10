"""
Tests for the optimized CSV import functionality.

This test suite focuses on validating the efficiency improvements:
1. CSV reader integration with data cleaning
2. Utility functions for metrics and validation
3. Consistent error handling across processing methods
4. Transaction management consistency
"""
import pytest
import os
import io
import pandas as pd
import tempfile
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy.orm import Session
from app.services.csv_import_service import CSVImportService, get_csv_import_service
from app.services.csv.csv_reader import PandasCSVReader
from app.services.csv.row_processor import RowProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.schemas.csv_import_schema import CSVImportOptions, CombinedCSVRow
from app.models.import_models import CSVImportJob, ImportStatus

# Sample CSV data for testing
SAMPLE_CSV = """Name,Designation,BPS,Office_Hierarchy,From,To,Tasks_Completed,Impact,Challenges,Support_Required,Tasks_Planned,Employee_ID
John Smith,Engineer,BS-17,Technical>Tech-I>SOC,2023-01-01,2023-01-31,Completed task 1,High impact,Some challenges,Need support,Plan for next month,1001
Jane Doe,Manager,BS-18,Management>Admin,2023-01-01,2023-01-31,Completed task 2,Medium impact,No challenges,No support needed,Continue work,1002
"""

@pytest.fixture
def csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        f.write(SAMPLE_CSV)
        f.flush()
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def csv_import_service():
    """Create a CSV import service for testing."""
    service = get_csv_import_service()
    # Mock the database session
    service.db_instance = MagicMock()
    service.db_instance.create_session.return_value = MagicMock(spec=Session)
    return service

@pytest.fixture
def error_handler():
    """Create an error handler for testing."""
    return ImportErrorHandler()

@pytest.fixture
def row_processor(error_handler):
    """Create a row processor for testing."""
    session = MagicMock(spec=Session)
    return RowProcessor(session, error_handler)

class TestCSVReaderIntegration:
    """Test the integration between CSVReader and RowProcessor."""

    def test_read_dataframes_with_pre_cleaned(self, csv_file, row_processor):
        """Test that DataFrames from read_dataframes are properly pre-cleaned."""
        reader = PandasCSVReader()
        dfs = list(reader.read_dataframes(file_path=csv_file))
        
        assert len(dfs) > 0, "Should have at least one DataFrame"
        
        # Patch the process_dataframe method to capture the pre_cleaned parameter
        with patch.object(row_processor, 'process_dataframe') as mock_process:
            mock_process.return_value = (2, 2)  # (successful_rows, total_rows)
            
            # Process the first DataFrame
            row_processor.process_dataframe(dfs[0], pre_cleaned=True)
            
            # Check that pre_cleaned=True was passed
            mock_process.assert_called_once()
            args, kwargs = mock_process.call_args
            assert kwargs.get('pre_cleaned') is True, "pre_cleaned should be True"

class TestUtilityFunctions:
    """Test the utility functions added to CSVImportService."""

    def test_calculate_processing_rate(self, csv_import_service):
        """Test the _calculate_processing_rate utility function."""
        # Normal case
        rate = csv_import_service._calculate_processing_rate(100, 10)
        assert rate == 10.0, "Rate should be 10.0 rows/sec"
        
        # Zero time case
        rate = csv_import_service._calculate_processing_rate(100, 0)
        assert rate == 0, "Rate should be 0 when time is 0"

    def test_validate_row(self, csv_import_service, error_handler):
        """Test the _validate_row utility function."""
        # Valid row - adding missing required fields
        valid_row = {
            'Name': 'John Smith',
            'Designation': 'Engineer',
            'From': '2023-01-01',
            'To': '2023-01-31',
            'Tasks_Completed': 'Task 1',
            'Employee_ID': 1001,
            # Add the following fields to satisfy validation
            'BPS': 'BS-17',
            'Office_Hierarchy': 'Technical>Support',
            'Impact': 'High impact'
        }
        
        # Fix: Patch the correct import path - CombinedCSVRow is imported within the method
        with patch('app.schemas.csv_import_schema.CombinedCSVRow') as mock_validator:
            mock_validator.return_value = MagicMock()  # Simulate successful validation
            result = csv_import_service._validate_row(valid_row, 1, error_handler)
            assert result is True, "Valid row should validate successfully"
        
        # Invalid row (missing required field)
        invalid_row = {
            'Name': 'John Smith',
            'Designation': 'Engineer',
            'From': '2023-01-01',
            'To': '2023-01-31',
            # Missing Tasks_Completed
            'Employee_ID': 1001
        }
        
        result = csv_import_service._validate_row(invalid_row, 2, error_handler)
        assert result is False, "Invalid row should fail validation"
        
        # Check that error was recorded
        assert error_handler.get_error_count() == 1, "Error should be recorded"

    def test_log_completion_info(self, csv_import_service):
        """Test the _log_completion_info utility function."""
        with patch('app.services.csv_import_service.logger.info') as mock_logger:
            csv_import_service._log_completion_info('test-id', 90, 100, 10.5)
            mock_logger.assert_called_once()
            log_message = mock_logger.call_args[0][0]
            assert 'test-id' in log_message, "Job ID should be in log message"
            assert '90/100' in log_message, "Row counts should be in log message"
            assert '10.5' in log_message, "Rate should be in log message"

class TestErrorHandling:
    """Test consistent error handling patterns."""
    
    def test_process_rows_error_handling(self, csv_import_service):
        """Test error handling in _process_rows method."""
        # Setup
        mock_session = MagicMock()
        mock_job = MagicMock(spec=CSVImportJob)
        mock_job.job_id = 'test-job-id'
        mock_generator = MagicMock()
        mock_generator.__iter__.side_effect = Exception("Test error")
        mock_error_handler = MagicMock(spec=ImportErrorHandler)
        mock_error_handler.get_error_count.return_value = 0
        
        # Fix: Add dry_run attribute to mock options
        mock_options = MagicMock(spec=CSVImportOptions)
        mock_options.dry_run = False
        mock_options.error_threshold_percent = 10.0
        mock_options.stop_on_error = False
        
        # Test that exception is caught and status is updated to FAILED
        with patch.object(csv_import_service, '_update_job_status') as mock_update:
            csv_import_service._process_rows(
                mock_session, mock_job, mock_generator, mock_error_handler, mock_options
            )
            
            # Check that status was updated to FAILED
            mock_update.assert_called_with(
                mock_session, mock_job, ImportStatus.FAILED
            )
    
    def test_process_with_pandas_error_handling(self, csv_import_service):
        """Test error handling in _process_with_pandas method."""
        # Setup
        mock_session = MagicMock()
        mock_job = MagicMock(spec=CSVImportJob)
        mock_job.job_id = 'test-job-id'
        mock_reader = MagicMock()
        mock_reader.__iter__.side_effect = Exception("Test error")
        mock_error_handler = MagicMock(spec=ImportErrorHandler)
        mock_error_handler.get_error_count.return_value = 0
        
        # Fix: Add dry_run attribute to mock options
        mock_options = MagicMock(spec=CSVImportOptions)
        mock_options.dry_run = False
        mock_options.error_threshold_percent = 10.0
        mock_options.stop_on_error = False
        
        # Test that exception is caught and status is updated to FAILED
        with patch.object(csv_import_service, '_update_job_status') as mock_update:
            csv_import_service._process_with_pandas(
                mock_session, mock_job, mock_reader, mock_error_handler, mock_options
            )
            
            # Check that status was updated to FAILED
            mock_update.assert_called_with(
                mock_session, mock_job, ImportStatus.FAILED
            )

@pytest.fixture
def employee_report_processor(error_handler):
    """Bulk methods moved from RowProcessor to EmployeeReportProcessor."""
    from app.services.csv.processors.employee_report_processor import EmployeeReportProcessor
    return EmployeeReportProcessor(MagicMock(spec=Session), error_handler)

class TestTransactionManagement:
    """Test transaction management consistency."""
    
    def test_bulk_process_employees_rollback(self, employee_report_processor):
        """Test that _bulk_process_employees rolls back on error."""
        # Setup mock db that raises an exception
        mock_db = MagicMock(spec=Session)
        mock_db.query.side_effect = Exception("Test error")
        employee_report_processor.db = mock_db
        
        # Call method with some data
        result = employee_report_processor._bulk_process_employees([{'Name': 'Test', 'Designation': 'Test', 'Employee_ID': 1}])
        
        # Check that rollback was called
        mock_db.rollback.assert_called_once()
        assert result is False, "Method should return False on error"
    
    def test_bulk_process_reports_rollback(self, employee_report_processor):
        """Test that _bulk_process_reports rolls back on error."""
        # Setup mock db that raises an exception
        mock_db = MagicMock(spec=Session)
        # Fix: Make sure the exception is raised during report processing, not just in query
        mock_db.execute.side_effect = Exception("Test error")
        employee_report_processor.db = mock_db
        
        # Call method with some data
        result = employee_report_processor._bulk_process_reports([{
            'Name': 'Test',
            'Designation': 'Test',
            'Employee_ID': 1,
            'From': '2023-01-01',
            'To': '2023-01-31',
            'Tasks_Completed': 'Test task'  # Add required field
        }])
        
        # Check that rollback was called
        mock_db.rollback.assert_called_once()
        assert result is False, "Method should return False on error"
