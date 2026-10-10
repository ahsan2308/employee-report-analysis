"""
Celery tasks for asynchronous report analysis.
"""
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from datetime import datetime, timedelta

from app.worker.celery_app import celery_app
from app.db.database import get_database
from app.models.task_models import BackgroundTask, TaskStatus, TaskType
from app.models.db_models import Report, Employee, EmployeeAnalysis
from app.services.vector_store_service import search_reports
from app.repositories.reports import get_reports_for_vector_results, get_recent_employee_reports
from app.repositories.vision_data import get_employee_vision_data
from app.repositories.analyses import get_monthly_analysis_by_params, store_monthly_analysis
from app.repositories.analyses import get_quarterly_analysis_by_params, store_quarterly_analysis
from app.repositories.job_descriptions import get_employee_job_descriptions_for_period
from app.services.analysis.jd_formatting import format_job_descriptions_for_weekly_prompt, format_job_descriptions_for_monthly_prompt, format_job_descriptions_for_quarterly_prompt
from app.services.monthly_analysis_db_service import get_monthly_data_for_analysis
from app.services.quarterly_analysis_db_service import get_quarterly_data_for_analysis
from app.services.llm_service import get_llm_service
from app.services.analysis.vision_formatting import filter_vision_data, format_vision_data_for_weekly_analysis_prompt
from app.services.analysis.vision_formatting import format_vision_data_for_monthly_analysis_prompt, format_vision_data_for_quarterly_analysis_prompt
from app.core.logger import logger
from app.repositories.vision_data import get_employee_vision_data_for_month, get_employee_vision_data_for_quarter

from app.core.settings import (
    VECTOR_SEARCH_HNSW_EF,
    MAX_CONTENT_ITEMS_PER_ENTITY_FOR_WEEKLY_ANALYSIS,
    MAX_CONTENT_ITEMS_PER_ENTITY_FOR_MONTHLY_ANALYSIS,
    MAX_CONTENT_ITEMS_PER_ENTITY_FOR_QUARTERLY_ANALYSIS,
    MAX_CONTENT_ITEM_LENGTH_WEEKLY,
    MAX_CONTENT_ITEM_LENGTH_MONTHLY,
    MAX_CONTENT_ITEM_LENGTH_QUARTERLY,
)

def _mark_task_failed(db, task_id: str, message: str) -> None:
    """Mark the BackgroundTask as FAILED with message, if the row exists."""
    with db.create_session() as session:
        task = session.query(BackgroundTask).filter(
            BackgroundTask.task_id == uuid.UUID(task_id)
        ).first()

        if task:
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now()
            task.error_message = message
            session.commit()


def _mark_task_failed_after_error(db, task_id: str, message: str) -> None:
    """Same, for the outer exception handlers: a failure to update is logged, not raised."""
    with db.create_session() as session:
        try:
            task = session.query(BackgroundTask).filter(
                BackgroundTask.task_id == uuid.UUID(task_id)
            ).first()

            if task:
                task.status = TaskStatus.FAILED.value
                task.completed_at = datetime.now()
                task.error_message = message
                session.commit()
        except Exception as update_error:
            logger.error(f"Failed to update task status: {str(update_error)}")


@celery_app.task(bind=True, name="app.tasks.analysis_tasks.analyze_report_task")
def analyze_report_task(self, task_id: str):
    """
    Celery task to analyze a report asynchronously.
    
    Args:
        self: The Celery task instance (automatically provided)
        task_id: The UUID of the BackgroundTask record
    
    Returns:
        dict: The analysis result data
    """
    celery_task_id = self.request.id
    logger.info(f"Starting analysis task {task_id} (Celery ID: {celery_task_id})")
    
    db = get_database()
    
    try:
        # Update task status to RUNNING
        with db.create_session() as session:
            # Get the task record and associated report
            task = session.query(BackgroundTask).filter(
                BackgroundTask.task_id == uuid.UUID(task_id)
            ).first()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Update celery_task_id and status
            task.celery_task_id = celery_task_id
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.now()
            session.commit()
            
            report_id = task.report_id
        
        # Get report data outside transaction to avoid holding connection
        with db.create_session() as session:
            report = session.query(Report).filter(Report.report_id == report_id).first()
            if not report:
                raise ValueError(f"Report {report_id} not found")
            
            employee = session.query(Employee).filter(
                Employee.id == report.employee_id
            ).first()
            if not employee:
                raise ValueError(f"Employee {report.employee_id} not found")
        
        # Perform analysis
        # Get recent reports for context - with clearer parameters
        target_recent_reports = 3  # Target number of recent reports
        target_similar_reports = 0  # Target number of similar historical reports
        
        logger.info(f"Fetching {target_recent_reports} most recent reports for employee {report.employee_id} (task: {task_id})")
        recent_report_data = get_recent_employee_reports(
            employee_id=report.employee_id,
            current_report_date=report.report_date,
            exclude_report_id=str(report_id),
            limit=target_recent_reports  
        )
        
        recent_count = len(recent_report_data)
        logger.info(f"Found {recent_count} recent reports for context")
        
        

        # # Determine cutoff date based on the oldest recent report or a fallback
        if recent_report_data and recent_count > 0:
            # Find the oldest report date in the returned data
            oldest_recent_report_date = min(report_data["date"] for report_data in recent_report_data)
            logger.info(f"Using oldest recent report date as cutoff: {oldest_recent_report_date}")
        else:
            # No recent reports, don't restrict the date range at all
            oldest_recent_report_date = report.report_date
            logger.info("No recent reports found")
            
        # Get similar reports for context - use the dynamic cutoff date (or None for unrestricted search)
        # logger.info(f"Finding similar reports for context with cutoff: {oldest_recent_report_date or 'None (unrestricted)'} (task: {task_id})")
        similar_reports_chunks = search_reports(
            query=report.report_text,
            employee_id=report.employee_id,
            top_k=target_similar_reports,  # Get exact number needed
            group_by_report=True,  # Ensure one chunk per report
            cutoff_date=oldest_recent_report_date,  # Only pass a date when we have recent reports
            search_params={"hnsw_ef": VECTOR_SEARCH_HNSW_EF}  # Add optimized search parameters
        )
        
        
        # Now get the complete reports based on the search results
        similar_report_data = get_reports_for_vector_results(similar_reports_chunks)
        
        logger.info(f"Found {len(similar_report_data)} semantically similar reports for context")
        
        # Get vision data, filter it, and format it
        raw_vision_data = get_employee_vision_data(report.employee_id, report.report_date, num_previous_weeks=4)
        filtered_vision_data = filter_vision_data(raw_vision_data)
        formatted_vision_data = format_vision_data_for_weekly_analysis_prompt(
            filtered_vision_data, 
            max_content_items_per_entity=MAX_CONTENT_ITEMS_PER_ENTITY_FOR_WEEKLY_ANALYSIS,
            max_content_item_length=MAX_CONTENT_ITEM_LENGTH_WEEKLY
        )
        
        report_week_start = report.report_date - timedelta(days=6)
        report_week_end = report.report_date

        employee_jds = get_employee_job_descriptions_for_period(
            employee_id=report.employee_id,
            period_start=report_week_start,
            period_end=report_week_end
        )

        formatted_jd_data = format_job_descriptions_for_weekly_prompt(employee_jds)


        # Get LLM service and generate analysis
        logger.info(f"Calling LLM service for analysis (task: {task_id})")
        llm_service = get_llm_service()
        analysis_result = llm_service.analyze_report(
            report.report_text, 
            formatted_vision_data,
            recent_report_data,     
            similar_report_data,
            formatted_jd_data,
            employee_info={
                "name": employee.name,
                "position": employee.position,
                "wing": employee.wing
            },
            num_ctx=64000
        )

        # Handle error in analysis generation
        if "error" in analysis_result and analysis_result["error"]:
            logger.error(f"Error in LLM analysis: {analysis_result['error']}")
            _mark_task_failed(db, task_id, f"LLM analysis failed: {analysis_result['error']}")

            return {"error": f"LLM analysis failed: {analysis_result['error']}"}

        # Extract key fields
        sentiment = analysis_result.get("sentiment", "neutral")
        risk_level = analysis_result.get("risk_level", "low")
        risk_explanation = analysis_result.get("risk_explanation", "")
        topics = analysis_result.get("topics", [])
        achievements = analysis_result.get("achievements", [])
        challenges = analysis_result.get("challenges", [])
        action_items = analysis_result.get("action_items", [])
        
        # Extract credibility assessment fields
        credibility_assessment = analysis_result.get("credibility_assessment", {})
        credibility_rating = credibility_assessment.get("rating", "medium")
        credibility_explanation = credibility_assessment.get("explanation", "")
        exaggeration_flags = credibility_assessment.get("exaggeration_flags", [])
        consistency_score = credibility_assessment.get("consistency_score", "medium")
        
        # Extract performance assessment fields
        performance_assessment = analysis_result.get("performance_assessment", {})
        performance_rating = performance_assessment.get("rating", "medium")
        performance_summary = performance_assessment.get("summary", "")
        performance_strengths = performance_assessment.get("key_strengths", [])
        performance_improvement_areas = performance_assessment.get("improvement_areas", [])
        
        # Calculate sentiment score
        sentiment_score = 0.0
        if sentiment == "positive":
            sentiment_score = 0.8
        elif sentiment == "negative":
            sentiment_score = 0.2
        elif sentiment == "neutral":
            sentiment_score = 0.5
        
        # Store analysis in the database
        with db.create_session() as session:
            # Create a new analysis record with enhanced fields
            new_analysis = EmployeeAnalysis(
                report_id=report_id,
                employee_id=report.employee_id,
                sentiment_score=sentiment_score,
                risk_level=risk_level,
                risk_explanation=risk_explanation,
                full_analysis_json=analysis_result,
                achievements_json=achievements,
                challenges_json=challenges,
                topics=topics,
                action_items=action_items,
                credibility_rating=credibility_rating,
                credibility_explanation=credibility_explanation,
                exaggeration_flags=exaggeration_flags,
                consistency_score=consistency_score,
                performance_rating=performance_rating,
                performance_summary=performance_summary,
                performance_strengths=performance_strengths,
                performance_improvement_areas=performance_improvement_areas
            )
            
            session.add(new_analysis)
            session.commit()
            session.refresh(new_analysis)
            
            # Prepare task result
            result_data = {
                "analysis_id": new_analysis.analysis_id,
                "report_id": str(new_analysis.report_id),
                "employee_name": employee.name,
                "sentiment": sentiment_score,
                "sentiment_score": sentiment_score,
                "risk_level": risk_level,
                "risk_explanation": risk_explanation,
                "full_analysis_json": analysis_result,
                "achievements_json": achievements,
                "challenges_json": challenges,
                "topics": topics,
                "action_items": action_items,
                "credibility_assessment": {
                    "rating": credibility_rating,
                    "explanation": credibility_explanation,
                    "exaggeration_flags": exaggeration_flags,
                    "consistency_score": consistency_score
                },
                "performance_assessment": {
                    "rating": performance_rating,
                    "summary": performance_summary,
                    "key_strengths": performance_strengths,
                    "improvement_areas": performance_improvement_areas
                }
            }

            
            
            # Update task as completed with result
            task = session.query(BackgroundTask).filter(
                BackgroundTask.task_id == uuid.UUID(task_id)
            ).first()
            
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now()
            task.result_data = result_data
            session.commit()
            
            logger.info(f"Analysis task {task_id} completed successfully")
            return result_data
            
    except SoftTimeLimitExceeded:
        logger.error(f"Analysis task {task_id} exceeded its time limit")
        _mark_task_failed_after_error(db, task_id, "Analysis exceeded the time limit")
        raise
    except Exception as e:
        logger.error(f"Error in analysis task {task_id}: {str(e)}")
        
        # Update task as failed
        _mark_task_failed_after_error(db, task_id, str(e))
        
        # Re-raise the exception for Celery to handle
        raise

@celery_app.task(bind=True, name="app.tasks.analysis_tasks.analyze_monthly_reports_task")
def analyze_monthly_reports_task(self, task_id: str):
    """
    Celery task to analyze an employee's monthly performance asynchronously.
    
    Args:
        self: The Celery task instance (automatically provided)
        task_id: The UUID of the BackgroundTask record
    
    Returns:
        dict: The monthly analysis result data
    """
    celery_task_id = self.request.id
    logger.info(f"Starting monthly analysis task {task_id} (Celery ID: {celery_task_id})")
    
    db = get_database()
    
    try:
        # Update task status to RUNNING
        with db.create_session() as session:
            # Get the task record and associated parameters
            task = session.query(BackgroundTask).filter(
                BackgroundTask.task_id == uuid.UUID(task_id)
            ).first()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Verify this is a monthly analysis task
            if task.task_type != TaskType.MONTHLY_ANALYSIS.value:
                logger.error(f"Task {task_id} is not a monthly analysis task")
                return {"error": "Incorrect task type"}
            
            # Update celery_task_id and status
            task.celery_task_id = celery_task_id
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.now()
            session.commit()
            
            # Extract parameters
            employee_id = task.employee_id
            year = task.year
            month = task.month
            
            if not all([employee_id, year, month]):
                raise ValueError(f"Missing required parameters: employee_id={employee_id}, year={year}, month={month}")
        
        # Get employee data outside transaction to avoid holding connection
        with db.create_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise ValueError(f"Employee {employee_id} not found")
        
        # Check if analysis already exists
        existing_analysis = get_monthly_analysis_by_params(employee_id, year, month)
        if existing_analysis:
            logger.info(f"Monthly analysis for employee {employee_id}, {year}-{month} already exists")
            
            # Update task as completed with reference to existing analysis
            with db.create_session() as session:
                task = session.query(BackgroundTask).filter(
                    BackgroundTask.task_id == uuid.UUID(task_id)
                ).first()
                
                if task:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.now()
                    task.result_data = {
                        "analysis_id": existing_analysis["analysis_id"],
                        "employee_id": employee_id,
                        "year": year,
                        "month": month,
                        "message": "Analysis already exists"
                    }
                    session.commit()
                    
            return {
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "month": month,
                "message": "Analysis already exists"
            }
        
        # Gather monthly data using the monthly analysis service
        logger.info(f"Gathering data for employee {employee_id}, {year}-{month}")
        monthly_data = get_monthly_data_for_analysis(employee_id, year, month)

        # Add vision data for the month
        raw_monthly_vision_data = get_employee_vision_data_for_month(employee_id, year, month)
        filtered_monthly_vision_data = filter_vision_data(raw_monthly_vision_data)
        formatted_monthly_vision_data = format_vision_data_for_monthly_analysis_prompt(
            filtered_monthly_vision_data, 
            max_content_items_per_entity=MAX_CONTENT_ITEMS_PER_ENTITY_FOR_MONTHLY_ANALYSIS,
            max_content_item_length=MAX_CONTENT_ITEM_LENGTH_MONTHLY
        )
        
        monthly_data["formatted_vision_data"] = formatted_monthly_vision_data
        
        logger.info(f"Formatted vision data for employee {employee_id}, {year}-{month}: {len(formatted_monthly_vision_data)} characters")

        # Format JD data for monthly prompt
        # Use the jd_report_mapping which contains temporal groupings
        jd_report_mapping = monthly_data.get("jd_report_mapping", {})
        formatted_jd_data = format_job_descriptions_for_monthly_prompt(jd_report_mapping)

        # Add to monthly_data for prompt access
        monthly_data["formatted_jd_data"] = formatted_jd_data

        logger.info(f"Formatted JD data for monthly analysis: {len(formatted_jd_data)} characters")

        # Check if we have any reports for this month
        if not monthly_data["reports"] or len(monthly_data["reports"]) == 0:
            logger.warning(f"No reports found for employee {employee_id} in {year}-{month}")
            _mark_task_failed(db, task_id, f"No reports found for employee {employee_id} in {year}-{month}")
            
            return {"error": f"No reports found for employee {employee_id} in {year}-{month}"}
        
        # Get LLM service and generate analysis
        logger.info(f"Calling LLM service for monthly analysis (task: {task_id})")
        llm_service = get_llm_service()
        analysis_result = llm_service.analyze_monthly_reports(
            monthly_data=monthly_data,
            num_ctx=80000
        )

        # Handle error in analysis generation
        if "error" in analysis_result and analysis_result["error"]:
            logger.error(f"Error in LLM analysis: {analysis_result['error']}")
            _mark_task_failed(db, task_id, f"LLM analysis failed: {analysis_result['error']}")
            
            return {"error": f"LLM analysis failed: {analysis_result['error']}"}
        
        # Extract key fields from analysis result
        try:
            # Extract progress trends
            progress_trends = analysis_result.get("progress_trends", {})
            performance_trend = progress_trends.get("performance_trend", "stable")
            sentiment_trend = progress_trends.get("sentiment_trend", "stable")
            risk_level_pattern = progress_trends.get("risk_level_pattern", "stable")
            challenge_resolution_progress = progress_trends.get("challenge_resolution_progress", "unchanged")
            
            # Extract monthly achievements
            monthly_achievements = analysis_result.get("monthly_achievements", [])
            
            # Extract recurring challenges
            recurring_challenges = analysis_result.get("recurring_challenges", [])
            
            # Extract consistency assessment
            consistency_assessment = analysis_result.get("consistency_assessment", {})
            task_completion_reliability = consistency_assessment.get("task_completion_reliability", "medium")
            work_quality_consistency = consistency_assessment.get("work_quality_consistency", "medium")
            performance_stability = consistency_assessment.get("performance_stability", "medium") 
            consistency_notable_strengths = consistency_assessment.get("notable_strengths", [])
            consistency_notable_weaknesses = consistency_assessment.get("notable_weaknesses", [])
            
            # Extract growth indicators
            growth_indicators = analysis_result.get("growth_indicators", {})
            complexity_of_tasks = growth_indicators.get("complexity_of_tasks", "unchanged")
            skill_development_evidence = growth_indicators.get("skill_development_evidence", "medium")
            confidence_level_change = growth_indicators.get("confidence_level_change", "unchanged") 
            approach_to_challenges = growth_indicators.get("approach_to_challenges", "unchanged")
            
            # Extract focus areas (store as array)
            focus_areas = analysis_result.get("focus_areas", [])
            
            # Extract risk assessment
            monthly_risk_assessment = analysis_result.get("monthly_risk_assessment", {})
            risk_level = monthly_risk_assessment.get("overall_risk_level", "medium")
            risk_explanation = monthly_risk_assessment.get("risk_explanation", "")
            significant_risks = monthly_risk_assessment.get("significant_risks", [])
            escalating_risks = monthly_risk_assessment.get("escalating_risks", [])
            risk_mitigation_recommendations = monthly_risk_assessment.get("risk_mitigation_recommendations", [])
            
            # Extract strategic recommendations
            strategic_recommendations = analysis_result.get("strategic_recommendations", [])
            
            # Extract monthly summary
            monthly_summary = analysis_result.get("monthly_summary", "")
            
            # Calculate achievement impact average if not already provided in metrics
            achievement_impact_avg = monthly_data["metrics"].get("achievement_impact_avg", 0.0)
            
            # If no pre-calculated value, calculate it from the LLM-generated achievements
            if achievement_impact_avg == 0.0:
                impact_count = 0
                impact_sum = 0.0
                
                for achievement in monthly_achievements:
                    impact_score = achievement.get("impact_score", 0)
                    try:
                        impact_value = int(impact_score)
                        impact_sum += impact_value
                        impact_count += 1
                    except (ValueError, IndexError):
                        pass
                
                if impact_count > 0:
                    achievement_impact_avg = round(impact_sum / impact_count, 2)
                    logger.info(f"Calculated achievement impact average from LLM results: {achievement_impact_avg}")
            else:
                logger.info(f"Using pre-calculated achievement impact average: {achievement_impact_avg}")
        
            # Get report IDs included in the analysis
            report_ids = [str(report.get("report_id")) for report in monthly_data["reports"] if "report_id" in report]
            
            # Prepare data for storage with all fields
            analysis_data = {
                "employee_id": employee_id,
                "year": year,
                "month": month,
                "period_start": monthly_data["period_start"],
                "period_end": monthly_data["period_end"],
                "weekly_report_ids": report_ids,
                "avg_sentiment_score": monthly_data["metrics"]["avg_sentiment"],
                
                # Progress trends fields
                "sentiment_trend": sentiment_trend,
                "performance_trend": performance_trend,
                "risk_level_pattern": risk_level_pattern,
                "challenge_resolution_progress": challenge_resolution_progress,
                
                # Risk assessment fields
                "risk_level": risk_level,
                "risk_explanation": risk_explanation,
                "significant_risks": significant_risks,
                "escalating_risks": escalating_risks,
                "risk_mitigation_recommendations": risk_mitigation_recommendations,
                
                # Monthly achievements & challenges
                "monthly_achievements": monthly_achievements,
                "recurring_challenges": recurring_challenges,
                "achievement_impact_avg": achievement_impact_avg,
                
                # Consistency assessment fields
                "task_completion_reliability": task_completion_reliability,
                "work_quality_consistency": work_quality_consistency,
                "performance_stability": performance_stability,
                "consistency_notable_strengths": consistency_notable_strengths,
                "consistency_notable_weaknesses": consistency_notable_weaknesses,
                
                # Growth indicators
                "complexity_of_tasks": complexity_of_tasks,
                "skill_development_evidence": skill_development_evidence,
                "confidence_level_change": confidence_level_change,
                "approach_to_challenges": approach_to_challenges,
                
                # Focus areas & recommendations
                "focus_areas": focus_areas,
                "strategic_recommendations": strategic_recommendations,
                
                # Summary and complete data
                "monthly_summary": monthly_summary,
                "full_analysis_json": analysis_result
            }
            
            # Store analysis in the database
            analysis_id = store_monthly_analysis(analysis_data)
            
            if not analysis_id:
                logger.error("Failed to store monthly analysis")
                _mark_task_failed(db, task_id, "Failed to store monthly analysis")
                
                return {"error": "Failed to store monthly analysis"}
            
            # Prepare task result
            result_data = {
                "analysis_id": analysis_id,
                "employee_id": employee_id,
                "employee_name": employee.name,
                "year": year,
                "month": month,
                "period_start": monthly_data["period_start"].isoformat() if hasattr(monthly_data["period_start"], "isoformat") else monthly_data["period_start"],
                "period_end": monthly_data["period_end"].isoformat() if hasattr(monthly_data["period_end"], "isoformat") else monthly_data["period_end"],
                "performance_trend": performance_trend,
                "sentiment_trend": sentiment_trend,
                "risk_level": risk_level,
                "achievement_count": len(monthly_achievements),
                "challenge_count": len(recurring_challenges),
                "monthly_summary": monthly_summary  
            }
            
            # Update task as completed with result
            with db.create_session() as session:
                task = session.query(BackgroundTask).filter(
                    BackgroundTask.task_id == uuid.UUID(task_id)
                ).first()
                
                if task:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.now()
                    task.result_data = result_data
                    session.commit()
                    
                    logger.info(f"Monthly analysis task {task_id} completed successfully")
                    return result_data
                else:
                    logger.error(f"Task {task_id} not found when updating status")
                    return {"error": "Task not found when updating status"}
                
        except Exception as e:
            logger.error(f"Error processing monthly analysis result: {str(e)}")
            _mark_task_failed(db, task_id, f"Error processing analysis result: {str(e)}")
            
            return {"error": f"Error processing analysis result: {str(e)}"}
            
    except SoftTimeLimitExceeded:
        logger.error(f"Analysis task {task_id} exceeded its time limit")
        _mark_task_failed_after_error(db, task_id, "Analysis exceeded the time limit")
        raise
    except Exception as e:
        logger.error(f"Error in monthly analysis task {task_id}: {str(e)}")
        
        # Update task as failed
        _mark_task_failed_after_error(db, task_id, str(e))
        
        # Re-raise the exception for Celery to handle
        raise

@celery_app.task(bind=True, name="app.tasks.analysis_tasks.analyze_quarterly_reports_task")
def analyze_quarterly_reports_task(self, task_id: str):
    """
    Celery task to analyze an employee's quarterly performance asynchronously.
    
    Args:
        self: The Celery task instance (automatically provided)
        task_id: The UUID of the BackgroundTask record
    
    Returns:
        dict: The quarterly analysis result data
    """
    celery_task_id = self.request.id
    logger.info(f"Starting quarterly analysis task {task_id} (Celery ID: {celery_task_id})")
    
    db = get_database()
    
    try:
        # Update task status to RUNNING
        with db.create_session() as session:
            # Get the task record and associated parameters
            task = session.query(BackgroundTask).filter(
                BackgroundTask.task_id == uuid.UUID(task_id)
            ).first()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Verify this is a quarterly analysis task
            if task.task_type != TaskType.QUARTERLY_ANALYSIS.value:
                logger.error(f"Task {task_id} is not a quarterly analysis task")
                return {"error": "Incorrect task type"}
            
            # Update celery_task_id and status
            task.celery_task_id = celery_task_id
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.now()
            session.commit()
            
            # Extract parameters
            employee_id = task.employee_id
            year = task.year
            quarter = task.quarter
            
            if not all([employee_id, year, quarter]):
                raise ValueError(f"Missing required parameters: employee_id={employee_id}, year={year}, quarter={quarter}")
        
        # Get employee data outside transaction to avoid holding connection
        with db.create_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise ValueError(f"Employee {employee_id} not found")
        

        existing_analysis = get_quarterly_analysis_by_params(employee_id, year, quarter)
        if existing_analysis:
            logger.info(f"Quarterly analysis for employee {employee_id}, {year}-Q{quarter} already exists")
            
            # Update task as completed with reference to existing analysis
            with db.create_session() as session:
                task = session.query(BackgroundTask).filter(
                    BackgroundTask.task_id == uuid.UUID(task_id)
                ).first()
                
                if task:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.now()
                    task.result_data = {
                        "analysis_id": existing_analysis["analysis_id"],
                        "employee_id": employee_id,
                        "year": year,
                        "quarter": quarter,
                        "message": "Analysis already exists"
                    }
                    session.commit()
                    
            return {
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "quarter": quarter,
                "message": "Analysis already exists"
            }
        
        # Gather quarterly data using the quarterly analysis service
        logger.info(f"Gathering data for employee {employee_id}, {year}-Q{quarter}")
        quarterly_data = get_quarterly_data_for_analysis(employee_id, year, quarter)

        # Add vision data for the quarter
        raw_quarterly_vision_data = get_employee_vision_data_for_quarter(employee_id, year, quarter)
        filtered_quarterly_vision_data = filter_vision_data(raw_quarterly_vision_data)
        
       
        formatted_quarterly_vision_data = format_vision_data_for_quarterly_analysis_prompt(
            filtered_quarterly_vision_data, 
            max_content_items_per_entity=MAX_CONTENT_ITEMS_PER_ENTITY_FOR_QUARTERLY_ANALYSIS,
            max_content_item_length=MAX_CONTENT_ITEM_LENGTH_QUARTERLY
        )
        quarterly_data["formatted_vision_data"] = formatted_quarterly_vision_data

        logger.info(f"Formatted vision data for employee {employee_id}, {year}-Q{quarter}")

        # Format JD data for quarterly prompt
        # Use the jd_analysis_mapping which contains career progression phases
        jd_analysis_mapping = quarterly_data.get("jd_analysis_mapping", {})
        formatted_jd_data = format_job_descriptions_for_quarterly_prompt(jd_analysis_mapping)

        # Add to quarterly_data for prompt access
        quarterly_data["formatted_jd_data"] = formatted_jd_data

        logger.info(f"Formatted JD data for quarterly analysis: {len(formatted_jd_data)} characters")

        # Check if we have any monthly analyses for this quarter
        if not quarterly_data["monthly_analyses"] or len(quarterly_data["monthly_analyses"]) == 0:
            logger.warning(f"No monthly analyses found for employee {employee_id} in {year}-Q{quarter}")
            _mark_task_failed(db, task_id, f"No monthly analyses found for employee {employee_id} in {year}-Q{quarter}")
            
            return {"error": f"No monthly analyses found for employee {employee_id} in {year}-Q{quarter}"}
        
        # Get LLM service and generate analysis
        logger.info(f"Calling LLM service for quarterly analysis (task: {task_id})")
        llm_service = get_llm_service()
        analysis_result = llm_service.analyze_quarterly_reports(
            quarterly_data=quarterly_data,
            num_ctx=40000  
        )

        # Handle error in analysis generation
        if "error" in analysis_result and analysis_result["error"]:
            logger.error(f"Error in LLM analysis: {analysis_result['error']}")
            _mark_task_failed(db, task_id, f"LLM analysis failed: {analysis_result['error']}")
            
            return {"error": f"LLM analysis failed: {analysis_result['error']}"}
        
        # Extract key fields from analysis result
        try:
            # Extract strategic alignment
            strategic_alignment = analysis_result.get("strategic_alignment", {})
            organizational_impact = strategic_alignment.get("organizational_impact", "individual")
            key_initiatives = strategic_alignment.get("key_initiatives", [])
            
            # Extract achievement themes
            achievement_themes = analysis_result.get("achievement_themes", [])
            
            # Extract performance trajectory
            performance_trajectory = analysis_result.get("performance_trajectory", {})
            performance_trend = performance_trajectory.get("trend", "stable")
            consistency_metrics = performance_trajectory.get("consistency", {})
            task_completion_reliability = consistency_metrics.get("task_completion_reliability", "medium")
            work_quality_consistency = consistency_metrics.get("work_quality_consistency", "medium")
            performance_stability = consistency_metrics.get("performance_stability", "medium")
            notable_shifts = performance_trajectory.get("notable_shifts", [])
            
            # Extract challenge patterns
            challenge_patterns = analysis_result.get("challenge_patterns", {})
            recurring_challenges = challenge_patterns.get("recurring_challenges", [])
            adaptation_effectiveness = challenge_patterns.get("adaptation_effectiveness", "medium")
            
            # Extract cross-functional impact
            cross_functional_impact = analysis_result.get("cross_functional_impact", {})
            collaboration_effectiveness = cross_functional_impact.get("collaboration_effectiveness", "medium")
            stakeholder_impacts = cross_functional_impact.get("stakeholder_impacts", [])
            
            # Calculate stakeholder count
            stakeholder_count = len(stakeholder_impacts)
            
            # Extract risk assessment
            risk_assessment = analysis_result.get("risk_assessment", {})
            risk_level = risk_assessment.get("overall_risk_level", "medium")
            risk_trend = risk_assessment.get("risk_trend", "stable")
            key_risk_factors = risk_assessment.get("key_risk_factors", [])
            mitigation_strategies = risk_assessment.get("mitigation_strategies", [])
            
            # Extract skill development
            skill_development = analysis_result.get("skill_development", {})
            key_capabilities = skill_development.get("key_capabilities", [])
            learning_agility = skill_development.get("learning_agility", "medium")
            autonomy_level = skill_development.get("autonomy_level", "medium")
            development_focus = skill_development.get("development_focus", "")
            
            # Extract behavioral assessment
            behavioral_assessment = analysis_result.get("behavioral_assessment", {})
            
            # Extract credibility assessment
            credibility_assessment = analysis_result.get("credibility_assessment", {})
            credibility_rating = credibility_assessment.get("rating", "medium")
            vision_data_alignment = credibility_assessment.get("vision_data_alignment", "none") 
            forward_planning = analysis_result.get("forward_planning", {})
            
            # Extract quarterly summary
            quarterly_summary = analysis_result.get("quarterly_summary", "")
            
            # Get monthly analysis IDs included in this analysis
            monthly_analysis_ids = [ma.get("analysis_id") for ma in quarterly_data["monthly_analyses"] if "analysis_id" in ma]
            
            # Prepare data for storage with all fields
            analysis_data = {
                "employee_id": employee_id,
                "year": year,
                "quarter": quarter,
                "period_start": quarterly_data["period_start"],
                "period_end": quarterly_data["period_end"],
                "monthly_analysis_ids": monthly_analysis_ids,
                
                # Strategic alignment fields
                "organizational_impact": organizational_impact,
                
                # Performance trajectory fields
                "performance_trend": performance_trend,
                "task_completion_reliability": task_completion_reliability,
                "work_quality_consistency": work_quality_consistency,
                "performance_stability": performance_stability,
                
                # Cross-functional impact
                "collaboration_effectiveness": collaboration_effectiveness,
                "stakeholder_count": stakeholder_count,
                
                # Risk assessment
                "risk_level": risk_level,
                "risk_trend": risk_trend,
                
                # Skills and development
                "learning_agility": learning_agility,
                "autonomy_level": autonomy_level,
                "development_focus": development_focus,
                
                # Credibility metrics
                "credibility_rating": credibility_rating,
                "vision_data_alignment": vision_data_alignment,
                
                # Challenge patterns
                "adaptation_effectiveness": adaptation_effectiveness,
                
                # Complex structures stored as JSONB
                "strategic_alignment_json": strategic_alignment,
                "achievement_themes_json": achievement_themes,
                "performance_trajectory_json": performance_trajectory,
                "challenge_patterns_json": challenge_patterns,
                "cross_functional_impact_json": cross_functional_impact,
                "skill_development_json": skill_development,
                "behavioral_assessment_json": behavioral_assessment,
                "risk_assessment_json": risk_assessment,
                "credibility_assessment_json": credibility_assessment,
                "forward_planning_json": forward_planning,
                
                # Summary and complete data
                "quarterly_summary": quarterly_summary,
                "full_analysis_json": analysis_result
            }
            
            # store_quarterly_analysis
            analysis_id = store_quarterly_analysis(analysis_data)
            
            if not analysis_id:
                logger.error("Failed to store quarterly analysis")
                _mark_task_failed(db, task_id, "Failed to store quarterly analysis")
                
                return {"error": "Failed to store quarterly analysis"}
            
            # Prepare task result
            result_data = {
                "analysis_id": analysis_id,
                "employee_id": employee_id,
                "employee_name": employee.name,
                "year": year,
                "quarter": quarter,
                "period_start": quarterly_data["period_start"].isoformat() if hasattr(quarterly_data["period_start"], "isoformat") else quarterly_data["period_start"],
                "period_end": quarterly_data["period_end"].isoformat() if hasattr(quarterly_data["period_end"], "isoformat") else quarterly_data["period_end"],
                "performance_trend": performance_trend,
                "risk_level": risk_level,
                "risk_trend": risk_trend,
                "organizational_impact": organizational_impact,
                "achievement_theme_count": len(achievement_themes),
                "quarterly_summary": quarterly_summary
            }
            
            # Update task as completed with result
            with db.create_session() as session:
                task = session.query(BackgroundTask).filter(
                    BackgroundTask.task_id == uuid.UUID(task_id)
                ).first()
                
                if task:
                    task.status = TaskStatus.COMPLETED.value
                    task.completed_at = datetime.now()
                    task.result_data = result_data
                    session.commit()
                    
                    logger.info(f"Quarterly analysis task {task_id} completed successfully")
                    return result_data
                else:
                    logger.error(f"Task {task_id} not found when updating status")
                    return {"error": "Task not found when updating status"}
                
        except Exception as e:
            logger.error(f"Error processing quarterly analysis result: {str(e)}")
            _mark_task_failed(db, task_id, f"Error processing analysis result: {str(e)}")
            
            return {"error": f"Error processing analysis result: {str(e)}"}
            
    except SoftTimeLimitExceeded:
        logger.error(f"Analysis task {task_id} exceeded its time limit")
        _mark_task_failed_after_error(db, task_id, "Analysis exceeded the time limit")
        raise
    except Exception as e:
        logger.error(f"Error in quarterly analysis task {task_id}: {str(e)}")
        
        # Update task as failed
        _mark_task_failed_after_error(db, task_id, str(e))
        
        # Re-raise the exception for Celery to handle
        raise
