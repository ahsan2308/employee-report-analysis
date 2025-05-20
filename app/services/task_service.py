"""
Service for managing background tasks.
Handles task creation, status tracking, and result retrieval.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task_models import BackgroundTask, TaskStatus
from app.models.db_models import Employee, Report, EmployeeAnalysis
from app.tasks.analysis_tasks import analyze_report_task
from app.core.logger import logger

def find_active_task_for_report(db: Session, report_id: UUID) -> Optional[BackgroundTask]:
    """
    Find any active (PENDING or RUNNING) task for a report.
    Used to prevent duplicate concurrent tasks for the same report.
    
    Checks if an analysis exists for the report. If an active task exists
    but no analysis has been created, the task is considered failed.
    """
    active_task = db.query(BackgroundTask).filter(
        BackgroundTask.report_id == report_id,
        BackgroundTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
    ).first()
    
    if active_task:
        # Check if any analysis exists for this report
        analysis_exists = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.report_id == report_id
        ).first() is not None
        
        if not analysis_exists:
            # Task has no analysis, mark it as failed
            logger.warning(f"Found task {active_task.task_id} for report {report_id} with no analysis. Marking as failed.")
            active_task.status = TaskStatus.FAILED.value
            active_task.error_message = "Task failed to produce analysis"
            active_task.completed_at = datetime.now()
            db.commit()
            return None  # Return None so a new task will be created
    
    return active_task

def create_task_for_analysis(
    db: Session, 
    report_uuid: UUID,
    employee: Employee,
    existing_analysis: Optional[EmployeeAnalysis] = None
) -> BackgroundTask:
    """
    Create a background task for report analysis.
    
    Args:
        db: Database session
        report_uuid: UUID of the report to analyze
        employee: Employee model instance
        existing_analysis: Optional existing analysis to skip processing
        
    Returns:
        The created BackgroundTask instance
    """
    # First check if there's already an active task for this report
    active_task = find_active_task_for_report(db, report_uuid)
    if active_task:
        logger.info(f"Found existing active task {active_task.task_id} for report {report_uuid}")
        return active_task
        
    if existing_analysis:
        # Store reference instead of duplicating all data
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="immediate",
            task_type="analyze_report",
            report_id=report_uuid,
            status=TaskStatus.COMPLETED.value,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result_data={
                "analysis_id": existing_analysis.analysis_id,
                "report_id": str(existing_analysis.report_id)
            }
        )
    else:
        # Create a new pending task
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="pending",
            task_type="analyze_report",
            report_id=report_uuid,
            status=TaskStatus.PENDING.value
        )
    
    # Save to database
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Submit to Celery if it's a new task
    if not existing_analysis:
        analyze_report_task.delay(str(task.task_id))
        
    return task

def get_task_status(db: Session, task_id: UUID) -> Optional[BackgroundTask]:
    """Get a task by ID."""
    return db.query(BackgroundTask).filter(BackgroundTask.task_id == task_id).first()

def get_task_result(db: Session, task_id: UUID) -> Dict[str, Any]:
    """
    Get task result, including error message if task failed.
    
    For tasks with existing analyses, this will automatically look up the full analysis data.
    
    Raises:
        ValueError: If the task is not in a terminal state or doesn't exist
    """
    task = get_task_status(db, task_id)
    
    if not task:
        raise ValueError(f"Task with ID {task_id} not found")
        
    if task.status not in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
        raise ValueError(f"Task is not complete: {task.status}")
    
    if task.status == TaskStatus.FAILED.value:
        return {
            "status": task.status,
            "error_message": task.error_message
        }
    
    # Check if this is a reference-only result (existing analysis)
    result_data = task.result_data
    if result_data and "analysis_id" in result_data and len(result_data) <= 2:
        # This looks like a reference, fetch the full analysis
        analysis_id = result_data["analysis_id"]
        analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.analysis_id == analysis_id
        ).first()
        
        if analysis:
            # Get the report to find employee info
            report = db.query(Report).filter(
                Report.report_id == analysis.report_id
            ).first()
            
            if report:
                employee = db.query(Employee).filter(
                    Employee.id == report.employee_id
                ).first()
                
                # Construct full result data
                result_data = {
                    "analysis_id": analysis.analysis_id,
                    "report_id": str(analysis.report_id),
                    "employee_name": employee.name if employee else None,
                    "sentiment": analysis.sentiment_score,
                    "sentiment_score": analysis.sentiment_score,
                    "risk_level": analysis.risk_level,
                    "risk_explanation": analysis.risk_explanation,
                    "full_analysis_json": analysis.full_analysis_json,
                    "achievements_json": analysis.achievements_json,
                    "challenges_json": analysis.challenges_json,
                    "topics": analysis.topics,
                    "action_items": analysis.action_items,
                    "credibility_assessment": {
                        "rating": analysis.credibility_rating or "medium",
                        "explanation": analysis.credibility_explanation or "No credibility assessment was performed for this analysis.",
                        "exaggeration_flags": analysis.exaggeration_flags or [],
                        "consistency_score": analysis.consistency_score or "medium"
                    }
                }
    
    return {
        "status": task.status,
        "result": result_data
    }
