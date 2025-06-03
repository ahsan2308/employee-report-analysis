"""
Vision Data Processor

Handles the transformation and processing of Vision system data CSV rows into database operations.
"""
from typing import Dict, Any, Tuple, List, Optional, Set
import pandas as pd
import json
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.base.base_csv_processor import BaseCSVProcessor
from app.schemas.csv_import_schema import VisionDataCSVRow
from app.models.db_models import Employee
from app.models.vision_data_models import EmployeeVisionData
from app.services.csv.error_handler import ImportErrorHandler, ErrorCategory
from app.core.logger import logger


class VisionDataProcessor(BaseCSVProcessor):
    """
    Processes Vision system data CSV rows into database operations.
    """
    
    # Required headers for Vision data CSV format
    REQUIRED_HEADERS = [
        "Employee_ID", "From_Date", "To_Date", "Main_Entity", "Sub_Entities"
    ]
    
    def __init__(self, db: Session, error_handler: ImportErrorHandler):
        """Initialize the processor."""
        super().__init__(db, error_handler)
        self.vision_records_created = 0
        self.vision_records_updated = 0
        self._existing_employee_ids = None
    
    def _get_existing_employee_ids(self) -> Set[int]:
        """
        Get a set of existing employee IDs for validation.
        
        Returns:
            Set of existing employee IDs
        """
        if self._existing_employee_ids is None:
            self._existing_employee_ids = set()
            
            # Query all employee IDs
            employee_ids = self.db.query(Employee.id).all()
            self._existing_employee_ids = {emp_id[0] for emp_id in employee_ids}
                
        return self._existing_employee_ids
    
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single Vision data CSV row.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Validate row data using Pydantic model
            validated_data = VisionDataCSVRow(**row_data)
            row_dict = validated_data.model_dump()
            
            # Check if employee exists
            employee_id = row_dict.get('Employee_ID')
            if employee_id not in self._get_existing_employee_ids():
                self.error_handler.add_validation_error(
                    row_number=row_number,
                    error_message=f"Employee ID {employee_id} does not exist in the database",
                    field_name="Employee_ID",
                    row_data=row_data
                )
                return False
            
            # Parse sub-entities JSON
            sub_entities_json = row_dict.get('Sub_Entities')
            try:
                if isinstance(sub_entities_json, str):
                    sub_entities = json.loads(sub_entities_json)
                else:
                    sub_entities = sub_entities_json
            except json.JSONDecodeError:
                self.error_handler.add_validation_error(
                    row_number=row_number,
                    error_message="Invalid JSON format in Sub_Entities field",
                    field_name="Sub_Entities",
                    row_data=row_data
                )
                return False
            
            # Check for existing record
            existing_record = self.db.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.from_date == row_dict.get('From_Date'),
                EmployeeVisionData.to_date == row_dict.get('To_Date'),
                EmployeeVisionData.main_entity == row_dict.get('Main_Entity')
            ).first()
            
            if existing_record:
                # Update existing record
                existing_record.sub_entities = sub_entities
                self.vision_records_updated += 1
            else:
                # Create new record
                new_record = EmployeeVisionData(
                    employee_id=employee_id,
                    from_date=row_dict.get('From_Date'),
                    to_date=row_dict.get('To_Date'),
                    main_entity=row_dict.get('Main_Entity'),
                    sub_entities=sub_entities
                )
                self.db.add(new_record)
                self.vision_records_created += 1
            
            self.db.commit()
            self.successful_rows += 1
            return True
            
        except ValidationError as e:
            # Handle validation errors
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing Vision data row {row_number}: {str(e)}")
            self.error_handler.add_processing_error(
                row_number=row_number,
                row_data=row_data,
                error_message=f"Unexpected error: {str(e)}",
                exception=e
            )
            return False
    
    def process_dataframe(self, df: pd.DataFrame, start_row_number: int = 1, pre_cleaned: bool = True) -> Tuple[int, int]:
        """
        Process a DataFrame of Vision data rows in bulk.
        
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
        
        # Validate all rows with Pydantic
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
                
                validated_data = VisionDataCSVRow(**row_dict)
                validated_rows.append((row_number, validated_data.model_dump()))
            except ValidationError as e:
                # Add to invalid rows
                invalid_rows.append((row_number, row.to_dict(), e))
                # Record validation errors
                self.error_handler.normalize_pydantic_errors(e, row_number, row.to_dict())
        
        if not validated_rows:
            return 0, total_rows
        
        # Process validated rows in bulk
        try:
            # Collect employee IDs for existence check
            employee_ids = set(row[1]['Employee_ID'] for row in validated_rows)
            existing_employees = self._get_existing_employee_ids()
            
            # Filter out rows with non-existent employees
            valid_rows = []
            for row_number, row_dict in validated_rows:
                if row_dict['Employee_ID'] in existing_employees:
                    valid_rows.append((row_number, row_dict))
                else:
                    # Add error for non-existent employee
                    self.error_handler.add_validation_error(
                        row_number=row_number,
                        error_message=f"Employee ID {row_dict['Employee_ID']} does not exist in the database",
                        field_name="Employee_ID",
                        row_data=row_dict
                    )
            
            # Process all valid rows in bulk
            bulk_success = self._bulk_process_vision_data([row for _, row in valid_rows])
            
            if bulk_success:
                successful_rows = len(valid_rows)
                self.successful_rows += successful_rows
                
            return successful_rows, total_rows
            
        except Exception as e:
            logger.error(f"Bulk Vision data processing failed: {str(e)}")
            self.db.rollback()
            return 0, total_rows

    def _bulk_process_vision_data(self, validated_rows: List[Dict[str, Any]]) -> bool:
        """
        Process vision data records in bulk using SQLAlchemy core operations.
        
        Args:
            validated_rows: List of validated row dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            
            # Prepare data for bulk insert
            vision_data = []
            
            for row in validated_rows:
                # Parse sub-entities JSON if needed
                sub_entities_json = row.get('Sub_Entities')
                try:
                    if isinstance(sub_entities_json, str):
                        sub_entities = json.loads(sub_entities_json)
                    else:
                        sub_entities = sub_entities_json
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Sub_Entities for employee {row['Employee_ID']}: {sub_entities_json}")
                    continue
                
                # Add to bulk data
                vision_data.append({
                    'employee_id': row['Employee_ID'],
                    'from_date': row['From_Date'],
                    'to_date': row['To_Date'],
                    'main_entity': row['Main_Entity'],
                    'sub_entities': sub_entities
                })
            
            # Skip if no data to process
            if not vision_data:
                return True
                
            # Perform bulk upsert
            stmt = pg_insert(EmployeeVisionData.__table__).values(vision_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['employee_id', 'from_date', 'to_date', 'main_entity'],
                set_={
                    'sub_entities': stmt.excluded.sub_entities
                }
            )
            
            result = self.db.execute(stmt)
            self.db.flush()
            
            # Update metrics
            created_count = result.rowcount
            self.vision_records_created += created_count
            
            # Note: PostgreSQL's on_conflict_do_update doesn't distinguish between
            # inserts and updates in the rowcount, so we can't accurately track updates
            # To track updates separately, we'd need to do a pre-query to check existence
            
            self.db.commit()
            logger.info(f"Bulk processed {len(vision_data)} vision records with {created_count} created/updated")
            return True
            
        except Exception as e:
            logger.error(f"Bulk vision data processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def get_metrics(self) -> Dict[str, int]:
        """Get processing metrics."""
        return {
            "vision_records_created": self.vision_records_created,
            "vision_records_updated": self.vision_records_updated,
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
        
        For Vision data, we need Employee_ID, From_date, To_date, Main_entity, and Sub_entities.
        """
        essential_headers = ["Employee_ID", "From_Date", "To_Date", "Main_Entity", "Sub_Entities"]
        return all(header in headers for header in essential_headers)
