"""
Celery tasks for asynchronous report analysis.
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.worker.celery_app import celery_app
from app.database import get_database
from app.models.task_models import BackgroundTask, TaskStatus
from app.models.db_models import Report, Employee, EmployeeAnalysis
from app.services.vector_store_service import search_reports
from app.services.db_service import get_reports_for_vector_results, get_employee_vision_data
from app.services.llm_service import get_llm_service
from app.services.additional_services import filter_vision_data, format_vision_data_for_prompt
from app.core.logger import logger


@celery_app.task(bind=True)
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
        
        # Perform analysis - using existing analysis code
        # Get similar reports for context
        logger.info(f"Finding similar reports for context (task: {task_id})")
        similar_reports_chunks = search_reports(
            query=report.report_text,
            employee_id=report.employee_id,
            top_k=3,
            group_by_report=True  # Enable grouping by report_id to get one chunk per report
        )
        similar_texts_chunks = [r.get("text", "") for r in similar_reports_chunks]
        
        # Retrieving Full Reports
        similar_texts = get_reports_for_vector_results(similar_texts_chunks)
        
        # Get vision data, filter it, and format it
        raw_vision_data = get_employee_vision_data(report.employee_id, report.report_date, num_previous_weeks=4)
        filtered_vision_data = filter_vision_data(raw_vision_data)
        formatted_vision_data = format_vision_data_for_prompt(filtered_vision_data)

        # Get LLM service and generate analysis
        logger.info(f"Calling LLM service for analysis (task: {task_id})")
        llm_service = get_llm_service()
        analysis_result = llm_service.analyze_report(
            report.report_text, 
            formatted_vision_data, 
            similar_texts, 
            num_ctx=40000
        )
        
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
                consistency_score=consistency_score
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
            
    except Exception as e:
        logger.error(f"Error in analysis task {task_id}: {str(e)}")
        
        # Update task as failed
        with db.create_session() as session:
            try:
                task = session.query(BackgroundTask).filter(
                    BackgroundTask.task_id == uuid.UUID(task_id)
                ).first()
                
                if task:
                    task.status = TaskStatus.FAILED.value
                    task.completed_at = datetime.now()
                    task.error_message = str(e)
                    session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update task status: {str(update_error)}")
        
        # Re-raise the exception for Celery to handle
        raise
