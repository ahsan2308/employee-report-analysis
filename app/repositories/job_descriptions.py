"""Job description queries."""
from typing import List, Dict, Any
from datetime import date
from app.db.database import get_database
from app.models.db_models import EmployeeJobDescription
from app.core.logger import logger


def get_employee_job_descriptions_for_period(
    employee_id: int,
    period_start: date,
    period_end: date
) -> List[Dict[str, Any]]:
    """
    Retrieve all job descriptions that overlap with the analysis period for an employee.
    
    This function identifies JDs that were active at any point during the specified period,
    including both current and historical assignments. It calculates the exact date range
    each JD was effective within the analysis period.
    
    Args:
        employee_id: The employee's ID
        period_start: Start date of the analysis period
        period_end: End date of the analysis period
        
    Returns:
        List of dictionaries containing JD data with effective period information.
        Returns empty list if no JDs found or on error.
        
    Example:
        >>> jds = get_employee_job_descriptions_for_period(123, date(2025, 1, 1), date(2025, 3, 31))
        >>> # Returns JDs with their effective dates within the quarter
    """
    db_instance = get_database()
    jds = []
    
    try:
        logger.info(f"Fetching JDs for employee {employee_id} from {period_start} to {period_end}")
        
        with db_instance.create_session() as session:
            # Query JDs that overlap with the analysis period
            # A JD overlaps if:
            # - It was assigned before or during the period AND
            # - It's either current (end_date is NULL) OR ended during or after the period
            query = session.query(EmployeeJobDescription).filter(
                EmployeeJobDescription.employee_id == employee_id,
                EmployeeJobDescription.assigned_date <= period_end,
                # Either no end date (current role) OR end date is after period start
                (
                    (EmployeeJobDescription.is_current == True) |
                    (EmployeeJobDescription.end_date >= period_start)
                )
            ).order_by(EmployeeJobDescription.assigned_date.asc())
            
            # Process each JD record
            for jd_record in query.all():
                # Calculate the effective date range within the analysis period
                # effective_start = the later of (assigned_date, period_start)
                effective_start = max(jd_record.assigned_date, period_start)
                
                # effective_end = the earlier of (end_date or period_end, period_end)
                if jd_record.end_date is None:
                    # Current role - effective until end of period
                    effective_end = period_end
                else:
                    # Historical role - effective until whichever comes first
                    effective_end = min(jd_record.end_date, period_end)
                
                # Add to results with all necessary fields
                jds.append({
                    "jd_id": jd_record.jd_id,
                    "job_description": jd_record.job_description,
                    "assigned_date": jd_record.assigned_date,
                    "end_date": jd_record.end_date,
                    "is_current": jd_record.is_current,
                    "effective_during_period": {
                        "start": effective_start,
                        "end": effective_end
                    }
                })
            
            logger.info(f"Found {len(jds)} JDs for employee {employee_id} overlapping period {period_start} to {period_end}")
            
            # Log details of each JD for debugging
            for jd in jds:
                logger.debug(
                    f"  JD {jd['jd_id']}: assigned {jd['assigned_date']}, "
                    f"ends {jd['end_date'] or 'current'}, "
                    f"effective in period: {jd['effective_during_period']['start']} to {jd['effective_during_period']['end']}"
                )
            
            return jds
            
    except Exception as e:
        logger.error(f"Error fetching job descriptions for employee {employee_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
