"""
Employee Report Processor

Handles the transformation and processing of employee report CSV rows into database operations.
"""
from typing import Dict, Any, Tuple, List
import pandas as pd
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.services.csv.processors.base import BaseCSVProcessor
from app.services.csv.row_models import CombinedCSVRow
from app.models.db_models import Employee, Report
from app.services.csv.error_handler import ImportErrorHandler
from app.services.vector_store_service import add_report_to_vector_store
from app.core.logger import logger


class EmployeeReportProcessor(BaseCSVProcessor):
    """
    Processes employee report CSV rows into database operations.
    """

    row_model = CombinedCSVRow
    
    # Required headers for employee report CSV format
    REQUIRED_HEADERS = [
        "Employee_ID", "Name", "Designation", "From", "To", 
        "Tasks_Completed", "Impact", "Challenges", "Support_Required", 
        "Tasks_Planned", "Confidence_Level"
    ]
    
    # Additional optional headers
    OPTIONAL_HEADERS = ["BPS", "Office_Hierarchy", "Draft", "NTR"]
    
    def __init__(self, db: Session, error_handler: ImportErrorHandler):
        """Initialize the processor."""
        super().__init__(db, error_handler)
        self.employees_created = 0
        self.employees_updated = 0
        self.reports_created = 0
        self.reports_updated = 0
        self.vector_store_failures = 0  # reports saved but not added to the vector store
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
    
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single employee report CSV row.
        
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
                    existing_emp.position = row_dict['Designation'] + f" ({row_dict['BPS']})"
                    existing_emp.wing = row_dict['Office_Hierarchy']
                    self.employees_updated += 1
                else:
                    # Employee ID provided but not found - create new employee with specified ID
                    new_employee = Employee(
                        id=emp_id,
                        name=row_dict['Name'],
                        position=row_dict['Designation'] + f" ({row_dict['BPS']})", 
                        wing=row_dict['Office_Hierarchy']
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
                    added = add_report_to_vector_store(
                        report_id=str(report_id),
                        employee_id=emp_id,
                        report_date=str(report_date),
                        report_text=report_text,
                        session=self.db
                    )
                except Exception as ve:
                    logger.warning(f"Failed to add report {report_id} to vector store: {str(ve)}")
                    added = False
                if not added:
                    # The report is kept; the failure is reported instead of passing as success
                    self._record_vector_store_failure(1, row_number)
            
            self.db.commit()  # Commit after vector store operations
            self.successful_rows += 1
            return True
            
        except ValidationError as e:
            # Handle validation errors
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing row {row_number}: {str(e)}")
            self.error_handler.add_processing_error(
                row_number=row_number,
                row_data=row_data,
                error_message=f"Unexpected error: {str(e)}",
                exception=e
            )
            return False
    
    def process_dataframe(self, df: pd.DataFrame, start_row_number: int = 1, pre_cleaned: bool = True) -> Tuple[int, int]:
        """
        Process a DataFrame of employee report rows in bulk.
        
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
        
        # NEW: De-duplicate based on (Employee_ID, To) before processing
        original_count = len(df)
        
        # Check if 'To' column exists (it should for employee reports)
        if 'Employee_ID' in df.columns and 'To' in df.columns:
            # Keep the last occurrence of each (Employee_ID, To) combination
            df = df.drop_duplicates(subset=['Employee_ID', 'To'], keep='last')
            
            deduplicated_count = len(df)
            if original_count > deduplicated_count:
                logger.warning(f"Removed {original_count - deduplicated_count} duplicate rows from chunk based on (Employee_ID, To). Kept last occurrence.")
        
        # Track metrics
        successful_rows = 0
        total_rows = len(df)
        
        # Validate all rows with Pydantic (vectorized operations)
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
                
                validated_data = CombinedCSVRow(**row_dict)
                validated_rows.append((row_number, validated_data.model_dump()))
            except ValidationError as e:
                # Add to invalid rows
                invalid_rows.append((row_number, row.to_dict(), e))
                # Record validation errors
                for error in e.errors():
                    loc = error.get("loc") or ()
                    message = error.get("msg", "Unknown validation error")
                    self.error_handler.add_validation_error(
                        row_number=row_number,
                        error_message=message,
                        # A model-level check (e.g. From after To) has no field
                        field_name=str(loc[0]) if loc else None,
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
            self.successful_rows += successful_rows
            
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
                    existing_emp.position = row['Designation'] + f" ({row['BPS']})"
                    existing_emp.wing = row['Office_Hierarchy']
                    self.employees_updated += 1
                else:
                    # Employee ID provided but not found - create new employee with specified ID
                    new_employee = Employee(
                        id=emp_id,
                        name=row['Name'],
                        position=row['Designation'] + f" ({row['BPS']})",
                        wing=row['Office_Hierarchy']
                    )
                    self.db.add(new_employee)
                    self.db.flush()
                    self.employees_created += 1
            
            self.db.flush()
            return True
        except Exception as e:
            logger.error(f"Bulk employee processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def _bulk_process_reports(self, validated_rows: List[Dict[str, Any]]) -> bool:
        """Process reports in bulk using SQLAlchemy core operations."""
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy import tuple_
            
            report_data = []
            # Track seen (employee_id, report_date) combinations to avoid duplicates
            seen_combinations = set()
            
            for row in validated_rows:
                # Check if "nothing to report" is set
                if row.get('NTR') and row['NTR'].strip() and row['NTR'].strip().upper() != 'NULL':
                    continue
                
                # Ensure proper date field handling - check both capitalization versions
                start_date = row.get('From') or row.get('from')
                report_date = row.get('To') or row.get('to')
                
                # Get employee ID from the right field
                emp_id = row.get('Employee_ID') or row.get('employee_id')
                if not emp_id:
                    # This should have been handled in validation, but as a safeguard
                    logger.warning(f"Missing employee ID in row: {row}")
                    continue
                
                # Check for duplicate (employee_id, report_date) in this batch
                combination_key = (emp_id, report_date)
                if combination_key in seen_combinations:
                    logger.warning(f"Duplicate report found in batch for employee {emp_id} on {report_date}. Using the last occurrence.")
                    # Remove the previous entry for this combination
                    report_data = [r for r in report_data if not (r['employee_id'] == emp_id and r['report_date'] == report_date)]
                
                # Mark this combination as seen
                seen_combinations.add(combination_key)
                
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
                
                # Add report data directly using emp_id we already extracted
                report_data.append({
                    'employee_id': emp_id,
                    'report_date': report_date,
                    'report_text': report_text
                })
            
            # Skip if no reports to process
            if not report_data:
                return True
            
            # Query for existing reports BEFORE upsert
            report_keys = [(r['employee_id'], r['report_date']) for r in report_data]
            existing_reports = self.db.query(
                Report.employee_id,
                Report.report_date
            ).filter(
                tuple_(Report.employee_id, Report.report_date).in_(report_keys)
            ).all()
            
            # Convert to set for fast lookup
            existing_set = {(emp_id, rep_date) for emp_id, rep_date in existing_reports}
            existing_count = len(existing_set)
            new_count = len(report_data) - existing_count
            
            logger.info(f"Pre-upsert check: {existing_count} existing reports, {new_count} new reports")
            
            # Log statistics about duplicates
            original_count = len(validated_rows) - len([r for r in validated_rows if r.get('NTR') and r['NTR'].strip() and r['NTR'].strip().upper() != 'NULL'])
            deduplicated_count = len(report_data)
            if original_count > deduplicated_count:
                logger.info(f"Removed {original_count - deduplicated_count} duplicate reports from batch (kept latest occurrence)")
                
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
            
            # Accurately track created vs updated
            self.reports_created += new_count
            self.reports_updated += existing_count
            
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
                    added = add_report_to_vector_store(
                        reports=reports_for_vector_store,
                        session=self.db
                    )
                except Exception as ve:
                    logger.warning(f"Failed to add reports to vector store in batch: {str(ve)}")
                    added = False
                if added:
                    logger.info(f"Added {len(reports_for_vector_store)} reports to vector store in batch")
                else:
                    # The reports are kept; the failure is reported instead of passing as success
                    self._record_vector_store_failure(len(reports_for_vector_store))
            
            # Now commit the entire transaction after all vector store operations
            self.db.commit()
            logger.info(f"Bulk processed {len(report_data)} reports ({new_count} created, {existing_count} updated)")
            return True
            
        except Exception as e:
            logger.error(f"Bulk report processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def _record_vector_store_failure(self, report_count: int, row_number: int = 0) -> None:
        """Count reports that were saved but not added to the vector store, and report it as an error."""
        self.vector_store_failures += report_count
        self.error_handler.add_processing_error(
            row_number=row_number,
            error_message=(
                f"{report_count} report(s) were saved but could not be added to the vector store, "
                "so analyses will not find them as similar reports. Import the file again to retry."
            ),
        )

    def get_metrics(self) -> Dict[str, int]:
        """Get processing metrics."""
        return {
            "employees_created": self.employees_created,
            "employees_updated": self.employees_updated,
            "reports_created": self.reports_created,
            "reports_updated": self.reports_updated,
            "vector_store_failures": self.vector_store_failures,
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
        
        For employee reports, we need at least Name, Designation, From, To, and Tasks_Completed.
        """
        essential_headers = ["Name", "Designation", "From", "To", "Tasks_Completed"]
        return all(header in headers for header in essential_headers)
