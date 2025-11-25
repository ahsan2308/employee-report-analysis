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
