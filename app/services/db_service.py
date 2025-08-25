from typing import List, Dict, Optional, Set, Any, Tuple
from uuid import UUID
from sqlalchemy import text, func, desc
from datetime import date, datetime, timedelta
import calendar
from app.database import get_database
from app.models.db_models import Report, EmployeeAnalysis, Employee, MonthlyAnalysis, QuarterlyAnalysis
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
                    "sub_entities_content": record.sub_entities_content,
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
                    "sub_entities_content": record.sub_entities_content,
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

def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given month.
    
    Args:
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Tuple of (start_date, end_date) for the month
    """
    # Get the first day of the month
    start_date = date(year, month, 1)
    
    # Get the last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    return start_date, end_date

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

def get_analyses_for_month(employee_id: int, year: int, month: int) -> List[Dict[str, Any]]:
    """
    Fetch all weekly analyses for an employee for a specific month.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        List of dictionaries containing analysis data and metadata
    """
    start_date, end_date = get_month_date_range(year, month)
    logger.info(f"Fetching analyses for employee {employee_id} from {start_date} to {end_date}")
    
    db_instance = get_database()
    analyses = []
    
    try:
        with db_instance.create_session() as session:
            # First get reports for the specified month
            report_query = session.query(Report).filter(
                Report.employee_id == employee_id,
                Report.report_date >= start_date,
                Report.report_date <= end_date
            )
            
            # Get the report IDs
            report_ids = [report.report_id for report in report_query.all()]
            
            if not report_ids:
                logger.warning(f"No reports found for employee {employee_id} in {year}-{month}")
                return []
            
            # Get analyses for these reports
            analysis_query = session.query(EmployeeAnalysis, Report).join(
                Report, EmployeeAnalysis.report_id == Report.report_id
            ).filter(
                EmployeeAnalysis.report_id.in_(report_ids)
            ).order_by(Report.report_date)
            
            # Format results
            for analysis, report in analysis_query.all():
                analyses.append({
                    "analysis_id": analysis.analysis_id,
                    "report_id": str(analysis.report_id),
                    "date": report.report_date,
                    "analysis_date": analysis.analysis_date,
                    "sentiment_score": analysis.sentiment_score,
                    "risk_level": analysis.risk_level,
                    "risk_explanation": analysis.risk_explanation,
                    "achievements": analysis.achievements_json,
                    "challenges": analysis.challenges_json,
                    "topics": analysis.topics,
                    "action_items": analysis.action_items,
                    "full_analysis": analysis.full_analysis_json,
                    
                    # Credibility assessment fields
                    "credibility_rating": analysis.credibility_rating,
                    "credibility_explanation": analysis.credibility_explanation,
                    "exaggeration_flags": analysis.exaggeration_flags,
                    "consistency_score": analysis.consistency_score,
                    
                    # Performance assessment fields
                    "performance_rating": analysis.performance_rating,
                    "performance_summary": analysis.performance_summary,
                    "performance_strengths": analysis.performance_strengths,
                    "performance_improvement_areas": analysis.performance_improvement_areas,
                    
                    # Audit timestamps
                    "created_at": analysis.created_at,
                    "updated_at": analysis.updated_at
                })
            
            logger.info(f"Found {len(analyses)} analyses for employee {employee_id} in {year}-{month}")
            return analyses
            
    except Exception as e:
        logger.error(f"Error fetching analyses for month: {e}")
        return []

def get_employee_info(employee_id: int) -> Dict[str, Any]:
    """
    Fetch basic information about an employee.
    
    Args:
        employee_id: The employee's ID
        
    Returns:
        Dictionary with employee information or None if not found
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                logger.error(f"Employee with ID {employee_id} not found")
                return None
                
            return {
                "id": employee.id,
                "name": employee.name,
                "wing": employee.wing,
                "position": employee.position
            }
    except Exception as e:
        logger.error(f"Error fetching employee info: {e}")
        return None

def get_monthly_analysis_by_params(employee_id: int, year: int, month: int) -> Optional[Dict[str, Any]]:
    """
    Check if a monthly analysis exists for a specific employee, year, and month.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Dictionary with analysis data if found, None otherwise
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:
            from app.models.db_models import MonthlyAnalysis
            
            # Query for existing analysis
            analysis = session.query(MonthlyAnalysis).filter(
                MonthlyAnalysis.employee_id == employee_id,
                MonthlyAnalysis.year == year,
                MonthlyAnalysis.month == month
            ).first()
            
            if not analysis:
                logger.info(f"No monthly analysis found for employee {employee_id}, {year}-{month}")
                return None
                
            # Convert to dictionary with all fields from the updated model
            return {
                "analysis_id": analysis.analysis_id,
                "employee_id": analysis.employee_id,
                "year": analysis.year,
                "month": analysis.month,
                "period_start": analysis.period_start,
                "period_end": analysis.period_end,
                "weekly_report_ids": analysis.weekly_report_ids,
                "avg_sentiment_score": analysis.avg_sentiment_score,
                
                # Progress trends fields
                "sentiment_trend": analysis.sentiment_trend,
                "performance_trend": analysis.performance_trend,
                "risk_level_pattern": analysis.risk_level_pattern,
                "challenge_resolution_progress": analysis.challenge_resolution_progress,
                
                # Risk assessment fields
                "risk_level": analysis.risk_level,
                "risk_explanation": analysis.risk_explanation,
                "significant_risks": analysis.significant_risks,
                "escalating_risks": analysis.escalating_risks,
                "risk_mitigation_recommendations": analysis.risk_mitigation_recommendations,
                
                # Monthly achievements & challenges
                "key_achievements": analysis.monthly_achievements,  
                "recurring_challenges": analysis.recurring_challenges,
                "achievement_impact_avg": analysis.achievement_impact_avg,
                
                # Consistency assessment fields
                "task_completion_reliability": analysis.task_completion_reliability,
                "work_quality_consistency": analysis.work_quality_consistency,
                "performance_stability": analysis.performance_stability,
                "consistency_notable_strengths": analysis.consistency_notable_strengths,
                "consistency_notable_weaknesses": analysis.consistency_notable_weaknesses,
                
                # Growth indicators
                "complexity_of_tasks": analysis.complexity_of_tasks,
                "skill_development_evidence": analysis.skill_development_evidence,
                "confidence_level_change": analysis.confidence_level_change,
                "approach_to_challenges": analysis.approach_to_challenges,
                
                # Focus areas & recommendations
                "focus_areas": analysis.focus_areas,
                "strategic_recommendations": analysis.strategic_recommendations,
                
                # Summary and complete data
                "monthly_summary": analysis.monthly_summary,
                "full_analysis_json": analysis.full_analysis_json,
                "analysis_date": analysis.analysis_date
            }
    except Exception as e:
        logger.error(f"Error checking for monthly analysis: {e}")
        return None

def store_monthly_analysis(analysis_data: Dict[str, Any]) -> Optional[int]:
    """
    Store monthly analysis results in the database.
    
    Args:
        analysis_data: Dictionary containing all analysis data
        
    Returns:
        ID of the stored analysis, or None if operation failed
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:
            from app.models.db_models import MonthlyAnalysis
            
            # Extract key fields
            employee_id = analysis_data.get("employee_id")
            year = analysis_data.get("year")
            month = analysis_data.get("month")
            
            if not (employee_id and year and month):
                logger.error("Missing required fields for monthly analysis")
                return None
                
            # Check if analysis exists
            existing = session.query(MonthlyAnalysis).filter(
                MonthlyAnalysis.employee_id == employee_id,
                MonthlyAnalysis.year == year,
                MonthlyAnalysis.month == month
            ).first()
            
            if existing:
                logger.info(f"Updating existing monthly analysis for employee {employee_id}, {year}-{month}")
                # Update fields on existing record
                for key, value in analysis_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                    # Handle field name differences
                    elif key == "key_achievements" and hasattr(existing, "monthly_achievements"):
                        setattr(existing, "monthly_achievements", value)
                    elif key == "progress_assessment" and hasattr(existing, "performance_trend"):
                        setattr(existing, "performance_trend", value)
                analysis = existing
            else:
                logger.info(f"Creating new monthly analysis for employee {employee_id}, {year}-{month}")
                
                # Create new analysis record using fields directly from analysis_data
                # rather than trying to re-extract from nested structures
                analysis = MonthlyAnalysis(
                    employee_id=employee_id,
                    year=year,
                    month=month,
                    period_start=analysis_data.get("period_start"),
                    period_end=analysis_data.get("period_end"),
                    weekly_report_ids=analysis_data.get("weekly_report_ids"),
                    avg_sentiment_score=analysis_data.get("avg_sentiment_score"),
                    
                    # Progress trends fields
                    sentiment_trend=analysis_data.get("sentiment_trend"),
                    performance_trend=analysis_data.get("performance_trend"),
                    risk_level_pattern=analysis_data.get("risk_level_pattern"),
                    challenge_resolution_progress=analysis_data.get("challenge_resolution_progress"),
                    
                    # Risk assessment fields
                    risk_level=analysis_data.get("risk_level"),
                    risk_explanation=analysis_data.get("risk_explanation"),
                    significant_risks=analysis_data.get("significant_risks"),
                    escalating_risks=analysis_data.get("escalating_risks"),
                    risk_mitigation_recommendations=analysis_data.get("risk_mitigation_recommendations"),
                    
                    # Monthly achievements & challenges
                    monthly_achievements=analysis_data.get("monthly_achievements"),
                    recurring_challenges=analysis_data.get("recurring_challenges"),
                    achievement_impact_avg=analysis_data.get("achievement_impact_avg"),
                    
                    # Consistency assessment fields
                    task_completion_reliability=analysis_data.get("task_completion_reliability"),
                    work_quality_consistency=analysis_data.get("work_quality_consistency"),
                    performance_stability=analysis_data.get("performance_stability"),
                    consistency_notable_strengths=analysis_data.get("consistency_notable_strengths"),
                    consistency_notable_weaknesses=analysis_data.get("consistency_notable_weaknesses"),
                    
                    # Growth indicators
                    complexity_of_tasks=analysis_data.get("complexity_of_tasks"),
                    skill_development_evidence=analysis_data.get("skill_development_evidence"),
                    confidence_level_change=analysis_data.get("confidence_level_change"),
                    approach_to_challenges=analysis_data.get("approach_to_challenges"),
                    
                    # Focus areas & recommendations
                    focus_areas=analysis_data.get("focus_areas"),
                    strategic_recommendations=analysis_data.get("strategic_recommendations"),
                    
                    # Summary and complete data
                    monthly_summary=analysis_data.get("monthly_summary"),
                    full_analysis_json=analysis_data.get("full_analysis_json")
                )
                session.add(analysis)
                
            # Commit the changes
            session.commit()
            session.refresh(analysis)
            
            logger.info(f"Successfully stored monthly analysis with ID {analysis.analysis_id}")
            return analysis.analysis_id
            
    except Exception as e:
        logger.error(f"Error storing monthly analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_employee_vision_data_for_month(employee_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for all weeks in a given month.
    
    Args:
        employee_id: The ID of the employee
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Dictionary containing a list of week-wise data for the month
    """
    from datetime import date, timedelta
    import calendar

    db_instance = get_database()
    start_date, end_date = get_month_date_range(year, month)
    result = {
        "date_context": {
            "month": month,
            "year": year,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        },
        "weeks_data": []
    }

    try:
        with db_instance.create_session() as session:
            # Query all vision data for the month
            records = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date >= start_date,
                EmployeeVisionData.to_date <= end_date
            ).order_by(EmployeeVisionData.to_date.asc()).all()

            # Group records by week (ISO week number)
            week_map = {}
            for record in records:
                week_num = record.to_date.isocalendar()[1]
                if week_num not in week_map:
                    week_map[week_num] = []
                week_map[week_num].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "sub_entities_content": record.sub_entities_content,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })

            # Build week-wise data list
            for idx, (week_num, items) in enumerate(sorted(week_map.items())):
                result["weeks_data"].append({
                    "week_number": idx + 1,
                    "iso_week": week_num,
                    "activities": items
                })

            logger.info(f"Retrieved vision data for employee {employee_id} for {year}-{month}: {len(result['weeks_data'])} weeks")
            return result

    except Exception as e:
        logger.error(f"Error fetching monthly vision data for employee {employee_id}: {e}")
        return result

def get_quarter_date_range(year: int, quarter: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given quarter.
    
    Args:
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Tuple of (start_date, end_date) for the quarter
    """
    if quarter < 1 or quarter > 4:
        raise ValueError(f"Quarter must be between 1 and 4, got {quarter}")
    
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    
    start_date = date(year, start_month, 1)
    # Last day of end month
    last_day = calendar.monthrange(year, end_month)[1]
    end_date = date(year, end_month, last_day)
    
    return start_date, end_date

def get_monthly_analyses_for_quarter(employee_id: int, year: int, quarter: int) -> List[Dict[str, Any]]:
    """
    Fetch all monthly analyses for an employee for a specific quarter.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        List of dictionaries containing monthly analysis data and metadata
    """
    start_date, end_date = get_quarter_date_range(year, quarter)
    logger.info(f"Fetching monthly analyses for employee {employee_id} from {start_date} to {end_date}")
    
    db_instance = get_database()
    analyses = []
    
    try:
        with db_instance.create_session() as session:
            # Get months in this quarter
            months_in_quarter = [(quarter - 1) * 3 + i + 1 for i in range(3)]
            
            # Query monthly analyses for the specified quarter
            query = session.query(MonthlyAnalysis).filter(
                MonthlyAnalysis.employee_id == employee_id,
                MonthlyAnalysis.year == year,
                MonthlyAnalysis.month.in_(months_in_quarter)
            ).order_by(MonthlyAnalysis.month)
            
            # Format results
            for analysis in query.all():
                if analysis:
                    month_name = {
                        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                    }.get(analysis.month, f"Month {analysis.month}")
                    
                    analyses.append({
                        "analysis_id": analysis.analysis_id,
                        "month": analysis.month,
                        "month_name": month_name,
                        "year": analysis.year,
                        "period_start": analysis.period_start,
                        "period_end": analysis.period_end,
                        "weekly_report_ids": analysis.weekly_report_ids,
                        "avg_sentiment_score": analysis.avg_sentiment_score,
                        "progress_trends": {
                            "performance_trend": analysis.performance_trend,
                            "sentiment_trend": analysis.sentiment_trend,
                            "risk_level_pattern": analysis.risk_level_pattern,
                            "challenge_resolution_progress": analysis.challenge_resolution_progress
                        },
                        "monthly_achievements": analysis.monthly_achievements,
                        "recurring_challenges": analysis.recurring_challenges,
                        "consistency_assessment": {
                            "task_completion_reliability": analysis.task_completion_reliability,
                            "work_quality_consistency": analysis.work_quality_consistency,
                            "performance_stability": analysis.performance_stability,
                            "notable_strengths": analysis.consistency_notable_strengths,
                            "notable_weaknesses": analysis.consistency_notable_weaknesses
                        },
                        "growth_indicators": {
                            "complexity_of_tasks": analysis.complexity_of_tasks,
                            "skill_development_evidence": analysis.skill_development_evidence,
                            "confidence_level_change": analysis.confidence_level_change,
                            "approach_to_challenges": analysis.approach_to_challenges
                        },
                        "focus_areas": analysis.focus_areas,
                        "achievement_impact_avg": analysis.achievement_impact_avg,
                        "monthly_risk_assessment": {
                            "overall_risk_level": analysis.risk_level,
                            "risk_explanation": analysis.risk_explanation,
                            "significant_risks": analysis.significant_risks,
                            "escalating_risks": analysis.escalating_risks,
                            "risk_mitigation_recommendations": analysis.risk_mitigation_recommendations
                        },
                        "strategic_recommendations": analysis.strategic_recommendations,
                        "monthly_summary": analysis.monthly_summary,
                        "full_analysis_json": analysis.full_analysis_json
                    })
            
            logger.info(f"Found {len(analyses)} monthly analyses for employee {employee_id} in {year}-Q{quarter}")
            return analyses
            
    except Exception as e:
        logger.error(f"Error fetching monthly analyses for quarter: {e}")
        return []

def get_quarterly_analysis_by_params(employee_id: int, year: int, quarter: int) -> Optional[Dict[str, Any]]:
    """
    Check if a quarterly analysis exists for a specific employee, year, and quarter.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Dictionary with analysis data if found, None otherwise
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:            
            # Query for existing analysis
            analysis = session.query(QuarterlyAnalysis).filter(
                QuarterlyAnalysis.employee_id == employee_id,
                QuarterlyAnalysis.year == year,
                QuarterlyAnalysis.quarter == quarter
            ).first()
            
            if not analysis:
                logger.info(f"No quarterly analysis found for employee {employee_id}, {year}-Q{quarter}")
                return None
                
            # Convert to dictionary with all fields from the model
            return {
                "analysis_id": analysis.analysis_id,
                "employee_id": analysis.employee_id,
                "year": analysis.year,
                "quarter": analysis.quarter,
                "period_start": analysis.period_start,
                "period_end": analysis.period_end,
                "monthly_analysis_ids": analysis.monthly_analysis_ids,
                
                # Strategic alignment fields
                "organizational_impact": analysis.organizational_impact,
                "strategic_alignment_json": analysis.strategic_alignment_json,
                
                # Performance trajectory fields
                "performance_trend": analysis.performance_trend,
                "task_completion_reliability": analysis.task_completion_reliability,
                "work_quality_consistency": analysis.work_quality_consistency,
                "performance_stability": analysis.performance_stability,
                "performance_trajectory_json": analysis.performance_trajectory_json,
                
                # Cross-functional impact
                "collaboration_effectiveness": analysis.collaboration_effectiveness,
                "stakeholder_count": analysis.stakeholder_count,
                "cross_functional_impact_json": analysis.cross_functional_impact_json,
                
                # Risk assessment
                "risk_level": analysis.risk_level,
                "risk_trend": analysis.risk_trend,
                "risk_assessment_json": analysis.risk_assessment_json,
                
                # Skills and development
                "learning_agility": analysis.learning_agility,
                "autonomy_level": analysis.autonomy_level,
                "development_focus": analysis.development_focus,
                "skill_development_json": analysis.skill_development_json,
                
                # Credibility metrics
                "credibility_rating": analysis.credibility_rating,
                "vision_data_alignment": analysis.vision_data_alignment,
                "credibility_assessment_json": analysis.credibility_assessment_json,
                
                # Challenge patterns
                "adaptation_effectiveness": analysis.adaptation_effectiveness,
                "challenge_patterns_json": analysis.challenge_patterns_json,
                
                # Other complex JSON fields
                "achievement_themes_json": analysis.achievement_themes_json,
                "behavioral_assessment_json": analysis.behavioral_assessment_json,
                "forward_planning_json": analysis.forward_planning_json,
                
                # Summary and complete data
                "quarterly_summary": analysis.quarterly_summary,
                "full_analysis_json": analysis.full_analysis_json,
                
                # Metadata
                "analysis_date": analysis.analysis_date
            }
    except Exception as e:
        logger.error(f"Error checking for quarterly analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def store_quarterly_analysis(analysis_data: Dict[str, Any]) -> Optional[int]:
    """
    Store quarterly analysis results in the database.
    
    Args:
        analysis_data: Dictionary containing all analysis data
        
    Returns:
        ID of the stored analysis, or None if operation failed
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:
            # Extract key fields
            employee_id = analysis_data.get("employee_id")
            year = analysis_data.get("year")
            quarter = analysis_data.get("quarter")
            
            if not all([employee_id, year, quarter]):
                logger.error(f"Missing required fields for quarterly analysis: employee_id={employee_id}, year={year}, quarter={quarter}")
                return None
                
            # Check if analysis exists
            existing = session.query(QuarterlyAnalysis).filter(
                QuarterlyAnalysis.employee_id == employee_id,
                QuarterlyAnalysis.year == year,
                QuarterlyAnalysis.quarter == quarter
            ).first()
            
            if existing:
                # Update existing analysis
                logger.info(f"Updating existing quarterly analysis for employee {employee_id}, {year}-Q{quarter}")
                
                # Update all fields from analysis_data
                for key, value in analysis_data.items():
                    if hasattr(existing, key) and key != "analysis_id":
                        setattr(existing, key, value)
                
                analysis = existing
            else:
                # Create new analysis
                logger.info(f"Creating new quarterly analysis for employee {employee_id}, {year}-Q{quarter}")
                
                # Create new QuarterlyAnalysis object
                analysis = QuarterlyAnalysis(
                    employee_id=employee_id,
                    year=year,
                    quarter=quarter,
                    period_start=analysis_data.get("period_start"),
                    period_end=analysis_data.get("period_end"),
                    monthly_analysis_ids=analysis_data.get("monthly_analysis_ids"),
                    
                    # Strategic alignment fields
                    organizational_impact=analysis_data.get("organizational_impact"),
                    strategic_alignment_json=analysis_data.get("strategic_alignment_json"),
                    
                    # Performance trajectory fields
                    performance_trend=analysis_data.get("performance_trend"),
                    task_completion_reliability=analysis_data.get("task_completion_reliability"),
                    work_quality_consistency=analysis_data.get("work_quality_consistency"),
                    performance_stability=analysis_data.get("performance_stability"),
                    performance_trajectory_json=analysis_data.get("performance_trajectory_json"),
                    
                    # Cross-functional impact
                    collaboration_effectiveness=analysis_data.get("collaboration_effectiveness"),
                    stakeholder_count=analysis_data.get("stakeholder_count"),
                    cross_functional_impact_json=analysis_data.get("cross_functional_impact_json"),
                    
                    # Risk assessment
                    risk_level=analysis_data.get("risk_level"),
                    risk_trend=analysis_data.get("risk_trend"),
                    risk_assessment_json=analysis_data.get("risk_assessment_json"),
                    
                    # Skills and development
                    learning_agility=analysis_data.get("learning_agility"),
                    autonomy_level=analysis_data.get("autonomy_level"),
                    development_focus=analysis_data.get("development_focus"),
                    skill_development_json=analysis_data.get("skill_development_json"),
                    
                    # Credibility metrics
                    credibility_rating=analysis_data.get("credibility_rating"),
                    vision_data_alignment=analysis_data.get("vision_data_alignment"),
                    credibility_assessment_json=analysis_data.get("credibility_assessment_json"),
                    
                    # Challenge patterns
                    adaptation_effectiveness=analysis_data.get("adaptation_effectiveness"),
                    challenge_patterns_json=analysis_data.get("challenge_patterns_json"),
                    
                    # Other complex JSON fields
                    achievement_themes_json=analysis_data.get("achievement_themes_json"),
                    behavioral_assessment_json=analysis_data.get("behavioral_assessment_json"),
                    forward_planning_json=analysis_data.get("forward_planning_json"),
                    
                    # Summary and complete data
                    quarterly_summary=analysis_data.get("quarterly_summary"),
                    full_analysis_json=analysis_data.get("full_analysis_json")
                )
                
                session.add(analysis)
            
            # Commit the changes
            session.commit()
            session.refresh(analysis)
            
            logger.info(f"Successfully stored quarterly analysis with ID {analysis.analysis_id}")
            return analysis.analysis_id
            
    except Exception as e:
        logger.error(f"Error storing quarterly analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_employee_vision_data_for_quarter(employee_id: int, year: int, quarter: int) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for all months in a given quarter.
    
    Args:
        employee_id: The ID of the employee
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Dictionary containing quarter-wise vision data
    """
    start_date, end_date = get_quarter_date_range(year, quarter)
    
    result = {
        "date_context": {
            "quarter": quarter,
            "year": year,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        },
        "months_data": []
    }

    try:
        # Get the three months in this quarter
        months_in_quarter = [(quarter - 1) * 3 + i + 1 for i in range(3)]
        
        # Get vision data for each month in the quarter
        for month in months_in_quarter:
            month_vision_data = get_employee_vision_data_for_month(employee_id, year, month)
            
            if month_vision_data and month_vision_data.get("weeks_data"):
                month_name = {
                    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                }.get(month, f"Month {month}")
                
                # Add month name to the month data
                month_vision_data["month_name"] = month_name
                result["months_data"].append(month_vision_data)

        logger.info(f"Retrieved vision data for employee {employee_id} for {year}-Q{quarter}: {len(result['months_data'])} months")
        return result

    except Exception as e:
        logger.error(f"Error fetching quarterly vision data for employee {employee_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result

def get_weekly_analyses_for_quarter(employee_id: int, year: int, quarter: int) -> List[Dict[str, Any]]:
    """
    Fetch all weekly analyses for an employee for a specific quarter.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        List of dictionaries containing weekly analysis data and metadata
    """
    start_date, end_date = get_quarter_date_range(year, quarter)
    logger.info(f"Fetching weekly analyses for employee {employee_id} from {start_date} to {end_date}")
    
    db_instance = get_database()
    analyses = []
    
    try:
        with db_instance.create_session() as session:
            # First get reports for the specified quarter
            report_query = session.query(Report).filter(
                Report.employee_id == employee_id,
                Report.report_date >= start_date,
                Report.report_date <= end_date
            )
            
            # Get the report IDs
            report_ids = [report.report_id for report in report_query.all()]
            
            if not report_ids:
                logger.warning(f"No reports found for employee {employee_id} in {year}-Q{quarter}")
                return []
            
            # Get analyses for these reports
            analysis_query = session.query(EmployeeAnalysis, Report).join(
                Report, EmployeeAnalysis.report_id == Report.report_id
            ).filter(
                EmployeeAnalysis.report_id.in_(report_ids)
            ).order_by(Report.report_date)
            
            # Format results
            for analysis, report in analysis_query.all():
                analyses.append({
                    "analysis_id": analysis.analysis_id,
                    "report_id": str(analysis.report_id),
                    "date": report.report_date,
                    "analysis_date": analysis.analysis_date,
                    "sentiment_score": analysis.sentiment_score,
                    "risk_level": analysis.risk_level,
                    "risk_explanation": analysis.risk_explanation,
                    "achievements": analysis.achievements_json,
                    "challenges": analysis.challenges_json,
                    "topics": analysis.topics,
                    "action_items": analysis.action_items,
                    "full_analysis": analysis.full_analysis_json,
                    
                    # Credibility assessment fields
                    "credibility_rating": analysis.credibility_rating,
                    "credibility_explanation": analysis.credibility_explanation,
                    "exaggeration_flags": analysis.exaggeration_flags,
                    "consistency_score": analysis.consistency_score,
                    
                    # Performance assessment fields
                    "performance_rating": analysis.performance_rating,
                    "performance_summary": analysis.performance_summary,
                    "performance_strengths": analysis.performance_strengths,
                    "performance_improvement_areas": analysis.performance_improvement_areas,
                    
                    # Audit timestamps
                    "created_at": analysis.created_at,
                    "updated_at": analysis.updated_at
                })
            
            logger.info(f"Found {len(analyses)} weekly analyses for employee {employee_id} in {year}-Q{quarter}")
            return analyses
            
    except Exception as e:
        logger.error(f"Error fetching weekly analyses for quarter: {e}")
        return []
