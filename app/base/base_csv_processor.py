"""
Base CSV Processor Interface

This module defines the abstract base class that all CSV processors must implement.
The Strategy Pattern allows for different CSV formats to be processed using the same interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Optional, Set
import pandas as pd
from sqlalchemy.orm import Session

from app.services.csv.error_handler import ImportErrorHandler


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
    
    def _initialize_metrics(self):
        """Initialize processing metrics. Override as needed in subclasses."""
        # Base metrics that all processors should track
        self.processed_rows = 0
        self.successful_rows = 0
    
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
