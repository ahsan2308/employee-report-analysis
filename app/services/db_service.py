from typing import List, Dict, Optional, Set, Any
from uuid import UUID
from sqlalchemy import text
from datetime import date, timedelta
from app.database import get_database
from app.models.db_models import Report
from app.models.vision_data_models import EmployeeVisionData
from app.core.logger import logger

def get_complete_reports_by_ids(report_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch complete reports from the database given a list of report IDs.
    This is useful when we have chunks from vector search and need to
    retrieve the full reports for LLM analysis.
    
    Args:
        report_ids: List of report IDs (as strings)
        
    Returns:
        List of dictionaries containing report text and metadata
    """
    # Early return if no report IDs
    if not report_ids:
        return []
    
    # Convert to set to remove duplicates - no need to fetch same report multiple times
    unique_report_ids = set(report_ids)
    
    db_instance = get_database()
    reports = []
    
    try:
        with db_instance.create_session() as session:
            # Query reports with the given IDs
            for report_id in unique_report_ids:
                try:
                    # Handle both string and UUID formats
                    if isinstance(report_id, str):
                        try:
                            # Try converting to UUID if it's in string format
                            uuid_id = UUID(report_id)
                        except ValueError:
                            logger.warning(f"Invalid UUID format: {report_id}")
                            continue
                    else:
                        uuid_id = report_id
                        
                    report = session.query(Report).filter(Report.report_id == uuid_id).first()
                    if report and report.report_text:
                        reports.append({
                            "text": report.report_text,
                            "date": report.report_date,
                            "report_id": str(report.report_id)
                        })
                    else:
                        logger.debug(f"Report not found or has no text: {report_id}")
                except Exception as e:
                    logger.error(f"Error retrieving report {report_id}: {e}")
                    
        return reports
    except Exception as e:
        logger.error(f"Database error when retrieving reports: {e}")
        return []

def get_reports_for_vector_results(search_results: List[Dict]) -> List[Dict[str, Any]]:
    """
    Extract report IDs from vector search results and fetch the complete reports with date information.
    
    Args:
        search_results: Results from vector search, containing report_id in metadata
        
    Returns:
        List of dictionaries containing report text and metadata
    """
    # Extract report IDs from search results
    report_ids = []
    for result in search_results:
        if "report_id" in result:
            report_ids.append(result["report_id"])
    
    # Fetch complete reports
    return get_complete_reports_by_ids(report_ids)

def get_employee_vision_data(employee_id: int, report_date: date, num_previous_weeks: int = 4) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for the given report date and previous periods.
    
    Args:
        employee_id: The ID of the employee
        report_date: The date of the report (to match with to_date in vision data)
        num_previous_weeks: Number of previous weeks worth of data to include
        
    Returns:
        Dictionary containing current data (matching report date) and previous data
    """
    db_instance = get_database()
    
    # Calculate cutoff date for previous data (4 weeks before report date by default)
    previous_data_cutoff = report_date - timedelta(weeks=num_previous_weeks)
    
    result = {
        "date_context": {
            "report_date": report_date.isoformat(),
        },
        "current_data": [],  # Data where to_date matches report_date
        "previous_data": []  # Data where to_date is before report_date but after cutoff
    }
    
    try:
        with db_instance.create_session() as session:
            # Get current data - records where to_date exactly matches the report_date
            current_data = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date == report_date
            ).all()
            
            # Format current data
            for record in current_data:
                result["current_data"].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })
            
            # Get previous data - records with to_date before report_date but after cutoff
            previous_data = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date < report_date,
                EmployeeVisionData.to_date >= previous_data_cutoff
            ).order_by(EmployeeVisionData.to_date.desc()).all()
            
            # Format previous data
            for record in previous_data:
                result["previous_data"].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })
                
            logger.info(f"Retrieved vision data for employee {employee_id}: {len(result['current_data'])} current records, {len(result['previous_data'])} previous records")
            return result
            
    except Exception as e:
        logger.error(f"Error fetching vision data for employee {employee_id}: {e}")
        return result

def get_recent_employee_reports(employee_id: int, current_report_date: date, 
                               exclude_report_id: str = None, limit: int = None, 
                               max_weeks: int = 52) -> List[Dict[str, Any]]:
    """
    Fetch the most recent reports for an employee before the given date.
    
    Args:
        employee_id: The employee's ID
        current_report_date: The date of the current report
        exclude_report_id: Optional ID of current report to exclude
        limit: Maximum number of reports to return (most recent first)
        max_weeks: Maximum age of reports to consider in weeks (default: 1 year)
        
    Returns:
        List of dictionaries containing report text and metadata
    """
    db_instance = get_database()
    reports = []
    
    try:
        with db_instance.create_session() as session:
            # Build query to get recent reports - use max_weeks as an upper bound only
            query = session.query(Report).filter(
                Report.employee_id == employee_id,
                Report.report_date < current_report_date,
                Report.report_date >= current_report_date - timedelta(weeks=max_weeks)
            ).order_by(Report.report_date.desc())
            
            # Exclude current report if provided
            if exclude_report_id:
                try:
                    uuid_id = UUID(exclude_report_id)
                    query = query.filter(Report.report_id != uuid_id)
                except ValueError:
                    logger.warning(f"Invalid UUID format for exclude_report_id: {exclude_report_id}")
            
            # Apply limit if provided
            if limit and isinstance(limit, int) and limit > 0:
                query = query.limit(limit)
            
            # Execute query
            recent_reports = query.all()
            
            # Extract report texts and dates
            for report in recent_reports:
                if report and report.report_text:
                    reports.append({
                        "text": report.report_text,
                        "date": report.report_date,
                        "report_id": str(report.report_id)
                    })
                    
            logger.info(f"Retrieved {len(reports)} recent reports for employee {employee_id}" +
                       (f" (limited to {limit})" if limit else ""))
            return reports
            
    except Exception as e:
        logger.error(f"Error fetching recent reports for employee {employee_id}: {e}")
        return []
