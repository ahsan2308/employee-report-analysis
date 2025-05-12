"""
Row Processor Component

Handles the transformation and processing of CSV rows into database operations.
"""
from typing import Dict, Any, Tuple, List, Optional, Set
from datetime import datetime
from uuid import UUID
import traceback
import pandas as pd
from sqlalchemy import insert, update, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import ValidationError

from app.core.logger import logger
from app.schemas.csv_import_schema import CombinedCSVRow
from app.models.db_models import Employee, Report
from app.services.csv.error_handler import ImportErrorHandler, ErrorCategory
from app.services.vector_store_service import add_report_to_vector_store


class RowProcessor:
    """
    Processes CSV rows into database operations using pandas and bulk SQLAlchemy operations.
    """
    
    def __init__(self, db: Session, error_handler: ImportErrorHandler):
        """
        Initialize with a database session and error handler.
        
        Args:
            db: SQLAlchemy database session
            error_handler: Error handler for collecting errors
        """
        self.db = db
        self.error_handler = error_handler
        self.employees_created = 0
        self.employees_updated = 0
        self.reports_created = 0
        self.reports_updated = 0
        self._existing_employee_ids = None
        
    def _get_existing_employee_id_map(self) -> Dict[str, int]:
        """
        Build a map of employee names to IDs for existing employees.
        Used for efficient lookups during processing.
        
        Returns:
            Dictionary mapping employee names to their IDs
        """
        if self._existing_employee_ids is None:
            self._existing_employee_ids = {}
            
            # Query all employees to build the map
            employees = self.db.query(Employee.id, Employee.name).all()
            for emp_id, emp_name in employees:
                self._existing_employee_ids[emp_name.lower()] = emp_id
                
        return self._existing_employee_ids
        
    def _find_employee_by_name(self, name: str) -> Optional[int]:
        """
        Find an employee by name (case-insensitive).
        
        Args:
            name: Employee name to search for
            
        Returns:
            Employee ID if found, None otherwise
        """
        return self._get_existing_employee_id_map().get(name.lower())
        
    def _does_report_exist(self, employee_id: int, report_date: datetime.date) -> bool:
        """
        Check if a report already exists for this employee on this date.
        
        Args:
            employee_id: Employee ID
            report_date: Report date
            
        Returns:
            True if a report exists, False otherwise
        """
        return self.db.query(Report).filter(
            Report.employee_id == employee_id,
            Report.report_date == report_date
        ).first() is not None
        
    def process_dataframe(self, df: pd.DataFrame, start_row_number: int = 1, pre_cleaned: bool = True) -> Tuple[int, int]:
        """
        Process a DataFrame of rows in bulk.
        
        Args:
            df: Pandas DataFrame with CSV data
            start_row_number: Starting row number for error reporting
            pre_cleaned: Whether the DataFrame has already been cleaned (NaN → None)
            
        Returns:
            Tuple of (successful_rows, total_rows)
        """
        if df.empty:
            return 0, 0
            
        # Track metrics
        successful_rows = 0
        total_rows = len(df)
        
        # Validate all rows with Pydantic (vectorized operations)
        validated_rows = []
        invalid_rows = []
        
        for idx, row in df.iterrows():
            row_number = start_row_number + idx
            try:
                if pre_cleaned:
                    # Data is already cleaned by PandasCSVReader.read_dataframes
                    row_dict = row.to_dict()
                else:
                    # Clean data - replace nan with None
                    row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                
                validated_data = CombinedCSVRow(**row_dict)
                validated_rows.append((row_number, validated_data.model_dump()))
            except ValidationError as e:
                # Add to invalid rows
                invalid_rows.append((row_number, row.to_dict(), e))
                # Record validation errors
                for error in e.errors():
                    field = error.get("loc", ["unknown"])[0]
                    message = error.get("msg", "Unknown validation error")
                    self.error_handler.add_validation_error(
                        row_number=row_number,
                        error_message=message,
                        field_name=str(field),
                        row_data=row.to_dict()
                    )
        
        if not validated_rows:
            return 0, total_rows
            
        # Process employees in bulk
        emp_success = self._bulk_process_employees([row for _, row in validated_rows])
        
        # Process reports in bulk (for rows where employee processing succeeded)
        if emp_success:
            rep_success = self._bulk_process_reports([row for _, row in validated_rows])
            successful_rows = len(validated_rows)
        
        return successful_rows, total_rows
    
    def _bulk_process_employees(self, validated_rows: List[Dict[str, Any]]) -> bool:
        """Process employees in bulk using SQLAlchemy core operations."""
        try:
            # If all rows have Employee_ID, we can simplify the logic
            for row in validated_rows:
                emp_id = row.get('Employee_ID')
                if not emp_id:
                    logger.warning(f"Row missing Employee_ID: {row['Name']}. Skipping employee update.")
                    continue
                
                # Update existing employee by ID
                existing_emp = self.db.query(Employee).filter(Employee.id == emp_id).first()
                if existing_emp:
                    existing_emp.position = row['Designation']
                    existing_emp.wing = row.get('department', 'Unspecified')
                    self.employees_updated += 1
                else:
                    # Employee ID provided but not found - create new employee with specified ID
                    new_employee = Employee(
                        id=emp_id,
                        name=row['Name'],
                        position=row['Designation'],
                        wing=row.get('department', 'Unspecified')
                    )
                    self.db.add(new_employee)
                    self.db.flush()
                    self.employees_created += 1
            
            self.db.flush()
            return True
        except Exception as e:
            logger.error(f"Bulk employee processing failed: {str(e)}")
            self.db.rollback()  # Add rollback here for consistency with _bulk_process_reports
            return False
    
    def _bulk_process_reports(self, validated_rows: List[Dict[str, Any]]) -> bool:
        """Process reports in bulk using SQLAlchemy core operations."""
        try:
            report_data = []
            
            for row in validated_rows:
                # Check if "nothing to report" is set
                if row.get('NTR') and row['NTR'].strip() and row['NTR'].strip().upper() != 'NULL':
                    continue
                
                # Ensure proper date field handling - check both capitalization versions
                start_date = row.get('From') or row.get('from')
                report_date = row.get('To') or row.get('to')
                
                # Construct report text from fields - check both naming conventions
                report_text = "\n\n".join([
                    f"Tasks Completed: {row.get('Tasks_Completed') or row.get('tasks_completed', 'N/A')}",
                    f"Impact: {row.get('Impact') or row.get('impact', 'N/A')}",
                    f"Challenges: {row.get('Challenges') or row.get('challenges', 'N/A')}",
                    f"Support Required: {row.get('Support_Required') or row.get('support_required', 'N/A')}",
                    f"Tasks Planned: {row.get('Tasks_Planned') or row.get('tasks_planned', 'N/A')}",
                    f"Confidence Level: {row.get('Confidence_Level') or row.get('confidence_level', 'N/A')}",
                    f"Report Period: {start_date} to {report_date}"
                ])
                
                # Map to database properly, get employee ID from the right field
                emp_id = row.get('Employee_ID') or row.get('employee_id')
                if not emp_id:
                    # This should have been handled in validation, but as a safeguard
                    logger.warning(f"Missing employee ID in row: {row}")
                    continue
                    
                report_data.append({
                    'employee_id': emp_id,
                    'report_date': report_date,
                    'report_text': report_text
                })
            
            # Skip if no reports to process
            if not report_data:
                return True
                
            stmt = pg_insert(Report.__table__).values(report_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['employee_id', 'report_date'],
                set_={
                    'report_text': stmt.excluded.report_text
                }
            )
            
            result = self.db.execute(stmt)
            # Flush to get IDs for newly created reports
            self.db.flush()
            
            self.reports_created += result.rowcount
            
            # Collect all reports for vector store processing in one batch
            reports_for_vector_store = []
            
            # Query for all the reports we just inserted/updated
            for data in report_data:
                report = self.db.query(Report).filter(
                    Report.employee_id == data['employee_id'],
                    Report.report_date == data['report_date']
                ).first()
                
                if report:
                    reports_for_vector_store.append({
                        "report_id": str(report.report_id),
                        "employee_id": report.employee_id,
                        "report_date": str(report.report_date),
                        "report_text": report.report_text
                    })
            
            # Process all reports in a single batch call to vector store
            if reports_for_vector_store:
                try:
                    add_report_to_vector_store(
                        reports=reports_for_vector_store,
                        session=self.db
                    )
                    logger.info(f"Added {len(reports_for_vector_store)} reports to vector store in batch")
                except Exception as ve:
                    # Log but don't fail the import if vector store fails
                    logger.warning(f"Failed to add reports to vector store in batch: {str(ve)}")
            
            # Now commit the entire transaction after all vector store operations
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Bulk report processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def get_metrics(self) -> Dict[str, int]:
        """Get processing metrics."""
        return {
            "employees_created": self.employees_created,
            "employees_updated": self.employees_updated,
            "reports_created": self.reports_created,
            "reports_updated": self.reports_updated
        }
    
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single CSV row.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Validate row data using Pydantic model
            validated_data = CombinedCSVRow(**row_data)
            row_dict = validated_data.model_dump()
            
            # Process employee using the same approach as bulk processing
            emp_id = row_dict.get('Employee_ID')
            if emp_id:
                # Update existing employee by ID
                existing_emp = self.db.query(Employee).filter(Employee.id == emp_id).first()
                if existing_emp:
                    existing_emp.position = row_dict['Designation']
                    existing_emp.wing = row_dict.get('department', 'Unspecified')
                    self.employees_updated += 1
                else:
                    # Employee ID provided but not found - create new employee with specified ID
                    new_employee = Employee(
                        id=emp_id,
                        name=row_dict['Name'],
                        position=row_dict['Designation'],
                        wing=row_dict.get('department', 'Unspecified')
                    )
                    self.db.add(new_employee)
                    self.db.flush()
                    self.employees_created += 1
            else:
                # Missing employee ID - cannot process
                self.error_handler.add_validation_error(
                    row_number=row_number,
                    error_message="Missing Employee_ID field",
                    row_data=row_data
                )
                return False
            
            # Process report if needed (not "nothing to report")
            if not (row_dict.get('NTR') and row_dict['NTR'].strip() and row_dict['NTR'].strip().upper() != 'NULL'):
                # Ensure proper date field handling
                start_date = row_dict.get('From') or row_dict.get('from')
                report_date = row_dict.get('To') or row_dict.get('to')
                
                # Construct report text
                report_text = "\n\n".join([
                    f"Tasks Completed: {row_dict.get('Tasks_Completed') or row_dict.get('tasks_completed', 'N/A')}",
                    f"Impact: {row_dict.get('Impact') or row_dict.get('impact', 'N/A')}",
                    f"Challenges: {row_dict.get('Challenges') or row_dict.get('challenges', 'N/A')}",
                    f"Support Required: {row_dict.get('Support_Required') or row_dict.get('support_required', 'N/A')}",
                    f"Tasks Planned: {row_dict.get('Tasks_Planned') or row_dict.get('tasks_planned', 'N/A')}",
                    f"Confidence Level: {row_dict.get('Confidence_Level') or row_dict.get('confidence_level', 'N/A')}",
                    f"Report Period: {start_date} to {report_date}"
                ])
                
                # Check for existing report
                existing_report = self.db.query(Report).filter(
                    Report.employee_id == emp_id,
                    Report.report_date == report_date
                ).first()
                
                if existing_report:
                    # Update existing report
                    existing_report.report_text = report_text
                    self.reports_updated += 1
                    report_id = existing_report.report_id
                else:
                    # Create new report
                    new_report = Report(
                        employee_id=emp_id,
                        report_date=report_date,
                        report_text=report_text
                    )
                    self.db.add(new_report)
                    self.db.flush()  # Need to flush to get the report_id
                    self.reports_created += 1
                    report_id = new_report.report_id
                
                # Add to vector store
                try:
                    # Pass the session to vector store function
                    add_report_to_vector_store(
                        report_id=str(report_id),
                        employee_id=emp_id,
                        report_date=str(report_date),
                        report_text=report_text,
                        session=self.db
                    )
                except Exception as ve:
                    # Log but don't fail the import if vector store fails
                    logger.warning(f"Failed to add report {report_id} to vector store: {str(ve)}")
            
            self.db.commit()  # Commit after vector store operations
            return True
            
        except ValidationError as e:
            # Handle validation errors
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing row {row_number}: {str(e)}\n{traceback.format_exc()}")
            self.error_handler.add_processing_error(
                row_number=row_number,
                row_data=row_data,
                error_message=f"Unexpected error: {str(e)}",
                exception=e
            )
            return False