from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from app.services.csv.row_models import (  # noqa: F401  (re-exported for compatibility)
    CombinedCSVRow,
    _top_level_split,
    _json_list_with_fixes,
    VisionDataCSVRow,
    JobDescriptionCSVRow,
    SupervisorFeedbackCSVRow,
)

class CSVImportOptions(BaseModel):
    """Options for CSV import process."""
    chunk_size: int = Field(default=1000, description="Size of chunks for processing")
    dry_run: bool = Field(default=False, description="Validate without writing to database")
    stop_on_error: bool = Field(default=False, description="Stop on first error")
    error_threshold_percent: float = Field(default=10.0, description="Max percentage of errors before aborting")
    
    # Option for selecting processing mode
    processing_mode: Literal["row_by_row", "bulk"] = Field(
        default="row_by_row", 
        description="Processing mode: row_by_row (memory efficient) or bulk (faster)"
    )
    
    # Option for file size threshold to auto-select mode
    auto_mode_selection: bool = Field(
        default=True,
        description="Automatically select processing mode based on file size"
    )
    file_size_threshold_mb: float = Field(
        default=10.0, 
        description="File size in MB above which row_by_row mode is used"
    )
    
    file_format: Literal["csv", "txt", "tsv", "auto"] = Field(
        default="auto",
        description="File format: csv (comma), txt (tab), tsv (tab), or auto (detect)"
    )
    
    delimiter: Optional[str] = Field(
        default=None,
        description="Field delimiter character (comma, tab, pipe, etc.). None means auto-detect."
    )
    
    encoding: Optional[str] = Field(
        default=None,
        description="File encoding (utf-8, utf-16, etc.). None means auto-detect."
    )


class CSVImportJobCreate(BaseModel):
    """Schema for creating a new CSV import job."""
    filename: str = Field(
        description="Original filename of the uploaded CSV"
    )
    options: Optional[CSVImportOptions] = Field(
        default=None,
        description="Import options controlling behavior"
    )
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Check if filename has valid CSV extension."""
        if not v.lower().endswith('.csv'):
            raise ValueError("File must have a .csv extension")
        return v

class CSVImportJobResponse(BaseModel):
    """
    Schema for CSV import job response.
    
    Returns comprehensive information about an import job,
    including progress statistics and status.
    """
    job_id: str = Field(description="Unique identifier for the import job")
    filename: str = Field(description="Original filename of the CSV")
    status: str = Field(description="Current status of the import job")
    csv_type: Optional[str] = Field(None, description="Type of CSV data being imported")
    submitted_at: datetime = Field(description="When the job was submitted")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing finished")
    
    # Progress metrics
    total_rows: int = Field(description="Total number of rows in the CSV")
    processed_rows: int = Field(description="Number of rows processed so far")
    successful_rows: int = Field(description="Number of rows successfully imported")
    error_count: int = Field(description="Number of rows with errors")
    
    # Type-specific metrics
    metrics: Optional[Dict[str, Any]] = Field(None, description="Type-specific detailed metrics")
    
    # Calculated fields
    percent_complete: float = Field(description="Percentage of processing completed")
    estimated_time_remaining: Optional[str] = Field(
        None, 
        description="Estimated time to completion (if available)"
    )
    
    @field_validator('percent_complete', mode='before')
    @classmethod
    def calculate_percent_complete(cls, v, info):
        """Calculate the percentage of processing completed."""
        data = info.data
        total = data.get('total_rows', 0)
        processed = data.get('processed_rows', 0)
        
        if total <= 0:
            return 0.0
            
        return round((processed / total) * 100, 1)
    
    model_config = {
        "from_attributes": True
    }

class ImportErrorResponse(BaseModel):
    """
    Schema for a single import error.
    
    Provides detailed information about an error encountered
    during CSV import processing.
    """
    row_number: int = Field(description="Row number in the CSV file (1-based)")
    field_name: Optional[str] = Field(
        None, 
        description="Name of the field with the error, or None for row-level errors"
    )
    error_message: str = Field(description="Detailed error message")
    row_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Original data from the row that failed"
    )
    
    model_config = {
        "from_attributes": True
    }

class ImportErrorsResponse(BaseModel):
    """
    Schema for paginated list of import errors.
    
    Returns a paginated collection of errors from an import job.
    """
    total: int = Field(description="Total number of errors")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of errors per page")
    errors: List[ImportErrorResponse] = Field(description="List of errors on this page")
    

    model_config = {
        "from_attributes": True
    }


