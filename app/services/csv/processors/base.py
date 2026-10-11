"""
Base CSV Processor Interface

This module defines the abstract base class that all CSV processors must implement.
The Strategy Pattern allows for different CSV formats to be processed using the same interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Set
import pandas as pd
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.services.csv.error_handler import ImportErrorHandler
from app.repositories.employees import all_employee_ids
from app.core.logger import logger


class BaseCSVProcessor(ABC):
    """
    Abstract base class for CSV row processors.
    
    Implements the Strategy Pattern to allow different CSV formats
    to be processed using a consistent interface.
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
        self._initialize_metrics()
    
    def _get_existing_employee_ids(self) -> Set[int]:
        """IDs of all employees, read once per processor; rows for other employees are rejected."""
        if getattr(self, "_existing_employee_ids", None) is None:
            self._existing_employee_ids = all_employee_ids(self.db)
            logger.info(f"Cached {len(self._existing_employee_ids)} existing employee IDs for {self.__class__.__name__}")
        return self._existing_employee_ids

    def _record_unsaved_rows(self, rows: List[Tuple[int, Dict[str, Any]]], exception: Exception = None) -> None:
        """Record a database error for each (row_number, row) a failed bulk write did not save."""
        for row_number, row_data in rows:
            self.error_handler.add_database_error(
                row_number=row_number,
                error_message="Not saved: the database write for its batch failed (see the server logs). "
                              "Importing or syncing it again retries it.",
                row_data=row_data,
                exception=exception,
            )

    def _initialize_metrics(self):
        """Initialize processing metrics. Override as needed in subclasses."""
        # Base metrics that all processors should track
        self.processed_rows = 0
        self.successful_rows = 0
    
    # Pydantic model for one CSV row; set by each processor
    row_model = None

    def validate_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Check a row without writing anything (used by dry runs).

        Returns:
            True if the row is valid; otherwise the errors are recorded and False is returned
        """
        return self._validate_model(row_data, row_number) is not None

    def _validate_model(self, row_data: Dict[str, Any], row_number: int):
        """The validated row model, or None after recording its validation errors."""
        try:
            return self.row_model(**row_data)
        except ValidationError as e:
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return None

    @abstractmethod
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single CSV row.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, int]:
        """
        Get processing metrics.
        
        Returns:
            Dictionary of metrics (counts of various operations performed)
        """
        pass
    
    @abstractmethod
    def get_required_headers(self) -> List[str]:
        """
        Get the list of required headers for this processor.
        
        Returns:
            List of header names that must be present in the CSV
        """
        pass
    
    @classmethod
    @abstractmethod
    def can_process(cls, headers: List[str]) -> bool:
        """
        Determine if this processor can handle a CSV with the given headers.
        
        Args:
            headers: List of headers from the CSV file
            
        Returns:
            True if this processor can handle the CSV, False otherwise
        """
        pass
