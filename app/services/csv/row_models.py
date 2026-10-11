"""Pydantic models that validate one CSV row for each import type."""
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Any, Dict, Union
from pydantic_core import PydanticCustomError
from datetime import date, datetime
import re
from app.core.logger import logger
from app.domain.periods import parse_period_date
import json


def _assignment_date(v, label: str, format_label: str) -> str:
    """Check a job description Assigned_Date / End_Date and return it as YYYY-MM-DD.

    Accepts a date, a datetime, or a string in a format parse_period_date reads;
    the date must be between 1970-01-01 and today.
    """
    today = date.today()
    if isinstance(v, datetime):
        parsed, shown = v.date(), v.date().isoformat()
    elif isinstance(v, date):
        parsed, shown = v, v.isoformat()
    elif isinstance(v, str):
        shown = v.strip()
        try:
            parsed = parse_period_date(shown)
        except ValueError:
            raise ValueError(
                f"Invalid {format_label} format: {shown}. Please use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format."
            )
    else:
        raise ValueError(f"{label} must be a date object or string, got {type(v).__name__}")

    if parsed > today:
        raise ValueError(f"{label} cannot be in the future. Received: {shown} (Today is {today.isoformat()})")
    if parsed < date(1970, 1, 1):
        raise ValueError(f"{label} appears unreasonably old ({shown}). Dates before 1970-01-01 are not accepted.")
    return parsed.isoformat()


def _not_a_string():
    """The error a str field gives for a value of another type (kept for fields that parse strings)."""
    return PydanticCustomError('string_type', 'Input should be a valid string')


def check_period_date(v):
    """Field check shared by the report-period models (From/To, From_Date/To_Date).

    A date must not be in the future; a string must also be in a format
    parse_period_date reads, and is returned as that date.
    """
    if isinstance(v, datetime):
        # A timestamp (e.g. a SQL Server DATETIME) is checked and stored as its day
        v = v.date()
    if isinstance(v, date):
        if v > date.today():
            raise ValueError(f"Date cannot be in the future: {v}")
        return v
    if isinstance(v, str):
        v = v.strip()
        if not v:
            raise ValueError("Date is required")
        try:
            parsed = parse_period_date(v)
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Please use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format.")
        if parsed > date.today():
            raise ValueError(f"Date cannot be in the future: {parsed}")
        return parsed
    return v


def read_period_date_string(v):
    """Before-validator for a date field given as a string: only strings are accepted, as for a str field."""
    if not isinstance(v, str):
        raise _not_a_string()
    return check_period_date(v)


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
        description="Grade of the employee (e.g., BS-21, BS-20, TS-17)"
    )
    Office_Hierarchy: Optional[str] = Field(
        default=None,
        description="Departmental structure (e.g., Technical>Tech-I>SOC)"
    )
    
    # This is needed by extract_department_from_hierarchy validator
    department: Optional[str] = Field(
        default="Unspecified",
        description="Department extracted from Office_Hierarchy"
    )
    
    # Date range fields 
    From: date = Field(
        description="Start date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    To: date = Field(
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
    Confidence_Level: Optional[int] = Field(
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
        "extra": "ignore",
        "validate_assignment": False,  # Performance optimization
        "str_strip_whitespace": True,  # Auto-strip whitespace from strings
        "str_to_lower": False,  # Don't lowercase strings automatically
        "validate_default": False,  # Performance optimization
    }
    
    # Pydantic v2 validators for better performance
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
            
        # Expected format: BS-XX or TS-XX where XX is a number
        if not re.match(r'^(?:BS|TS)-\d+$', v, re.IGNORECASE):
            raise ValueError("BPS should be in format 'BS-XX' or 'TS-XX' where XX is a number (e.g., BS-21)")
        return v
    
    @field_validator('From', 'To', mode='before')
    @classmethod
    def validate_dates(cls, v, info):
        """Read a report-period date: not in the future, in a format parse_period_date accepts."""
        return read_period_date_string(v)
    
    @field_validator('Confidence_Level', mode='before')
    @classmethod
    def extract_confidence_number(cls, v):
        """Extract numeric confidence level from text like '3 - Moderately confident'."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise _not_a_string()
        v = v.strip()
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


def _top_level_split(s: str, delimiter: str = ','):
    """
    Split on delimiter only when not inside [], {}, or quotes. Handles escapes.
    """
    if s is None:
        return []
    parts, buf = [], []
    depth_square = depth_curly = 0
    in_str = False
    esc = False
    quote_char = ''
    for ch in str(s):
        if esc:
            buf.append(ch); esc = False; continue
        if ch == '\\':
            buf.append(ch); esc = True; continue
        if in_str:
            buf.append(ch)
            if ch == quote_char:
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            quote_char = ch
            buf.append(ch)
            continue
        if ch == '[': depth_square += 1
        elif ch == ']': depth_square = max(0, depth_square - 1)
        elif ch == '{': depth_curly += 1
        elif ch == '}': depth_curly = max(0, depth_curly - 1)
        if ch == delimiter and depth_square == 0 and depth_curly == 0:
            parts.append(''.join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf).strip())
    return parts


def _json_list_with_fixes(value: str):
    """
    Try to json.loads a list; if it fails, apply light fixes:
    - replace unescaped single quotes with double quotes
    - remove trailing commas before ] or }
    - strip control chars
    Returns: list | None
    """
    if value is None:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        pass

    repaired = str(value).strip()
    repaired = re.sub(r'(?<!\\)\'', '"', repaired)
    repaired = re.sub(r',\s*([\]\}])', r'\1', repaired)
    repaired = ''.join(ch for ch in repaired if ch >= ' ')

    try:
        parsed = json.loads(repaired)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None


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
    
    # Date range fields
    From_Date: date = Field(
        description="Start date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    To_Date: date = Field(
        description="End date of the reporting period (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    
    # Entity data fields
    Main_Entity: str = Field(
        description="The primary entity type being reported"
    )
    Sub_Entities: str = Field(
        description="Quantitative data about sub-entities in format 'Name1:Count1, Name2:Count2, ...'"
    )
    Sub_Entities_Content: Dict[str, list] = Field(
        description="Content for each sub-entity as a string: 'Cases:[], Activities:[{...}], ...'. Not a full JSON object, but a comma-separated list of key:list pairs."
    )
    
    # Configuration
    model_config = {
        "from_attributes": True,
        "extra": "ignore",
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
    
    @field_validator('From_Date', 'To_Date', mode='before')
    @classmethod
    def validate_dates(cls, v, info):
        """Read a report-period date: not in the future, in a format parse_period_date accepts."""
        return read_period_date_string(v)
    
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
    
    @field_validator('Sub_Entities_Content', mode='before')
    @classmethod
    def validate_sub_entities_content(cls, v):
        """
        Validate and CONVERT Sub_Entities_Content from string format to dictionary.
        
        Input format: 'Cases:[], Activities:[{...}], ...'
        Output format: {"Cases": [], "Activities": [{...}], ...}
        """
        if not isinstance(v, str):
            raise _not_a_string()
        v = v.strip()
        if not v:
            return {}  # Return empty dict instead of empty string

        parts = _top_level_split(v, delimiter=',')
        content_dict = {}
        
        for part in parts:
            if ':' not in part:
                raise ValueError(f"Invalid Sub_Entities_Content part: '{part}'. Expected format 'Key:[...]'")
            
            key, value = part.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Value must be a list (JSON array)
            if not (value.startswith('[') and value.endswith(']')):
                raise ValueError(f"Value for '{key}' must be a list enclosed in []")

            items = _json_list_with_fixes(value)
            if items is None:
                raise ValueError(f"Invalid JSON list for '{key}' in Sub_Entities_Content")
            if not isinstance(items, list):
                raise ValueError(f"Value for '{key}' must be a list")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"Each item in list for '{key}' must be a JSON object/dict")
            
            # Add the parsed list to the dictionary
            content_dict[key] = items

        # Return the dictionary instead of the string
        return content_dict
    
    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure From_Date is before or equal to To_Date."""
        from_date = self.From_Date
        to_date = self.To_Date
        
        if from_date and to_date and from_date > to_date:
            raise ValueError(f"From date ({from_date}) cannot be after To date ({to_date})")
        return self


class JobDescriptionCSVRow(BaseModel):
    """
    Pydantic validation schema for Job Description CSV rows.
    
    This schema validates job description data from both CSV imports and SQL Server sync.
    It ensures data quality before database operations.
    
    Key Validation Rules:
    - Employee_ID must be a positive integer
    - Assigned_Date is REQUIRED for accurate historical tracking
    - Job description text must be meaningful (minimum 50 characters)
    - JD_ID is flexible (accepts both numeric and string formats from SQL Server)
    - Is_Current tracks whether this is the employee's current JD
    - End_Date marks when a JD assignment ended (NULL if current)
    """
    
    # Field 1: Employee_ID (flexible: accepts int or string, converts to int)
    Employee_ID: int = Field(
        ...,
        description="Employee identifier. Accepts integer or string format.",
        gt=0,
        examples=[101]
    )
    
    # Field 2: JD_ID (always numeric, but can come as int or string)
    JD_ID: str = Field(
        ...,
        description="Job Description identifier from SQL Server. Always numeric (e.g., 1001, 1002) but may be provided as integer or string. Will be stored as string.",
        min_length=1,
        max_length=50,
        examples=["1001"]
    )
    
    # Field 3: Job_Description (minimum 50 characters for meaningful content)
    Job_Description: str = Field(
        ...,
        description="Full text of the job description. Must be at least 50 characters to ensure meaningful content.",
        min_length=50,
        examples=["Responsible for analyzing employee performance data, generating insights, and presenting findings to management. Requires proficiency in data analysis tools and strong communication skills."]
    )
    
    # Field 4: Assigned_Date (REQUIRED - no default, must be provided)
    Assigned_Date: Union[str, date, datetime] = Field(
        ...,
        description="Date when this JD was assigned to the employee in YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format. REQUIRED field - rows without this date will be rejected.",
        examples=["2024-01-15"]
    )
    
    # Field 5: is_current (REQUIRED - tracks if this is current JD)
    Is_Current: bool = Field(
        ...,
        description="Whether this is the employee's current job description. TRUE if current, FALSE if ended.",
        examples=[True]
    )
    
    # Field 6: end_date (OPTIONAL - only set if JD assignment has ended)
    End_Date: Optional[Union[str, date, datetime]] = Field(
        default=None,
        description="Date when this JD assignment ended. NULL if this is still the current role. Format: YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY.",
        examples=[None]
    )
    
    # Model configuration
    model_config = ConfigDict(
        # Allow extra fields in input (for forward compatibility)
        extra='ignore',
        
        # Automatically strip whitespace from string fields
        str_strip_whitespace=True,
        
        # Validate default values (if any added later)
        validate_default=True,
        
        # Example for OpenAPI/Swagger documentation
        json_schema_extra={
            "examples": [
                {
                    "Employee_ID": 101,
                    "JD_ID": "1001",
                    "Job_Description": "Responsible for analyzing employee performance data, generating insights, and presenting findings to management. Requires proficiency in data analysis tools and strong communication skills. Works closely with HR team to identify trends and recommend interventions.",
                    "Assigned_Date": "2024-01-15",
                    "Is_Current": True,
                    "End_Date": None
                },
                {
                    "Employee_ID": 102,
                    "JD_ID": "1002",
                    "Job_Description": "Coordinates project activities across multiple teams, manages timelines, and ensures deliverables meet quality standards. Acts as liaison between technical and business stakeholders. Facilitates communication and resolves conflicts to keep projects on track.",
                    "Assigned_Date": "2023-06-01",
                    "Is_Current": False,
                    "End_Date": "2024-05-31"
                }
            ]
        }
    )
    
    # Validator for JD_ID: Convert numeric types to string
    @field_validator('JD_ID', mode='before')
    @classmethod
    def validate_and_convert_jd_id(cls, v: Any) -> str:
        """
        Convert JD_ID to string format.
        
        JD_ID is always a numeric identifier (integer), but SQL Server may return it as:
        - Integer: 1001, 1002, etc.
        - String: "1001", "1002", etc.
        - Float: 1001.0 (unlikely but possible from some SQL drivers)
        """
        # Handle None
        if v is None:
            raise ValueError("JD_ID is required and cannot be empty")
        
        # Convert to string based on type
        if isinstance(v, int):
            jd_id = str(v)
        elif isinstance(v, float):
            if v.is_integer():
                jd_id = str(int(v))
            else:
                raise ValueError(f"JD_ID must be an integer, got float with decimal: {v}")
        elif isinstance(v, str):
            v_stripped = v.strip()
            
            # Verify it's a valid integer string
            try:
                int(v_stripped)
                jd_id = v_stripped
            except ValueError:
                raise ValueError(f"JD_ID must be numeric. Received non-numeric string: '{v_stripped}'")
        else:
            raise ValueError(f"JD_ID must be an integer or numeric string, got {type(v).__name__}")
        
        # Validate not empty after conversion
        if not jd_id:
            raise ValueError("JD_ID cannot be empty")
        
        # Validate length
        if len(jd_id) > 50:
            raise ValueError(f"JD_ID exceeds maximum length of 50 characters. Received {len(jd_id)} characters.")
        
        # Double-check it's still numeric
        try:
            int(jd_id)
        except ValueError:
            raise ValueError(f"JD_ID must be numeric. Final value '{jd_id}' is not a valid integer.")
        
        return str(jd_id)
    
    # Validator 1: Employee_ID - Convert string to int, but DON'T check if exists
    @field_validator('Employee_ID', mode='before')
    @classmethod
    def validate_and_convert_employee_id(cls, v: Any) -> int:
        """
        Convert Employee_ID from string to int if needed.
        
        
        Args:
            v: Employee ID value (int or string)
            
        Returns:
            The validated employee ID as integer
            
        Raises:
            ValueError: If conversion fails or value is not positive
        """
        # Step 1: Convert to int if string
        try:
            if isinstance(v, str):
                employee_id = int(v.strip())
            elif isinstance(v, int):
                employee_id = v
            else:
                raise ValueError(f"Employee_ID must be an integer or numeric string, got {type(v).__name__}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Employee_ID must be a valid integer or numeric string. Received: '{v}'")
        
        # Step 2: Validate positive integer
        if employee_id <= 0:
            raise ValueError(f"Employee_ID must be a positive integer. Received: {employee_id}")
        
        return employee_id
    
    # Validator 2: Job_Description - Content quality validation
    @field_validator('Job_Description')
    @classmethod
    def validate_job_description_content(cls, v: str) -> str:
        """
        Validate job description content quality.
        
        Checks:
        - Not empty after stripping whitespace
        - At least 50 characters long
        - Contains letter characters (not just numbers/symbols)
        - Not placeholder text
        """
        v_stripped = v.strip()
        
        if not v_stripped:
            raise ValueError("Job description cannot be empty or only whitespace")
        
        if len(v_stripped) < 50:
            raise ValueError(
                f"Job description must be at least 50 characters long. "
                f"Received only {len(v_stripped)} characters."
            )
        
        if not any(c.isalpha() for c in v_stripped):
            raise ValueError(
                "Job description must contain actual text (letters), "
                "not just numbers or symbols"
            )
        
        # Check for placeholder text
        placeholders = [
            "lorem ipsum", "placeholder", "sample text", "test description",
            "todo", "tbd", "to be determined", "n/a", "not applicable"
        ]
        
        v_lower = v_stripped.lower()
        for placeholder in placeholders:
            if placeholder in v_lower and len(v_stripped) < 100:
                raise ValueError(
                    f"Job description appears to contain placeholder text ('{placeholder}'). "
                    f"Please provide an actual job description."
                )
        
        return v_stripped
    
    # Validator 3: Assigned_Date - Format and logic validation 
    @field_validator('Assigned_Date')
    @classmethod
    def validate_assigned_date(cls, v: Union[str, date]) -> str:
        """
        Validate assigned date format and business logic.
        
        Accepts multiple date formats:
        - YYYY-MM-DD (ISO format)
        - MM/DD/YYYY (US format)
        - DD/MM/YYYY (International format)
        - MM-DD-YYYY, DD-MM-YYYY
        
        Checks date is not in future and not unreasonably old.
        """
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("Assigned_Date is required and cannot be empty")
        return _assignment_date(v, "Assigned_Date", "date")
    
    # NEW Validator 4: end_date - Format validation (same as Assigned_Date)
    @field_validator('End_Date')
    @classmethod
    def validate_end_date(cls, v: Optional[Union[str, date]]) -> Optional[str]:
        """
        Validate end date format and business logic.
        
        Note: This validator runs AFTER normalize_end_date, so all NULL-like strings
        have already been converted to actual None.
        
        Accepts same formats as Assigned_Date:
        - YYYY-MM-DD (ISO format)
        - MM/DD/YYYY (US format)
        - DD/MM/YYYY (International format)
        - MM-DD-YYYY, DD-MM-YYYY
        
        Can be NULL (for current roles).
        """
        # NULL (or an empty string) is valid for current roles
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return _assignment_date(v, "end_date", "end_date")
    
    # NEW Validator 5: Consistency between is_current and end_date
    @model_validator(mode='after')
    def validate_is_current_end_date_consistency(self):
        """
        Validate business logic consistency between is_current and end_date.
        
        Business Rules:
        1. If Is_Current=TRUE, End_Date SHOULD be NULL
        2. If Is_Current=FALSE, End_Date SHOULD be set
        
        We LOG warnings for inconsistencies but DON'T fail validation because:
        - SQL Server is the source of truth
        - Data might be in a transition state
        - Better to import with warning than fail entire sync
        """
        is_current = self.Is_Current
        end_date = self.End_Date
        
        # Rule 1: Current roles should not have end_date
        if is_current and end_date is not None:
            logger.warning(
                f"Data inconsistency detected: Is_Current=TRUE but End_Date={end_date} is set "
                f"for Employee_ID={self.Employee_ID}, JD_ID={self.JD_ID}. "
                f"This may indicate the role ended but Is_Current flag wasn't updated in SQL Server."
            )
        
        # Rule 2: Ended roles should have end_date
        if not is_current and end_date is None:
            logger.warning(
                f"Data inconsistency detected: Is_Current=FALSE but End_Date is NULL "
                f"for Employee_ID={self.Employee_ID}, JD_ID={self.JD_ID}. "
                f"This may indicate the role ended but no End_Date was recorded in SQL Server."
            )
        
        return self
    
    # Normalizer 1: is_current - Handle text boolean and null-like values
    @field_validator('Is_Current', mode='before')
    @classmethod
    def normalize_is_current(cls, v: Any) -> bool:
        """
        Convert various boolean representations to actual bool.
        Also handles NULL-like values which default to True (current role assumption).
        
        Handles:
        - Boolean: True/False (pass-through)
        - Integer: 1→True, 0→False
        - String: "true", "True", "TRUE", "1", "yes", "Yes" → True
        - String: "false", "False", "FALSE", "0", "no", "No" → False
        - String NULL-like: "none", "null", "n/a", "na", "unknown" → True (default)
        - None: None → True (default)
        """
        # Handle actual None
        if v is None:
            logger.debug("is_current value is None, defaulting to True (current role)")
            return True
        
        # Handle boolean (already correct type)
        if isinstance(v, bool):
            return v
        
        # Handle integer (1 → True, 0 → False)
        if isinstance(v, int):
            return bool(v)
        
        # Handle string values
        if isinstance(v, str):
            v_lower = v.strip().lower()
            
            # True representations
            if v_lower in ('true', '1', 'yes', 'y'):
                return True
            
            # False representations
            if v_lower in ('false', '0', 'no', 'n'):
                return False
            
            # NULL-like values default to True (assume current role if not explicitly marked as ended)
            null_representations = {'none', 'null', 'nil', 'n/a', 'na', 'unknown', 'unspecified', 'tbd', 'todo'}
            if v_lower in null_representations:
                logger.debug(f"is_current value '{v}' treated as null, defaulting to True (current role)")
                return True
        
        # Default fallback for any other type
        logger.warning(f"Could not parse is_current value '{v}' (type: {type(v).__name__}), defaulting to True")
        return True
    
    # Normalizer 2: end_date - Handle text NULL representations BEFORE date validation
    @field_validator('End_Date', mode='before')
    @classmethod
    def normalize_end_date(cls, v: Any) -> Optional[Union[str, date]]:
        """
        Normalize text representations of NULL to actual None BEFORE date validation.
        
        This pre-validator runs BEFORE the date format validator.
        It converts text nulls like "none", "null", "n/a", etc. to actual None.
        Actual date values pass through for downstream validation.
        
        Handles:
        - None: Already None (pass-through)
        - Empty string: "" → None
        - NULL-like text: "none", "null", "n/a", "na", "unknown", "tbd", "todo", "-", "--" → None
        - Actual dates: Pass through to date validator
        """
        # Handle actual None
        if v is None:
            return None
        
        # Handle non-string types (dates, etc.) - pass through to date validator
        if not isinstance(v, str):
            return v
        
        # For strings, check for null-like values (case-insensitive)
        v_stripped = v.strip()
        
        # Empty string is NULL
        if not v_stripped:
            logger.debug("end_date is empty string, normalized to None")
            return None
        
        # Common NULL representations
        null_representations = {
            'none',          # Python representation
            'null',          # JSON representation
            'nil',           # Alternative null
            'n/a',           # Not applicable
            'na',            # Not available
            'unknown',       # Unknown value
            'unspecified',   # Unspecified
            'tbd',           # To be determined
            'todo',          # Not yet determined
            '-',             # Dash placeholder
            '--',            # Double dash placeholder
        }
        
        # Check if normalized value is in null representations
        if v_stripped.lower() in null_representations:
            logger.debug(f"end_date value '{v}' recognized as null representation, normalized to None")
            return None
        
        # Not a null representation, pass through to date validation
        return v


class SupervisorFeedbackCSVRow(BaseModel):
    """
    Schema for supervisor feedback CSV rows from SQL Server.
    
    Data Structure:
    - Each row represents ONE metric response for ONE form
    - 30 metrics per form = 30 rows with same RO_Form_ID
    - Form header fields are repeated in every row
    
    Column Categories:
    - Form Header: RO_Form_ID, Employee_ID, Name, Designation, BPS, Office_Hierarchy, Executive_Office, From, To
    - Metric Definition: Section_ID, Section, Metric_ID, Metric_Title, Instructions, Metric_Type, Possible_Values
    - Response Data: L_RO_Form_Metric_ID, Value
    
    Example Row:
        RO_Form_ID=12345, L_RO_Form_Metric_ID=67890, Employee_ID=101, Name="John Doe",
        From=2025-11-01, To=2025-11-30, Section_ID=1, Section="Performance",
        Metric_ID=10, Metric_Title="Communication", Metric_Type="R",
        Possible_Values="Poor, Fair, Good, Excellent", Value="Good"
    
    Note: Designation, BPS, Office_Hierarchy, Executive_Office fields are accepted but NOT stored in PostgreSQL.
    """
    
    # ========== FORM HEADER FIELDS (repeated in every row) ==========
    
    RO_Form_ID: int = Field(
        ...,
        description="Unique form identifier from SQL Server",
        gt=0
    )
    
    L_RO_Form_Metric_ID: int = Field(
        ...,
        description="Unique metric response identifier (primary key in SQL Server)",
        gt=0
    )
    
    Employee_ID: int = Field(
        ...,
        description="Employee ID (foreign key to employees table)",
        gt=0
    )
    
    Name: str = Field(
        ...,
        description="Employee name (for reference only, not stored in PostgreSQL)",
        min_length=1,
        max_length=500
    )
    
    # Fields accepted but NOT stored in PostgreSQL
    Designation: Optional[str] = Field(
        None,
        description="Employee designation/position (not stored in PostgreSQL)",
        max_length=200
    )
    
    BPS: Optional[str] = Field(
        None,
        description="Basic Pay Scale (not stored in PostgreSQL)",
        max_length=50
    )
    
    Office_Hierarchy: Optional[str] = Field(
        None,
        description="Office hierarchy path (not stored in PostgreSQL)",
        max_length=500
    )
    
    Executive_Office: Optional[str] = Field(
        None,
        description="Executive office (not stored in PostgreSQL)",
        max_length=200
    )
    
    # Date fields - will be stored in from_date, to_date columns
    From: Union[str, date, datetime] = Field(
        ...,
        description="Feedback period start date (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    
    To: Union[str, date, datetime] = Field(
        ...,
        description="Feedback period end date (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"
    )
    
    # ========== METRIC DEFINITION FIELDS ==========
    
    Section_ID: int = Field(
        ...,
        description="Section ID for categorizing metrics",
        ge=0
    )
    
    Section: str = Field(
        ...,
        description="Section name (e.g., 'Performance', 'Behavior')",
        min_length=1,
        max_length=200
    )
    
    Metric_ID: int = Field(
        ...,
        description="Unique metric identifier (business key)",
        gt=0
    )
    
    Metric_Title: str = Field(
        ...,
        description="Metric display name (e.g., 'Communication Skills')",
        min_length=1,
        max_length=200
    )
    
    Instructions: Optional[str] = Field(
        None,
        description="Brief explanation of the metric (help text)",
        max_length=1000
    )
    
    Metric_Type: str = Field(
        ...,
        description="Metric type: 'R' for rating (with choices), 'T' for text (free form)",
        pattern=r'^[RT]$'
    )
    
    Possible_Values: Optional[str] = Field(
        None,
        description="Comma-separated rating options (e.g., 'Poor, Fair, Good, Excellent'). NULL for text-type metrics.",
        max_length=500
    )
    
    # ========== RESPONSE DATA ==========
    
    Value: Optional[str] = Field(
        None,
        description="Supervisor's response (rating label or free text)",
        max_length=5000
    )
    
    # Model configuration
    model_config = {
        "from_attributes": True,
        "extra": "ignore",
        "validate_assignment": False,
        "str_strip_whitespace": True,
        "str_to_lower": False,
        "validate_default": False,
    }
    
    # ========== FIELD VALIDATORS ==========
    
    @field_validator('Employee_ID', mode='before')
    @classmethod
    def validate_and_convert_employee_id(cls, v: Any) -> int:
        """Convert Employee_ID from string to int if needed."""
        try:
            if isinstance(v, str):
                employee_id = int(v.strip())
            elif isinstance(v, int):
                employee_id = v
            else:
                raise ValueError(f"Employee_ID must be an integer or numeric string, got {type(v).__name__}")
        except (ValueError, AttributeError):
            raise ValueError(f"Employee_ID must be a valid integer or numeric string. Received: '{v}'")
        
        if employee_id <= 0:
            raise ValueError(f"Employee_ID must be a positive integer. Received: {employee_id}")
        
        return employee_id
    
    @field_validator('From', 'To')
    @classmethod
    def validate_dates(cls, v: Union[str, date], info) -> Union[str, date]:
        """Check a report-period date: not in the future, in a format parse_period_date accepts.

        Strings are returned as given and converted in convert_date_strings.
        """
        return check_period_date(v)
    
    @field_validator('Metric_Type')
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        """Validate Metric_Type is exactly 'R' or 'T' (case-sensitive)."""
        if v not in ['R', 'T']:
            raise ValueError(f"Metric_Type must be 'R' (rating) or 'T' (text), got: '{v}'")
        return v
    
    # ========== MODEL VALIDATORS ==========
    
    @model_validator(mode='after')
    def convert_date_strings(self):
        """Convert the validated date strings to date objects."""
        for date_field in ['From', 'To']:
            value = getattr(self, date_field)
            if isinstance(value, str):
                setattr(self, date_field, parse_period_date(value))
        return self
    
    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure From date is before To date."""
        from_date = self.From
        to_date = self.To
        
        if from_date and to_date:
            if from_date >= to_date:
                raise ValueError(f"From date ({from_date}) must be before To date ({to_date})")
        
        return self
    
    @model_validator(mode='after')
    def validate_metric_type_consistency(self):
        """
        Validate Metric_Type aligns with Possible_Values.
        Blocks import if a rating value does not match Possible_Values.
        """
        metric_type = self.Metric_Type
        possible_values = self.Possible_Values
        value = self.Value
        metric_id = self.Metric_ID

        # Rating metrics must have Possible_Values and Value must match one of them
        if metric_type == 'R':
            if not possible_values or not possible_values.strip():
                raise ValueError(
                    f"Rating metric (Metric_ID={metric_id}) must define Possible_Values."
                )

            # If a value is provided, it must match one of the possible options
            if value is not None and str(value).strip():
                options = [opt.strip() for opt in possible_values.split(',') if opt.strip()]
                # use case-insensitive comparison for robustness
                normalized_options = {opt.lower() for opt in options}
                if str(value).strip().lower() not in normalized_options:
                    raise ValueError(
                        f"Value '{value}' not found in Possible_Values '{possible_values}' for metric {metric_id}."
                    )

        # Text metrics should NOT have Possible_Values (warning only)
        elif metric_type == 'T':
            # Check if Possible_Values contains actual content (not just null-like text)
            if possible_values and possible_values.strip():
                # Define null-like representations that are acceptable for text metrics
                null_representations = {
                    'null', 'none', 'nil', 'n/a', 'na', 'unknown', 'unspecified', 
                    'tbd', 'todo', '-', '--', 'not applicable', 'not available'
                }
                
                # If it's not a null-like representation, warn
                if possible_values.strip().lower() not in null_representations:
                    logger.warning(
                        f"Text metric (Metric_ID={metric_id}) has Possible_Values defined: '{possible_values}'. "
                        f"This will be ignored."
                    )

        return self
