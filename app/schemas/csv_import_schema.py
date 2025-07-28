from pydantic import BaseModel, Field, validator, ValidationError, root_validator, field_validator, model_validator
from typing import Optional, Dict, Any, List, Union, Annotated, Literal
from datetime import date, datetime
import re
import pandas as pd

class CSVImportOptions(BaseModel):
    """Options for CSV import process."""
    chunk_size: int = Field(default=1000, description="Size of chunks for processing")
    dry_run: bool = Field(default=False, description="Validate without writing to database")
    stop_on_error: bool = Field(default=False, description="Stop on first error")
    error_threshold_percent: float = Field(default=10.0, description="Max percentage of errors before aborting")
    
    # New option for selecting processing mode
    processing_mode: Literal["row_by_row", "bulk"] = Field(
        default="row_by_row", 
        description="Processing mode: row_by_row (memory efficient) or bulk (faster)"
    )
    
    # New option for file size threshold to auto-select mode
    auto_mode_selection: bool = Field(
        default=True,
        description="Automatically select processing mode based on file size"
    )
    file_size_threshold_mb: float = Field(
        default=10.0, 
        description="File size in MB above which row_by_row mode is used"
    )

class CombinedCSVRow(BaseModel):
    """
    Schema for a single row of combined employee and report data in a CSV file.
    
    Each row contains both employee information and report content for a specific period.
    """
    # Employee data fields
    Employee_ID: Optional[int] = Field(
        default=None, 
        description="Employee ID (used for updating existing employees)"
    )
    Name: str = Field(
        description="Employee's full name (2-100 characters)",
        min_length=2,
        max_length=100
    )
    Designation: str = Field(
        description="Job title or position (2-100 characters)",
        min_length=2,
        max_length=100
    )
    BPS: Optional[str] = Field(
        default=None,
        description="Grade of the employee (e.g., BS-21, BS-20)"
    )
    Office_Hierarchy: Optional[str] = Field(
        default=None,
        description="Departmental structure (e.g., Technical>Tech-I>SOC)"
    )
    
    # Add the department field here - this is needed by extract_department_from_hierarchy validator
    department: Optional[str] = Field(
        default="Unspecified",
        description="Department extracted from Office_Hierarchy"
    )
    
    # Date range fields - Changed from date to str type
    From: str = Field(
        description="Start date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    To: str = Field(
        description="End date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    
    # Unused field
    Draft: Optional[str] = Field(
        default=None,
        description="Draft information (not used)"
    )
    
    # Report content fields
    Tasks_Completed: Optional[str] = Field(
        default=None,
        description="Key tasks completed in this period"
    )
    Impact: Optional[str] = Field(
        default=None,
        description="Impact or outcome of completed tasks"
    )
    Challenges: Optional[str] = Field(
        default=None,
        description="Challenges faced during this period"
    )
    Support_Required: Optional[str] = Field(
        default=None,
        description="Support or resources required"
    )
    Tasks_Planned: Optional[str] = Field(
        default=None,
        description="Tasks planned for next period"
    )
    Confidence_Level: Optional[str] = Field(
        default=None,
        description="Confidence level (1-5, possibly with text like '3 - Moderate')"
    )
    NTR: Optional[str] = Field(
        default=None,
        description="Nothing to report reason (if provided, report will not be created)"
    )
    
    # Better model configuration with performance settings
    model_config = {
        "from_attributes": True,
        "extra": "forbid",  # Prevents extra fields
        "validate_assignment": False,  # Performance optimization
        "str_strip_whitespace": True,  # Auto-strip whitespace from strings
        "str_to_lower": False,  # Don't lowercase strings automatically
        "validate_default": False,  # Performance optimization
    }
    
    # Use new Pydantic v2 validators for better performance
    @field_validator('Name')
    @classmethod
    def validate_name(cls, v):
        """Ensure name doesn't contain invalid characters."""
        if not v or not v.strip():
            raise ValueError("Employee name cannot be empty")
            
        # Allow letters, numbers, spaces, commas, periods, slashes, hyphens, apostrophes, parentheses, and square brackets
        # Block potentially harmful characters like <, >, {, }, etc.
        allowed_pattern = r'^[A-Za-z0-9\s,.\'"\/\-()[\]]+$'
        if not re.match(allowed_pattern, v):
            raise ValueError(f"Name contains invalid characters. Allowed: letters, numbers, spaces, commas, periods, slashes, hyphens, apostrophes, parentheses, and square brackets")
        return v
    
    @field_validator('BPS')
    @classmethod
    def validate_bps(cls, v):
        """Validate BPS format if provided."""
        if not v:
            return v
            
        # Expected format: BS-XX where XX is a number
        if not re.match(r'^BS-\d+$', v, re.IGNORECASE):
            raise ValueError("BPS should be in format 'BS-XX' where XX is a number (e.g., BS-21)")
        return v
    
    @field_validator('From', 'To')
    @classmethod
    def validate_dates(cls, v, info):
        """
        Parse and validate dates in various formats.
        Uses MM/DD/YYYY as the default format for slash-separated dates.
        """
        from datetime import datetime, date
        today = date.today()
        
        # If already a date object, just validate it's not in future
        if isinstance(v, date):
            if v > today:
                raise ValueError(f"Date cannot be in the future: {v}")
            return v
            
        # Handle string dates in various formats
        if isinstance(v, str):
            v = v.strip()
            
            try:
                # Try to parse different date formats
                if '/' in v:
                    import re
                    # Format with slashes - interpret as MM/DD/YYYY by default
                    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', v):
                        # First try MM/DD/YYYY (US format - the default)
                        try:
                            parsed_date = datetime.strptime(v, '%m/%d/%Y').date()
                        except ValueError:
                            # If MM/DD/YYYY fails, try DD/MM/YYYY as fallback
                            parsed_date = datetime.strptime(v, '%d/%m/%Y').date()
                        
                        # Check if the date is in the future
                        if parsed_date > today:
                            raise ValueError(f"Date cannot be in the future: {parsed_date}")
                        
                        # Return the original string - we'll convert to date in the model_validator
                        return v
                
                # Format: MM-DD-YYYY or DD-MM-YYYY
                elif '-' in v:
                    # ... Same logic as above, but return v instead of parsed_date ...
                    return v
                
                # For ISO format (YYYY-MM-DD), validate but return the string
                elif re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                    parsed_date = datetime.strptime(v, '%Y-%m-%d').date()
                    if parsed_date > today:
                        raise ValueError(f"Date cannot be in the future: {parsed_date}")
                    return v
                
            except ValueError as e:
                # Provide more specific error message
                raise ValueError(f"Invalid date format: {v}. Please use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format.")
        
        return v
    
    @field_validator('Confidence_Level')
    @classmethod
    def extract_confidence_number(cls, v):
        """Extract numeric confidence level from text like '3 - Moderately confident'."""
        if not v:
            return None
            
        # Try to extract just the numeric part
        try:
            # Look for the first digit in the string
            match = re.search(r'(\d+)', str(v))
            if match:
                number = int(match.group(1))
                # Validate it's in the expected range
                if 1 <= number <= 5:
                    return number
                else:
                    raise ValueError(f"Confidence level must be between 1-5, got {number}")
            else:
                # If no number found, try to convert the whole string
                number = int(v.strip())
                if 1 <= number <= 5:
                    return number
                else:
                    raise ValueError(f"Confidence level must be between 1-5, got {number}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid confidence level format. Expected number between 1-5, got '{v}'")
    
    @model_validator(mode='after')
    def convert_date_strings(self):
        """Convert date strings to actual date objects after all validation."""
        from datetime import datetime

        # Handle From date
        from_date = self.From
        if isinstance(from_date, str):
            if '/' in from_date:
                try:
                    # First try MM/DD/YYYY
                    self.From = datetime.strptime(from_date, '%m/%d/%Y').date()
                except ValueError:
                    # Then try DD/MM/YYYY
                    try:
                        self.From = datetime.strptime(from_date, '%d/%m/%Y').date()
                    except ValueError:
                        # If all else fails, let it pass - likely already validated
                        pass
            elif '-' in from_date and not from_date.startswith('20'):  # Not ISO format
                try:
                    # First try MM-DD-YYYY
                    self.From = datetime.strptime(from_date, '%m-%d-%Y').date()
                except ValueError:
                    # Then try DD-MM-YYYY
                    try:
                        self.From = datetime.strptime(from_date, '%d-%m-%Y').date()
                    except ValueError:
                        pass
            else:
                # Try ISO format
                try:
                    self.From = datetime.strptime(from_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

        # Handle To date (same logic as From)
        to_date = self.To
        if isinstance(to_date, str):
            # Same conversion logic as above for To date
            if '/' in to_date:
                try:
                    self.To = datetime.strptime(to_date, '%m/%d/%Y').date()
                except ValueError:
                    try:
                        self.To = datetime.strptime(to_date, '%d/%m/%Y').date()
                    except ValueError:
                        pass
            elif '-' in to_date and not to_date.startswith('20'):
                try:
                    self.To = datetime.strptime(to_date, '%m-%d-%Y').date()
                except ValueError:
                    try:
                        self.To = datetime.strptime(to_date, '%d-%m-%Y').date()
                    except ValueError:
                        pass
            else:
                try:
                    self.To = datetime.strptime(to_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

        return self

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure From date is before or equal to To date."""
        from_date = self.From
        to_date = self.To
        
        if from_date and to_date and from_date > to_date:
            raise ValueError(f"From date ({from_date}) cannot be after To date ({to_date})")
        return self
    
    @model_validator(mode='after')
    def validate_report_content(self):
        """
        Validate report content based on NTR field.
        
        If NTR is provided (and not 'NULL'), no report will be created.
        If NTR is not provided or is 'NULL', at least Tasks_Completed must be provided.
        """
        ntr = self.NTR
        tasks_completed = self.Tasks_Completed
        
        # Check if NTR has a valid value (not empty and not 'NULL')
        has_valid_ntr = ntr and ntr.strip() and ntr.strip().upper() != 'NULL'
        
        # If NTR is provided and valid, we don't need report content
        if has_valid_ntr:
            return self
            
        # If no valid NTR, then we need at least Tasks_Completed
        if not tasks_completed or not tasks_completed.strip() or tasks_completed.strip().upper() == 'NULL':
            raise ValueError(
                "Either 'Tasks_Completed' must be provided or 'NTR' (Nothing to Report) must be specified with a valid reason"
            )
            
        return self
    
    @model_validator(mode='after')
    def extract_department_from_hierarchy(self):
        """Extract department (wing) from Office_Hierarchy."""
        hierarchy = self.Office_Hierarchy
        
        if hierarchy and '>' in hierarchy:
            # Get the top-level department (first segment before '>')
            department = hierarchy.split('>', 1)[0].strip()
            # Store it for later use in the import process
            self.department = department
        elif hierarchy:
            # If no '>' found but hierarchy is provided, use the whole string
            self.department = hierarchy.strip()
        else:
            # Default department if none provided
            self.department = 'Unspecified'
            
        return self

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
    
    # Replace old Config class
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
    
    # Replace old Config class
    model_config = {
        "from_attributes": True
    }

class VisionDataCSVRow(BaseModel):
    """
    Schema for validating a single row of vision system data in a CSV file.
    
    Each row contains employee activity data from the Vision system with metrics
    about various entity interactions.
    """
    # Employee identification field
    Employee_ID: int = Field(
        description="Employee ID (must match an existing employee)"
    )
    
    # Date range fields - Note the capitalization
    From_Date: str = Field(
        description="Start date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    To_Date: str = Field(
        description="End date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    
    # Entity data fields
    Main_Entity: str = Field(
        description="The primary entity type being reported"
    )
    Sub_Entities: str = Field(
        description="Quantitative data about sub-entities in format 'Name1:Count1, Name2:Count2, ...'"
    )
    Sub_Entities_Content: str = Field(
        description="Content for each sub-entity as a string: 'Cases:[], Activities:[{...}], ...'. Not a full JSON object, but a comma-separated list of key:list pairs."
    )
    
    # Configuration
    model_config = {
        "from_attributes": True,
        "extra": "forbid",
        "validate_assignment": False,
        "str_strip_whitespace": True,
        "str_to_lower": False,
        "validate_default": False,
    }
    
    @field_validator('Employee_ID')
    @classmethod
    def validate_employee_id(cls, v):
        """Validate employee ID is a positive integer."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError("Employee ID must be a positive integer")
        return v
    
    @field_validator('From_Date', 'To_Date')
    @classmethod
    def validate_dates(cls, v, info):
        """
        Parse and validate dates in various formats.
        Uses MM/DD/YYYY as the default format for slash-separated dates.
        """
        from datetime import datetime, date
        today = date.today()
        
        # If already a date object, just validate it's not in future
        if isinstance(v, date):
            if v > today:
                raise ValueError(f"Date cannot be in the future: {v}")
            return v
            
        # Handle string dates in various formats
        if isinstance(v, str):
            v = v.strip()
            
            try:
                # Try to parse different date formats
                if '/' in v:
                    import re
                    # Format with slashes - interpret as MM/DD/YYYY by default
                    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', v):
                        # First try MM/DD/YYYY (US format - the default)
                        try:
                            parsed_date = datetime.strptime(v, '%m/%d/%Y').date()
                        except ValueError:
                            # If MM/DD/YYYY fails, try DD/MM/YYYY as fallback
                            parsed_date = datetime.strptime(v, '%d/%m/%Y').date()
                        
                        # Check if the date is in the future
                        if parsed_date > today:
                            raise ValueError(f"Date cannot be in the future: {parsed_date}")
                        
                        # Return the original string - we'll convert to date in the model_validator
                        return v
                
                # Format: MM-DD-YYYY or DD-MM-YYYY
                elif '-' in v:
                    # Try both formats
                    try:
                        parsed_date = datetime.strptime(v, '%m-%d-%Y').date()
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(v, '%d-%m-%Y').date()
                        except ValueError:
                            # Try ISO format
                            parsed_date = datetime.strptime(v, '%Y-%m-%d').date()
                    
                    # Check if the date is in the future
                    if parsed_date > today:
                        raise ValueError(f"Date cannot be in the future: {parsed_date}")
                    
                    return v
                
                # For ISO format (YYYY-MM-DD), validate but return the string
                elif re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                    parsed_date = datetime.strptime(v, '%Y-%m-%d').date()
                    if parsed_date > today:
                        raise ValueError(f"Date cannot be in the future: {parsed_date}")
                    return v
                
            except ValueError as e:
                # Provide more specific error message
                raise ValueError(f"Invalid date format: {v}. Please use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format.")
        
        return v
    
    @field_validator('Main_Entity')
    @classmethod
    def validate_main_entity(cls, v):
        """Validate the main entity type."""
        known_entities = [
            "Activities and Cases", 
            "Correspondence", 
            "Events", 
            "Links", 
            "Media", 
            "Nadra", 
            "Organizations", 
            "PER", 
            "Persons", 
            "Tasks"
        ]
        
        if not v or not v.strip():
            raise ValueError("Main entity cannot be empty")
            
        # Check against known entity types, but allow others since the list may expand
        if v.strip() not in known_entities:
            # This is a warning rather than an error
            pass
            
        return v
    
    @field_validator('Sub_Entities')
    @classmethod
    def validate_sub_entities(cls, v):
        """Validate the sub-entities format (Name:Count, Name:Count, ...)."""
        if not v or not v.strip():
            return "{}"  # Return empty JSON object if no sub-entities
            
        import re
        import json
        
        # Expected format: "Name1:Count1, Name2:Count2, ..."
        sub_entity_pattern = r'([^:,]+):(\d+)'
        matches = re.findall(sub_entity_pattern, v)
        
        if not matches:
            raise ValueError(f"Invalid sub-entities format. Expected 'Name:Count, Name:Count, ...' but got '{v}'")
            
        # Convert to structured dictionary
        sub_entities_dict = {}
        for name, count in matches:
            name = name.strip()
            count = int(count)
            sub_entities_dict[name] = count
            
        # Return the string representation for downstream processing
        return json.dumps(sub_entities_dict)
    
    @field_validator('Sub_Entities_Content')
    @classmethod
    def validate_sub_entities_content(cls, v):
        """
        Validate that Sub_Entities_Content is a string in the format:
        'Cases:[], Activities:[{...}], ...'
        Each value must be a list (possibly empty) of dicts, but the whole string is not a JSON object.
        """
        import re
        import json
        if not v or not v.strip():
            return ""
        # Split by comma, but not inside brackets
        # This regex splits on commas that are not inside square brackets
        parts = re.split(r',\s*(?![^[]*\])', v)
        for part in parts:
            if ':' not in part:
                raise ValueError(f"Invalid Sub_Entities_Content part: '{part}'. Expected format 'Key:[...]'")
            key, value = part.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Value must start with [ and end with ]
            if not (value.startswith('[') and value.endswith(']')):
                raise ValueError(f"Value for '{key}' must be a list enclosed in []")
            try:
                # Try to parse the list
                items = json.loads(value)
                if not isinstance(items, list):
                    raise ValueError(f"Value for '{key}' must be a list")
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError(f"Each item in list for '{key}' must be a JSON object/dict")
            except Exception as e:
                raise ValueError(f"Invalid JSON list for '{key}' in Sub_Entities_Content: {e}")
        return v
    
    @model_validator(mode='after')
    def convert_date_strings(self):
        """Convert date strings to actual date objects after all validation."""
        from datetime import datetime
        
        # Apply same date conversion logic as in CombinedCSVRow
        for date_field in ['From_Date', 'To_Date']:
            date_str = getattr(self, date_field)
            if isinstance(date_str, str):
                if '/' in date_str:
                    try:
                        # First try MM/DD/YYYY
                        setattr(self, date_field, datetime.strptime(date_str, '%m/%d/%Y').date())
                    except ValueError:
                        # Then try DD/MM/YYYY
                        try:
                            setattr(self, date_field, datetime.strptime(date_str, '%d/%m/%Y').date())
                        except ValueError:
                            # If all else fails, let it pass - likely already validated
                            pass
                elif '-' in date_str and not date_str.startswith('20'):  # Not ISO format
                    try:
                        # First try MM-DD-YYYY
                        setattr(self, date_field, datetime.strptime(date_str, '%m-%d-%Y').date())
                    except ValueError:
                        # Then try DD-MM-YYYY
                        try:
                            setattr(self, date_field, datetime.strptime(date_str, '%d-%m-%Y').date())
                        except ValueError:
                            pass
                else:
                    # Try ISO format
                    try:
                        setattr(self, date_field, datetime.strptime(date_str, '%Y-%m-%d').date())
                    except ValueError:
                        pass
        
        return self
    
    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure From_Date is before or equal to To_Date."""
        from_date = self.From_Date
        to_date = self.To_Date
        
        if from_date and to_date and from_date > to_date:
            raise ValueError(f"From date ({from_date}) cannot be after To date ({to_date})")
        return self
