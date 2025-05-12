"""
Error Handler Component
"""
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from pydantic import ValidationError

from app.core.logger import logger
from app.models.import_models import ImportError


class ErrorCategory(str, Enum):
    """Categories of errors encountered during CSV import."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    DATABASE = "database"
    SYSTEM = "system"
    OTHER = "other"


@dataclass
class ErrorInfo:
    """Structured information about an error."""
    row_number: int
    field_name: Optional[str]
    error_message: str
    row_data: Optional[Dict[str, Any]]
    category: ErrorCategory
    exception: Optional[Exception] = None


class ImportErrorHandler:
    """
    Handles error collection and reporting during CSV import process.
    
    Features:
    - Collects and categorizes errors
    - Maps errors to database model
    - Provides error statistics and reporting
    - Tracks error thresholds
    """
    
    def __init__(self):
        self.errors: List[ErrorInfo] = []
        
    def add_error(self, 
                  row_number: int, 
                  error_message: str, 
                  field_name: Optional[str] = None,
                  row_data: Optional[Dict[str, Any]] = None,
                  category: ErrorCategory = ErrorCategory.OTHER,
                  exception: Optional[Exception] = None) -> None:
        """
        Add an error to the collection.
        
        Args:
            row_number: Row number from the CSV file (1-based)
            error_message: Description of the error
            field_name: Name of the field with the error, if applicable
            row_data: The row data that caused the error
            category: Category of the error
            exception: Original exception, if applicable
        """
        error = ErrorInfo(
            row_number=row_number,
            field_name=field_name,
            error_message=error_message,
            row_data=row_data,
            category=category,
            exception=exception
        )
        
        logger.debug(f"Error in row {row_number}{'.' + field_name if field_name else ''}: {error_message}")
        self.errors.append(error)
        
    def add_validation_error(self, 
                           row_number: int, 
                           error_message: str, 
                           field_name: Optional[str] = None,
                           row_data: Optional[Dict[str, Any]] = None) -> None:
        """Add a validation error."""
        self.add_error(
            row_number=row_number,
            error_message=error_message,
            field_name=field_name,
            row_data=row_data,
            category=ErrorCategory.VALIDATION
        )
        
    def add_processing_error(self, 
                           row_number: int, 
                           error_message: str, 
                           field_name: Optional[str] = None,
                           row_data: Optional[Dict[str, Any]] = None,
                           exception: Optional[Exception] = None) -> None:
        """Add a processing error."""
        self.add_error(
            row_number=row_number,
            error_message=error_message,
            field_name=field_name,
            row_data=row_data,
            category=ErrorCategory.PROCESSING,
            exception=exception
        )
        
    def add_database_error(self, 
                         row_number: int, 
                         error_message: str,
                         row_data: Optional[Dict[str, Any]] = None,
                         exception: Optional[Exception] = None) -> None:
        """Add a database error."""
        self.add_error(
            row_number=row_number,
            error_message=error_message,
            field_name=None,  # Database errors typically affect the whole row
            row_data=row_data,
            category=ErrorCategory.DATABASE,
            exception=exception
        )
        
    def clear(self) -> None:
        """Clear all errors."""
        self.errors = []
        
    def get_error_count(self) -> int:
        """Get the total number of errors."""
        return len(self.errors)
        
    def get_error_count_by_category(self) -> Dict[ErrorCategory, int]:
        """Get the count of errors by category."""
        counts = {category: 0 for category in ErrorCategory}
        for error in self.errors:
            counts[error.category] += 1
        return counts
        
    def get_error_percentage(self, total_rows: int) -> float:
        """
        Calculate the percentage of rows with errors.
        
        Args:
            total_rows: Total number of rows processed
            
        Returns:
            Percentage of rows with errors (0-100)
        """
        if total_rows <= 0:
            return 0.0
            
        # Count unique row numbers with errors
        rows_with_errors = len(set(error.row_number for error in self.errors))
        return (rows_with_errors / total_rows) * 100
        
    def to_db_models(self, job_id: str) -> List[ImportError]:
        """
        Convert errors to database models.
        
        Args:
            job_id: ID of the import job
            
        Returns:
            List of ImportError models for database insertion
        """
        return [
            ImportError(
                job_id=job_id,
                row_number=error.row_number,
                field_name=error.field_name,
                error_message=error.error_message,
                row_data=error.row_data
            )
            for error in self.errors
        ]
        
    def should_abort(self, 
                   total_rows: int, 
                   error_threshold_percent: float = 10.0,
                   stop_on_error: bool = False) -> Tuple[bool, str]:
        """
        Determine if processing should be aborted based on error thresholds.
        
        Args:
            total_rows: Total number of rows processed
            error_threshold_percent: Maximum allowed percentage of errors
            stop_on_error: Whether to stop on any error
            
        Returns:
            Tuple of (should_abort, reason)
        """
        if stop_on_error and self.get_error_count() > 0:
            return True, "Stopping due to stop_on_error=True and errors were found"
            
        if total_rows > 0:
            error_percentage = self.get_error_percentage(total_rows)
            if error_percentage > error_threshold_percent:
                return True, f"Error threshold exceeded: {error_percentage:.1f}% > {error_threshold_percent:.1f}%"
                
        return False, ""
    
    def normalize_pydantic_errors(self, error: ValidationError, row_number: int, row_data: Dict[str, Any]) -> None:
        """Process Pydantic validation errors into standardized format."""
        for err in error.errors():
            field_path = ".".join(str(loc) for loc in err.get("loc", []))
            message = err.get("msg", "Unknown validation error")
            
            self.add_validation_error(
                row_number=row_number,
                error_message=message,
                field_name=field_path if field_path else None,
                row_data=row_data
            )
    
    def get_error_summary_by_field(self) -> Dict[str, int]:
        """Get count of errors by field name."""
        summary = {}
        for error in self.errors:
            if error.field_name:
                if error.field_name not in summary:
                    summary[error.field_name] = 0
                summary[error.field_name] += 1
        return summary
    
    def get_error_patterns(self) -> Dict[str, int]:
        """Group similar errors to identify patterns."""
        patterns = {}
        for error in self.errors:
            message = error.error_message
            if message not in patterns:
                patterns[message] = 0
            patterns[message] += 1
        
        # Return top patterns by frequency
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
    
    def get_errors(self) -> List[Any]:
        """
        Get all error objects for detailed error reporting.
        Used to access error details when logging or reporting problems.
        
        Returns:
            List of error objects containing error_message, row_data, etc.
        """
        # Return the raw list of error objects that contain error_message and row_data
        # These are referenced in _process_with_pandas when generating error logs
        return self.errors if hasattr(self, 'errors') else []
