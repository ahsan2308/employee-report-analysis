"""Report queries."""
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date, timedelta
from app.db.database import get_database
from app.models.db_models import Report
from app.core.logger import logger
from app.domain.periods import get_month_date_range


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
    
    # Remove duplicates, keeping the given (relevance) order so prompts are stable
    unique_report_ids = list(dict.fromkeys(report_ids))
    
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


def get_reports_for_month(employee_id: int, year: int, month: int) -> List[Dict[str, Any]]:
    """
    Fetch all reports for an employee for a specific month.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        List of dictionaries containing report data and metadata
    """
    start_date, end_date = get_month_date_range(year, month)
    logger.info(f"Fetching reports for employee {employee_id} from {start_date} to {end_date}")
    
    db_instance = get_database()
    reports = []
    
    try:
        with db_instance.create_session() as session:
            # Query reports for the specified month
            query = session.query(Report).filter(
                Report.employee_id == employee_id,
                Report.report_date >= start_date,
                Report.report_date <= end_date
            ).order_by(Report.report_date)
            
            # Execute query and format results
            for report in query.all():
                if report and report.report_text:
                    reports.append({
                        "text": report.report_text,
                        "date": report.report_date,
                        "report_id": str(report.report_id)
                    })
            
            logger.info(f"Found {len(reports)} reports for employee {employee_id} in {year}-{month}")
            return reports
            
    except Exception as e:
        logger.error(f"Error fetching reports for month: {e}")
        return []


def get_report(session: Session, report_id: UUID) -> Optional[Report]:
    """The report row, in the caller's session."""
    return session.query(Report).filter(Report.report_id == report_id).first()


def list_reports_for_employee(session: Session, employee_id: int) -> List[Report]:
    return session.query(Report).filter(Report.employee_id == employee_id).all()


def add_report(session: Session, report: Report) -> Report:
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def find_report_for_date(session: Session, employee_id: int, report_date) -> Optional[Report]:
    """An employee's report for a report date (there is at most one)."""
    return session.query(Report).filter(
        Report.employee_id == employee_id,
        Report.report_date == report_date
    ).first()


def upsert_report(session: Session, employee_id: int, report_date, report_text: str) -> Tuple[Report, bool]:
    """Set the text of the employee's report for the date, creating it if needed (flushed, so it has an id).

    Returns the report and whether it was created.
    """
    existing = find_report_for_date(session, employee_id, report_date)
    if existing:
        existing.report_text = report_text
        return existing, False
    report = Report(employee_id=employee_id, report_date=report_date, report_text=report_text)
    session.add(report)
    session.flush()
    return report, True


def existing_report_keys(session: Session, keys: List[Tuple[int, Any]]) -> Set[Tuple[int, Any]]:
    """The (employee_id, report_date) pairs among keys that already have a report."""
    rows = session.query(Report.employee_id, Report.report_date).filter(
        tuple_(Report.employee_id, Report.report_date).in_(keys)
    ).all()
    return {(employee_id, report_date) for employee_id, report_date in rows}


def bulk_upsert_reports(session: Session, report_data: List[Dict[str, Any]]) -> None:
    """Insert reports, replacing the text of those that exist (one per employee and date); flushed."""
    stmt = pg_insert(Report.__table__).values(report_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['employee_id', 'report_date'],
        set_={'report_text': stmt.excluded.report_text}
    )
    session.execute(stmt)
    session.flush()
