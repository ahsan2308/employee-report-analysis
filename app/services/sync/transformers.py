"""
Row Transformers for SQL Server Sync

Converts SQL Server row data (with datetime objects) to Pydantic-compatible dictionaries
(with string dates) that can be processed by existing CSV import processors.

These transformers ONLY handle type conversion, NOT validation.
All validation is delegated to existing Pydantic schemas (CombinedCSVRow, VisionDataCSVRow).
"""
from typing import Dict, Any, Optional
from datetime import datetime, date

from app.core.logger import logger


def _format_date(dt: Any) -> Optional[str]:
    """
    Convert datetime/date object to YYYY-MM-DD string format.
    
    This is the ONLY transformation needed because:
    - SQL Server returns datetime.date or datetime.datetime objects
    - Pydantic validators expect string dates
    - Pydantic then converts strings → date objects internally
    
    Args:
        dt: datetime, date, or string object
        
    Returns:
        Date string in YYYY-MM-DD format, or None if input is None
    """
    if dt is None:
        return None
    
    # If already a string, return as-is (shouldn't happen with SQL Server DATE types)
    if isinstance(dt, str):
        return dt
    
    # Convert datetime.datetime or datetime.date to ISO string
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%Y-%m-%d")
    
    # Log warning for unexpected types
    logger.warning(f"Unexpected date type: {type(dt).__name__} for value: {dt}")
    return str(dt)


class EmployeeReportTransformer:
    """
    Transforms SQL Server EmployeeReports rows to CombinedCSVRow-compatible format.
    
    ONLY does type conversion (datetime → string).
    All validation is handled by CombinedCSVRow Pydantic schema.
    """
    
    @staticmethod
    def transform(sql_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert SQL Server row to CombinedCSVRow-compatible dict.
        
        Only includes fields that are part of the CSV import schema.
        LastModifiedDate is tracked separately by the sync service.
        
        SQL Server column → Pydantic field mapping:
        - Date columns (From, To) converted from datetime → "YYYY-MM-DD" strings
        - All other fields passed through as-is
        
        Args:
            sql_row: Row from SQL Server (dictionary with column names as keys)
            
        Returns:
            Dictionary compatible with CombinedCSVRow Pydantic schema
        """
        return {
            # Employee fields - pass through
            "Employee_ID": sql_row.get("Employee_ID"),
            "Name": sql_row.get("Name"),
            "Designation": sql_row.get("Designation"),
            "BPS": sql_row.get("BPS"),
            "Office_Hierarchy": sql_row.get("Office_Hierarchy"),
            
            # Date fields - ONLY CHANGE: datetime → string
            "From": _format_date(sql_row.get("From")),
            "To": _format_date(sql_row.get("To")),
            
            # Report content fields - pass through
            "Draft": sql_row.get("Draft"),
            "Tasks_Completed": sql_row.get("Tasks_Completed"),
            "Impact": sql_row.get("Impact"),
            "Challenges": sql_row.get("Challenges"),
            "Support_Required": sql_row.get("Support_Required"),
            "Tasks_Planned": sql_row.get("Tasks_Planned"),
            "Confidence_Level": sql_row.get("Confidence_Level"),  # Pydantic extracts number
            "NTR": sql_row.get("NTR")
            # NOTE: LastModifiedDate is intentionally excluded
            # It's tracked separately in _process_employee_report_batches
        }


class VisionDataTransformer:
    """
    Transforms SQL Server VisionEmployeeData rows to VisionDataCSVRow-compatible format.
    
    ONLY does type conversion (datetime → string).
    JSON fields (Sub_Entities, Sub_Entities_Content) are already strings in SQL Server.
    All validation is handled by VisionDataCSVRow Pydantic schema.
    """
    
    @staticmethod
    def transform(sql_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert SQL Server row to VisionDataCSVRow-compatible dict.
        
        Only includes fields that are part of the CSV import schema.
        ModifiedDate is tracked separately by the sync service.
        
        SQL Server storage (as confirmed):
        - Date columns: DATE type → Python datetime.date objects
        - Sub_Entities: VARCHAR → Python string (e.g., "Analysis:5, Reporting:3")
        - Sub_Entities_Content: VARCHAR → Python string (e.g., "Cases:[], Tasks:[{...}]")
        
        Args:
            sql_row: Row from SQL Server (dictionary with column names as keys)
            
        Returns:
            Dictionary compatible with VisionDataCSVRow Pydantic schema
        """
        return {
            # Employee field - pass through
            "Employee_ID": sql_row.get("Employee_ID"),
            
            # Date fields - ONLY CHANGE: datetime → string
            "From_Date": _format_date(sql_row.get("From_Date")),
            "To_Date": _format_date(sql_row.get("To_Date")),
            
            # Entity fields - pass through (already strings in SQL Server)
            "Main_Entity": sql_row.get("Main_Entity"),
            "Sub_Entities": sql_row.get("Sub_Entities"),  # String: "Name:Count, ..."
            "Sub_Entities_Content": sql_row.get("Sub_Entities_Content")  # String: "Key:[...], ..."
        }


class JobDescriptionTransformer:
    """
    Transforms SQL Server JobDescriptions rows to JobDescriptionCSVRow-compatible format.
    
    All validation is delegated to JobDescriptionCSVRow Pydantic schema.
    
    Design Philosophy:
    - Minimal transformation layer
    - No validation or type conversion logic (handled by Pydantic)
    - No date conversion (Pydantic accepts Union[str, date])
    
    SQL Server Column → Pydantic Field Mapping:
    - Employee_ID: pass through (already int)
    - JD_ID: pass through (Pydantic validator converts int → str)
    - Job_Description: pass through (already string)
    - Assigned_Date: pass through as date object (Pydantic accepts date)
    - Is_Current: pass through as boolean (SQL Server BIT → Python bool)
    - End_Date: pass through as date object or None (Pydantic accepts date/None)
    
    Note: LastModifiedDate from SQL Server is NOT included in the output dictionary.
    It's tracked separately by sync service in _max_modified_date_jd instance variable
    for incremental sync logic.
    """
    
    @staticmethod
    def transform(sql_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert SQL Server row to JobDescriptionCSVRow-compatible dict.
        
        Only includes fields that are part of the CSV import schema.
        The LastModifiedDate column from SQL Server is intentionally excluded
        because it's tracked separately by the sync service for incremental sync logic.
        
        Args:
            sql_row: Row from SQL Server as dictionary with column names as keys
                Expected format from SQL Server:
                {
                    "Employee_ID": 101,                    # int
                    "JD_ID": 1001,                         # int
                    "Job_Description": "Full JD text...",  # str
                    "Assigned_Date": date(2024, 1, 15),    # date object
                    "Is_Current": True,                    # bool (from BIT)
                    "End_Date": None,                      # date object or None
                    "LastModifiedDate": datetime(...)      # NOT INCLUDED IN OUTPUT
                }
            
        Returns:
            Dictionary compatible with JobDescriptionCSVRow Pydantic schema
            {
                "Employee_ID": 101,
                "JD_ID": 1001,
                "Job_Description": "Full JD text...",
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "End_Date": None
            }
        """
        return {
            "Employee_ID": sql_row.get("Employee_ID"),
            "JD_ID": sql_row.get("JD_ID"),
            "Job_Description": sql_row.get("Job_Description"),
            "Assigned_Date": sql_row.get("Assigned_Date"),
            "Is_Current": sql_row.get("Is_Current"),  
            "End_Date": sql_row.get("End_Date")       
            # NOTE: LastModifiedDate is intentionally excluded
            # It's tracked separately in _process_job_description_batches_bulk()
        }


class SupervisorFeedbackTransformer:
    """
    Transforms SQL Server supervisor feedback rows to SupervisorFeedbackCSVRow-compatible format.
    
    ONLY does type conversion (datetime → string).
    All validation is handled by SupervisorFeedbackCSVRow Pydantic schema.
    
    Data Structure:
    - SQL Server table is denormalized: ONE row per metric per form
    - Each form has multiple rows (one per metric)
    - All form header fields (RO_Form_ID, Employee_ID, From, To, etc.) are repeated in each row
    
    SQL Server Column → Pydantic Field Mapping:
    - L_RO_Form_Metric_ID: pass through (already int)
    - RO_Form_ID: pass through (already int)
    - Employee_ID: pass through (already int)
    - Name: pass through (string, for reference only)
    - Designation: pass through (string, not stored in database but required by schema)
    - BPS: pass through (string, not stored in database but required by schema)
    - Office_Hierarchy: pass through (string, not stored in database but required by schema)
    - Executive_Office: pass through (string, not stored in database but required by schema)
    - From: pass through as date object (Pydantic accepts Union[str, date, datetime])
    - To: pass through as date object (Pydantic accepts Union[str, date, datetime])
    - Section_ID: pass through (already int)
    - Section: pass through (string)
    - Metric_ID: pass through (already int)
    - Metric_Title: pass through (string)
    - Instructions: pass through (string)
    - Value: pass through (string)
    - Metric_Type: pass through (string, 'R' or 'T')
    - Possible_Values: pass through (string, e.g., "Poor,Fair,Good,Excellent")
    
    Note: LastModifiedDate from SQL Server is NOT included in the output dictionary.
    It's tracked separately by sync service for incremental sync logic.
    """
    
    @staticmethod
    def transform(sql_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert SQL Server row to SupervisorFeedbackCSVRow-compatible dict.
        
        Only includes fields that are part of the CSV import schema.
        
        Args:
            sql_row: Row from SQL Server as dictionary with column names as keys
                Expected format from SQL Server:
                {
                    "L_RO_Form_Metric_ID": 74,                # int
                    "RO_Form_ID": 15,                         # int
                    "Employee_ID": 1012,                      # int
                    "Name": "MAJ.(R) NADEEM ARIF CH",         # str
                    "Designation": "Director",                # str
                    "BPS": "BS-19",                           # str
                    "Office_Hierarchy": "PPHQ>CI",            # str
                    "Executive_Office": "PPHQ",               # str
                    "From": date(2025, 11, 1),                # date object
                    "To": date(2025, 11, 30),                 # date object
                    "Section_ID": 1,                          # int
                    "Section": "Performance & Work Habits",   # str
                    "Metric_ID": 1,                           # int
                    "Metric_Title": "Quality & Accuracy...",  # str
                    "Instructions": "Ability to deliver...",  # str
                    "Value": "Good",                          # str
                    "Metric_Type": "R",                       # str ('R' or 'T')
                    "Possible_Values": "Poor,Fair,Good,Excellent",  # str
                    "LastModifiedDate": datetime(...)         # NOT INCLUDED IN OUTPUT
                }
            
        Returns:
            Dictionary compatible with SupervisorFeedbackCSVRow Pydantic schema
        """
        return {
            # Form header fields
            "L_RO_Form_Metric_ID": sql_row.get("L_RO_Form_Metric_ID"),
            "RO_Form_ID": sql_row.get("RO_Form_ID"),
            "Employee_ID": sql_row.get("Employee_ID"),
            "Name": sql_row.get("Name"),
            
            # Fields not stored in database but required by schema (extra='ignore')
            "Designation": sql_row.get("Designation"),
            "BPS": sql_row.get("BPS"),
            "Office_Hierarchy": sql_row.get("Office_Hierarchy"),
            "Executive_Office": sql_row.get("Executive_Office"),
            
            # Date fields - pass through (Pydantic accepts date objects)
            "From": sql_row.get("From"),
            "To": sql_row.get("To"),
            
            # Metric definition fields
            "Section_ID": sql_row.get("Section_ID"),
            "Section": sql_row.get("Section"),
            "Metric_ID": sql_row.get("Metric_ID"),
            "Metric_Title": sql_row.get("Metric_Title"),
            "Instructions": sql_row.get("Instructions"),
            "Metric_Type": sql_row.get("Metric_Type"),
            "Possible_Values": sql_row.get("Possible_Values"),
            
            # Response data
            "Value": sql_row.get("Value")
            # NOTE: LastModifiedDate is intentionally excluded
            # It's tracked separately by sync service for incremental sync logic
        }
