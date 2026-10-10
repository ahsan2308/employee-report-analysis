"""
Row Processor Component

This module provides a compatibility layer for the existing code,
delegating to the appropriate specialized processor via the factory.
"""
from typing import Dict, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
import traceback
from pydantic import ValidationError

from app.services.csv.processors.base import BaseCSVProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.services.csv.processors.processor_factory import ProcessorFactory
from app.core.logger import logger


class RowProcessor:
    """
    Row processor that delegates to specialized processors.
    
    This class maintains a consistent interface while delegating
    actual processing to the appropriate specialized processor.
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
        self._processor = None
        self._csv_type = None
        self._known_headers = None
        self.metrics = {
            "processed_rows": 0,
            "successful_rows": 0
        }
        
    def _get_processor(self, row_data: Dict[str, Any] = None, df: pd.DataFrame = None) -> BaseCSVProcessor:
        """
        Get the appropriate processor for the data format.
        
        Lazily creates the processor based on the first row or DataFrame.
        
        Args:
            row_data: Optional row data for single-row processing
            df: Optional DataFrame for bulk processing
            
        Returns:
            Appropriate processor instance
        """
        if self._processor is not None:
            return self._processor
            
        # Extract headers from the row data or DataFrame
        if row_data is not None:
            headers = list(row_data.keys())
        elif df is not None:
            headers = list(df.columns)
        else:
            raise ValueError("Either row_data or df must be provided")
            
        # Use the factory to get the appropriate processor
        self._processor, self._csv_type = ProcessorFactory.get_processor(
            headers=headers,
            db=self.db,
            error_handler=self.error_handler
        )
        
        self._known_headers = headers
        logger.info(f"Using processor: {self._processor.__class__.__name__} (csv_type: {self._csv_type})")
        
        return self._processor
    
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single CSV row.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        processor = self._get_processor(row_data=row_data)
        return processor.process_row(row_data, row_number)
    
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
        processor = self._get_processor(df=df)
        try:
            return processor.process_dataframe(df, start_row_number, pre_cleaned)
        except Exception as e:
            logger.error(f"Error processing dataframe: {str(e)}\n{traceback.format_exc()}")
            # Register error for each row in the dataframe
            first_index = df.index[0] if len(df) else 0
            for i, row in df.iterrows():
                row_number = start_row_number + (i - first_index)
                row_data = row.to_dict() if not pd.isna(row).all() else {}
                
                # Handle different error types appropriately
                if isinstance(e, ValidationError):
                    self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
                elif isinstance(e, TypeError) and "'>' not supported between" in str(e):
                    # Handle specific type comparison errors
                    self.error_handler.add_validation_error(
                        row_number=row_number,
                        error_message=f"Type error in date comparison: {str(e)}",
                        field_name="date_range",
                        row_data=row_data
                    )
                else:
                    # Generic error handling
                    self.error_handler.add_processing_error(
                        row_number=row_number,
                        error_message=str(e),
                        row_data=row_data,
                        exception=e
                    )
            
            # Update metrics to reflect processing attempt
            self.metrics["processed_rows"] += len(df)
            self.metrics["successful_rows"] += 0
            
            return 0, len(df)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get processing metrics.
        
        Returns:
            Dictionary containing metrics and CSV type
        """
        if self._processor is None:
            # No processor has been created yet, return empty metrics
            return {
                "processed_rows": 0,
                "successful_rows": 0,
                "csv_type": None,
                "metrics": {}
            }
            
        # Get metrics from the processor
        metrics = self._processor.get_metrics()
        
        # Add CSV type information
        return {
            "processed_rows": metrics.get("processed_rows", 0),
            "successful_rows": metrics.get("successful_rows", 0),
            "csv_type": self._csv_type,
            "metrics": metrics
        }