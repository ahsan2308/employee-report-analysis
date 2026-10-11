"""
Job Description Processor

Handles the transformation and processing of Job Description CSV rows into database operations.
Supports both manual CSV imports and SQL Server sync operations.
"""
from typing import Dict, Any, Tuple, List
import pandas as pd
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.services.csv.processors.base import BaseCSVProcessor
from app.services.csv.row_models import JobDescriptionCSVRow
from app.services.csv.error_handler import ImportErrorHandler
from app.core.logger import logger
from app.repositories.job_descriptions import (
    bulk_upsert_job_descriptions, existing_job_description_keys, upsert_job_description,
)


class JobDescriptionProcessor(BaseCSVProcessor):
    """
    Processes job description CSV rows into database operations.
    
    Design follows VisionDataProcessor pattern:
    - Employee existence validation BEFORE bulk processing
    - Bulk upsert using PostgreSQL INSERT ... ON CONFLICT
    - Tracks metrics (created/updated records)
    - Integrates with existing error handling system
    """

    row_model = JobDescriptionCSVRow
    
    # Required headers for job description CSV format
    REQUIRED_HEADERS = [
        "Employee_ID", "JD_ID", "Job_Description", "Assigned_Date"
    ]
    
    def __init__(self, db: Session, error_handler: ImportErrorHandler):
        """Initialize the processor."""
        super().__init__(db, error_handler)
        self.jd_records_created = 0
        self.jd_records_updated = 0
        self._existing_employee_ids = None
    
    def validate_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """Dry-run check: the row model, then that the employee exists (read-only)."""
        validated = self._validate_model(row_data, row_number)
        if validated is None:
            return False
        employee_id = validated.model_dump().get('Employee_ID')
        if employee_id not in self._get_existing_employee_ids():
            self.error_handler.add_missing_employee_error(
                row_number=row_number,
                error_message=f"Employee ID {employee_id} does not exist in the database. Please ensure the employee is created before importing their job description.",
                row_data=row_data
            )
            return False
        return True

    
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single job description CSV row.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Validate row data using Pydantic model
            # NO context parameter - validation is simpler now
            validated_data = JobDescriptionCSVRow(**row_data)
            row_dict = validated_data.model_dump()
            
            # Check if employee exists
            employee_id = row_dict.get('Employee_ID')
            if employee_id not in self._get_existing_employee_ids():
                self.error_handler.add_missing_employee_error(
                    row_number=row_number,
                    error_message=f"Employee ID {employee_id} does not exist in the database. Please ensure the employee is created before importing their job description.",
                    row_data=row_data
                )
                return False
            
            # Check for existing JD assignment (employee_id, jd_id combination)
            created = upsert_job_description(
                self.db,
                employee_id=employee_id,
                jd_id=row_dict.get('JD_ID'),
                job_description=row_dict.get('Job_Description'),
                assigned_date=row_dict.get('Assigned_Date'),
                is_current=row_dict.get('Is_Current'),
                end_date=row_dict.get('End_Date')
            )
            if created:
                self.jd_records_created += 1
            else:
                self.jd_records_updated += 1
            
            self.db.commit()
            self.successful_rows += 1
            return True
            
        except ValidationError as e:
            # Handle validation errors from Pydantic
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing JD row {row_number}: {str(e)}")
            self.error_handler.add_processing_error(
                row_number=row_number,
                row_data=row_data,
                error_message=f"Unexpected error: {str(e)}",
                exception=e
            )
            return False
    
    def process_dataframe(self, df: pd.DataFrame, start_row_number: int = 1, pre_cleaned: bool = True) -> Tuple[int, int]:
        """
        Process a DataFrame of job description rows in bulk.
        
        Pattern follows VisionDataProcessor:
        1. Validate all rows with Pydantic
        2. Filter for existing employees BEFORE bulk operations
        3. Call _bulk_process_job_descriptions() for bulk upsert
        
        Args:
            df: Pandas DataFrame with CSV data
            start_row_number: Starting row number for error reporting
            pre_cleaned: Whether the DataFrame has already been cleaned (NaN → None)
            
        Returns:
            Tuple of (successful_rows, total_rows)
        """
        first_index = df.index[0] if len(df) else 0  # index of this chunk's first file row
        if df.empty:
            return 0, 0
        
        # Track metrics
        successful_rows = 0
        total_rows = len(df)
        
        # Validate all rows with Pydantic
        validated_rows = []
        invalid_rows = []
        
        for idx, row in df.iterrows():
            # Chunks keep the file-wide index; dropped duplicates keep their gaps
            row_number = start_row_number + (idx - first_index)
            try:
                if pre_cleaned:
                    # Data is already cleaned by PandasCSVReader.read_dataframes
                    row_dict = row.to_dict()
                else:
                    # Clean data - replace nan with None
                    row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                
                # Use simple constructor - no context needed anymore
                validated_data = JobDescriptionCSVRow(**row_dict)
                validated_rows.append((row_number, validated_data.model_dump()))
            except ValidationError as e:
                # Add to invalid rows
                invalid_rows.append((row_number, row.to_dict(), e))
                # Record validation errors
                self.error_handler.normalize_pydantic_errors(e, row_number, row.to_dict())
        
        if not validated_rows:
            return 0, total_rows
        
        # Check employee existence BEFORE bulk processing
        # Every validated row counts as unsaved until the employee check narrows the list
        valid_rows = validated_rows
        try:
            # Get set of existing employee IDs
            existing_employees = self._get_existing_employee_ids()
            
            # Filter out rows with non-existent employees BEFORE bulk processing
            valid_rows = []
            for row_number, row_dict in validated_rows:
                employee_id = row_dict.get('Employee_ID')
                if employee_id not in existing_employees:
                    # Add error for non-existent employee
                    self.error_handler.add_missing_employee_error(
                        row_number=row_number,
                        error_message=f"Employee ID {employee_id} does not exist in the database. Please ensure the employee is created before importing their job description.",
                        row_data=row_dict
                    )
                    logger.warning(f"Row {row_number}: Employee ID {employee_id} not found in database")
                else:
                    valid_rows.append((row_number, row_dict))
            
            # If no valid rows after filtering, return early
            if not valid_rows:
                logger.warning(f"No valid rows to process after employee existence check. All {len(validated_rows)} rows had non-existent employee IDs.")
                return 0, total_rows
            
            # Process all valid rows in bulk
            bulk_success = self._bulk_process_job_descriptions([row for _, row in valid_rows])
            
            successful_rows = 0
            if bulk_success:
                successful_rows = len(valid_rows)
                self.successful_rows += successful_rows
            else:
                self._record_unsaved_rows(valid_rows)
            
            return successful_rows, total_rows
            
        except Exception as e:
            logger.error(f"Bulk JD processing failed: {str(e)}")
            self.db.rollback()
            self._record_unsaved_rows(valid_rows, e)
            return 0, total_rows
    
    def _bulk_process_job_descriptions(self, validated_rows: List[Dict[str, Any]]) -> bool:
        """
        Process job descriptions in bulk using PostgreSQL INSERT ... ON CONFLICT.
        
        Pattern follows EmployeeReportProcessor._bulk_process_reports():
        - Uses PostgreSQL upsert (INSERT ... ON CONFLICT DO UPDATE)
        - Updates job_description, assigned_date, is_current, end_date, and updated_at on conflict
        - Tracks created/updated counts via rowcount
        
        Args:
            validated_rows: List of validated row dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            
            # Prepare data for bulk insert
            jd_data = []
            
            for row in validated_rows:
                jd_data.append({
                    'employee_id': row['Employee_ID'],
                    'jd_id': str(row['JD_ID']),
                    'job_description': row['Job_Description'],
                    'assigned_date': row['Assigned_Date'],
                    'is_current': row['Is_Current'],
                    'end_date': row.get('End_Date')
                })
            
            if not jd_data:
                logger.warning("No JD data to process after preparation")
                return True
            
            # Query for existing JD assignments BEFORE upsert
            jd_keys = [(jd['employee_id'], jd['jd_id']) for jd in jd_data]
            existing_count = len(existing_job_description_keys(self.db, jd_keys))
            new_count = len(jd_data) - existing_count
            
            logger.info(f"Pre-upsert check: {existing_count} existing JD assignments, {new_count} new JD assignments")
            
            # Perform bulk upsert using PostgreSQL-specific INSERT ... ON CONFLICT
            bulk_upsert_job_descriptions(self.db, jd_data)
            
            # Accurately track created vs updated
            self.jd_records_created += new_count
            self.jd_records_updated += existing_count
            
            self.db.commit()
            logger.info(f"Bulk processed {len(jd_data)} JD records ({new_count} created, {existing_count} updated)")
            return True
            
        except Exception as e:
            logger.error(f"Bulk JD processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get processing metrics.
        
        Returns dictionary with processor-specific metrics.
        Used by RowProcessor.get_metrics() and sync service.
        """
        return {
            "jd_records_created": self.jd_records_created,
            "jd_records_updated": self.jd_records_updated,
            "processed_rows": self.processed_rows,
            "successful_rows": self.successful_rows
        }
    
    def get_required_headers(self) -> List[str]:
        """Get the list of required headers for this processor."""
        return self.REQUIRED_HEADERS
    
    @classmethod
    def can_process(cls, headers: List[str]) -> bool:
        """
        Determine if this processor can handle a CSV with the given headers.
        
        For job descriptions, we need Employee_ID, JD_ID, Job_Description, and Assigned_Date.
        This enables ProcessorFactory auto-detection.
        
        Args:
            headers: List of CSV column headers
            
        Returns:
            True if all required headers are present
        """
        essential_headers = ["Employee_ID", "JD_ID", "Job_Description", "Assigned_Date", "Is_Current"]
        return all(header in headers for header in essential_headers)
