from typing import List, Dict, Optional, Set
from uuid import UUID
from sqlalchemy import text
from app.database import get_database
from app.models.db_models import Report
from app.core.logger import logger

def get_complete_reports_by_ids(report_ids: List[str]) -> List[str]:
    """
    Fetch complete reports from the database given a list of report IDs.
    This is useful when we have chunks from vector search and need to
    retrieve the full reports for LLM analysis.
    
    Args:
        report_ids: List of report IDs (as strings)
        
    Returns:
        List of complete report texts
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
                        reports.append(report.report_text)
                    else:
                        logger.debug(f"Report not found or has no text: {report_id}")
                except Exception as e:
                    logger.error(f"Error retrieving report {report_id}: {e}")
                    
        return reports
    except Exception as e:
        logger.error(f"Database error when retrieving reports: {e}")
        return []

def get_reports_for_vector_results(search_results: List[Dict]) -> List[str]:
    """
    Extract report IDs from vector search results and fetch the complete reports.
    
    Args:
        search_results: Results from vector search, containing report_id in metadata
        
    Returns:
        List of complete report texts
    """
    # Extract report IDs from search results
    report_ids = []
    for result in search_results:
        if "report_id" in result:
            report_ids.append(result["report_id"])
    
    # Fetch complete reports
    return get_complete_reports_by_ids(report_ids)
