"""Map employee reports to the job descriptions in effect for their period."""
from typing import Dict, Any, List
from datetime import date
from app.core.logger import logger
from app.domain.periods import report_week_start


def map_reports_to_jds(
    reports: List[Dict[str, Any]],
    jds: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Map reports to their applicable job description(s) based on temporal overlap.
    
    Groups reports by their applicable JD configuration, handling scenarios where:
    - Employee has single stable JD throughout period
    - Employee transitions between JDs during period  
    - Employee holds multiple concurrent JDs
    
    Args:
        reports: List of report dictionaries with at least 'date' field
        jds: List of JD dictionaries from get_employee_job_descriptions_for_period()
        
    Returns:
        Dictionary with 'jd_groups' (reports grouped by applicable JDs) and 
        'unmapped_reports' (reports without applicable JD)
        
    Example:
        >>> reports = [{"text": "...", "date": date(2025, 1, 5), "report_id": "..."}]
        >>> jds = [{"jd_id": "JD_001", "effective_during_period": {...}, ...}]
        >>> result = map_reports_to_jds(reports, jds)
        >>> # Returns grouped reports with their applicable JDs
    """
    
    # Input validation - return empty structure if no data
    if not reports:
        logger.info("No reports provided for JD mapping")
        return {"jd_groups": [], "unmapped_reports": []}
    
    if not jds:
        logger.warning(f"No JDs provided for mapping {len(reports)} reports - all reports will be unmapped")
        return {"jd_groups": [], "unmapped_reports": reports}
    
    logger.info(f"Mapping {len(reports)} reports to {len(jds)} job descriptions")
    
    # Data structure to group reports by their applicable JD configuration
    # Key: tuple of sorted jd_ids (for consistent grouping)
    # Value: list of reports applicable to that JD configuration
    jd_groups_map = {}
    unmapped_reports = []
    
    # Process each report
    for report in reports:
        report_date = report.get("date")
        
        # Skip reports without dates
        if not report_date:
            logger.warning(f"Report {report.get('report_id', 'unknown')} has no date - adding to unmapped")
            unmapped_reports.append(report)
            continue
        
        # Convert date to date object if it's a string
        if isinstance(report_date, str):
            try:
                from datetime import datetime
                report_date = datetime.fromisoformat(report_date).date()
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse date '{report_date}' for report {report.get('report_id', 'unknown')}")
                unmapped_reports.append(report)
                continue
        
        # Calculate the week period for this report
        # report_date is the END of the week
        week_start_date = report_week_start(report_date)
        week_end_date = report_date
        
        logger.debug(f"Report {report.get('report_id', 'unknown')[:8]} covers week: {week_start_date} to {week_end_date}")
        
        # Find all JDs applicable to this report's week
        # A JD is applicable if it overlaps with ANY part of the report week
        applicable_jds = []
        for jd in jds:
            effective_period = jd.get("effective_during_period", {})
            effective_start = effective_period.get("start")
            effective_end = effective_period.get("end")
            
            # Check if JD overlaps with the report week
            # JD overlaps if: JD_start <= week_end AND JD_end >= week_start
            if effective_start and effective_end:
                if effective_start <= week_end_date and effective_end >= week_start_date:
                    applicable_jds.append(jd)
                    logger.debug(
                        f"  JD {jd['jd_id']} applicable: JD period ({effective_start} to {effective_end}) "
                        f"overlaps with week ({week_start_date} to {week_end_date})"
                    )
        
        # If no applicable JDs found, add to unmapped
        if not applicable_jds:
            logger.debug(f"Report week {week_start_date} to {week_end_date} has no applicable JD")
            unmapped_reports.append(report)
            continue
        
        # Create a unique key for this JD configuration
        # Sort JD IDs to ensure consistent grouping (e.g., [JD_A, JD_B] same as [JD_B, JD_A])
        jd_ids = sorted([jd["jd_id"] for jd in applicable_jds])
        group_key = tuple(jd_ids)
        
        # Add report to the appropriate group with week range information
        if group_key not in jd_groups_map:
            jd_groups_map[group_key] = {
                "jd_ids": jd_ids,
                "jd_texts": [jd["job_description"] for jd in applicable_jds],
                "reports": [],
                "jd_metadata": applicable_jds  # Store full JD info for date range calculation
            }
        
        # Add week range information to the report before storing
        report_with_week_range = report.copy()
        report_with_week_range["week_start_date"] = week_start_date
        report_with_week_range["week_end_date"] = week_end_date
        
        jd_groups_map[group_key]["reports"].append(report_with_week_range)
    
    # Convert the map to a list and calculate effective date ranges for each group
    jd_groups = []
    for group_key, group_data in jd_groups_map.items():
        # Calculate the date range for this group based on its reports' week ranges
        reports_with_weeks = group_data["reports"]
        
        if reports_with_weeks:
            # Get all week start and end dates
            week_starts = [r.get("week_start_date") for r in reports_with_weeks if r.get("week_start_date")]
            week_ends = [r.get("week_end_date") for r in reports_with_weeks if r.get("week_end_date")]
            
            # Group effective dates span from earliest week start to latest week end
            group_start = min(week_starts) if week_starts else None
            group_end = max(week_ends) if week_ends else None
        else:
            # Fallback to JD effective dates if no valid report dates
            jd_starts = [jd["effective_during_period"]["start"] for jd in group_data["jd_metadata"]]
            jd_ends = [jd["effective_during_period"]["end"] for jd in group_data["jd_metadata"]]
            group_start = min(jd_starts) if jd_starts else None
            group_end = max(jd_ends) if jd_ends else None
        
        # Build final group structure without internal metadata
        jd_groups.append({
            "jd_ids": group_data["jd_ids"],
            "jd_texts": group_data["jd_texts"],
            "effective_dates": {
                "start": group_start,
                "end": group_end
            },
            "reports": group_data["reports"]
        })
    
    # Sort groups by effective start date for chronological order
    jd_groups.sort(key=lambda g: g["effective_dates"]["start"] if g["effective_dates"]["start"] else date.min)
    
    # Log summary
    logger.info(f"Created {len(jd_groups)} JD groups with {len(unmapped_reports)} unmapped reports")
    for i, group in enumerate(jd_groups):
        logger.debug(
            f"  Group {i+1}: JDs {group['jd_ids']} - "
            f"{len(group['reports'])} reports covering weeks from {group['effective_dates']['start']} to {group['effective_dates']['end']}"
        )
    
    return {
        "jd_groups": jd_groups,
        "unmapped_reports": unmapped_reports
    }
