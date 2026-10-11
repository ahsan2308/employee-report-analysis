"""Weekly, monthly and quarterly analysis queries and storage."""
from typing import List, Dict, Optional, Any
from app.db.database import get_database
from app.models.db_models import Report, EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis
from app.core.logger import logger
from app.domain.periods import get_month_date_range, get_quarter_date_range
from sqlalchemy.orm import Session


def find_monthly_analysis(session: Session, employee_id: int, year: int, month: int) -> Optional[MonthlyAnalysis]:
    """The monthly analysis row for an employee's month, in the caller's session."""
    return session.query(MonthlyAnalysis).filter(
        MonthlyAnalysis.employee_id == employee_id,
        MonthlyAnalysis.year == year,
        MonthlyAnalysis.month == month
    ).first()


def find_quarterly_analysis(session: Session, employee_id: int, year: int, quarter: int) -> Optional[QuarterlyAnalysis]:
    """The quarterly analysis row for an employee's quarter, in the caller's session."""
    return session.query(QuarterlyAnalysis).filter(
        QuarterlyAnalysis.employee_id == employee_id,
        QuarterlyAnalysis.year == year,
        QuarterlyAnalysis.quarter == quarter
    ).first()


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
                "monthly_achievements": analysis.monthly_achievements,  
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
