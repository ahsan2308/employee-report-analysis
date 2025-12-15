"""
Monthly Analysis DB Service

Provides functionality for aggregating and analyzing monthly employee data.
This service acts as a layer between the database and analysis tasks.
"""
from typing import List, Dict, Optional, Any
from datetime import date

from app.core.logger import logger
from app.services.db_service import (
    get_month_date_range, 
    get_reports_for_month, 
    get_analyses_for_month,
    get_employee_info
)

from app.services.db_service import get_employee_job_descriptions_for_period
from app.services.additional_services import map_reports_to_jds

def get_monthly_data_for_analysis(employee_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Aggregate all data needed for monthly analysis, including reports, analyses,
    and employee information.
    
    Args:
        employee_id: The employee's ID
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Dictionary containing all data needed for monthly analysis
    """
    logger.info(f"Gathering monthly analysis data for employee {employee_id}, {year}-{month}")
    
    result = {
        "year": year,
        "month": month,
        "employee_id": employee_id,
        "employee_info": None,
        "reports": [],
        "analyses": [],
        "period_start": None,
        "period_end": None,
        "metrics": {
            "report_count": 0,
            "avg_sentiment": 0.0,
            "sentiment_trend": "stable",
            "risk_levels": {},
            "recurring_topics": [],
            "achievement_count": 0,
            "challenge_count": 0,
            "achievement_impact_avg": 0.0 
        }
    }
    
    try:
        # Get date range for the month
        start_date, end_date = get_month_date_range(year, month)
        result["period_start"] = start_date
        result["period_end"] = end_date
        
        # Get employee information using db_service
        employee_info = get_employee_info(employee_id)
        if not employee_info:
            logger.error(f"Employee with ID {employee_id} not found")
            return result
            
        result["employee_info"] = employee_info
        
        # Get all reports for the month using db_service
        reports = get_reports_for_month(employee_id, year, month)
        result["reports"] = reports
        result["metrics"]["report_count"] = len(reports)
        
        # Get all analyses for the month using db_service
        analyses = get_analyses_for_month(employee_id, year, month)
        result["analyses"] = analyses
        
        # Calculate metrics if we have analyses
        if analyses:
            # Calculate average sentiment
            sentiment_scores = [a.get("sentiment_score", 0.5) for a in analyses if a.get("sentiment_score") is not None]
            if sentiment_scores:
                result["metrics"]["avg_sentiment"] = round(sum(sentiment_scores) / len(sentiment_scores), 2)
            
            # Calculate sentiment trend (improving, declining, stable)
            if len(sentiment_scores) >= 2:
                # Sort by date
                sorted_analyses = sorted(analyses, key=lambda a: a.get("date"))
                sorted_scores = [a.get("sentiment_score", 0.5) for a in sorted_analyses if a.get("sentiment_score") is not None]
                
                if len(sorted_scores) >= 2:
                    first_half = sorted_scores[:len(sorted_scores)//2]
                    second_half = sorted_scores[len(sorted_scores)//2:]
                    
                    avg_first = sum(first_half) / len(first_half)
                    avg_second = sum(second_half) / len(second_half)
                    
                    if avg_second > avg_first + 0.1:
                        result["metrics"]["sentiment_trend"] = "improving"
                    elif avg_second < avg_first - 0.1:
                        result["metrics"]["sentiment_trend"] = "declining"
                    else:
                        result["metrics"]["sentiment_trend"] = "stable"
            
            # Count risk levels
            risk_levels = {}
            for analysis in analyses:
                risk = analysis.get("risk_level", "medium")
                risk_levels[risk] = risk_levels.get(risk, 0) + 1
            result["metrics"]["risk_levels"] = risk_levels
            
            # Find recurring topics
            all_topics = []
            for analysis in analyses:
                topics = analysis.get("topics", [])
                if topics:
                    all_topics.extend(topics)
            
            # Count topic frequencies and get top recurring ones
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Get topics that appear in multiple reports
            recurring_topics = [topic for topic, count in topic_counts.items() if count > 1]
            result["metrics"]["recurring_topics"] = recurring_topics
            
            # Count achievements and challenges
            total_achievements = []
            for analysis in analyses:
                achievements = analysis.get("achievements", [])
                challenges = analysis.get("challenges", [])
                result["metrics"]["achievement_count"] += len(achievements)
                result["metrics"]["challenge_count"] += len(challenges)
                
                # Add achievements to total collection for impact calculation
                if achievements:
                    total_achievements.extend(achievements)
            
            # Calculate achievement impact average
            achievement_impact_avg = 0.0
            impact_count = 0
            
            for achievement in total_achievements:
                impact_str = achievement.get("impact", "0")
                # Extract numeric part if in format "8 (reason)"
                if impact_str and isinstance(impact_str, str):
                    try:
                        impact_value = int(impact_str.split(" ")[0])
                        achievement_impact_avg += impact_value
                        impact_count += 1
                    except (ValueError, IndexError):
                        pass
            
            if impact_count > 0:
                result["metrics"]["achievement_impact_avg"] = round(achievement_impact_avg / impact_count, 2)
                logger.info(f"Calculated average achievement impact: {result['metrics']['achievement_impact_avg']} from {impact_count} achievements")
        
        # Retrieve job descriptions that overlap with the monthly period
        employee_jds = get_employee_job_descriptions_for_period(
            employee_id=employee_id,
            period_start=start_date,
            period_end=end_date
        )

        # Map reports to JDs based on temporal overlap
        # This creates groups showing which reports fall under which JD configuration
        jd_report_mapping = map_reports_to_jds(reports, employee_jds)

        # Store in result dictionary for downstream use
        result["jd_report_mapping"] = jd_report_mapping
        result["employee_jds"] = employee_jds

        logger.info(
            f"Monthly analysis: Retrieved {len(employee_jds)} JD(s), "
            f"created {len(jd_report_mapping.get('jd_groups', []))} JD groups, "
            f"{len(jd_report_mapping.get('unmapped_reports', []))} unmapped reports"
        )
        
        logger.info(f"Successfully gathered monthly data for employee {employee_id}, {year}-{month}")
        return result
        
    except Exception as e:
        logger.error(f"Error gathering monthly analysis data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result
