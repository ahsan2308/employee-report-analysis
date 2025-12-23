"""
Service for managing background tasks.
Handles task creation, status tracking, and result retrieval.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task_models import BackgroundTask, TaskStatus, TaskType
from app.models.db_models import Employee, Report, EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis
from app.tasks.analysis_tasks import analyze_report_task
from app.core.logger import logger
from app.services.db_service import get_monthly_analysis_by_params, get_quarterly_analysis_by_params

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

def find_active_task_for_monthly_analysis(db: Session, employee_id: int, year: int, month: int) -> Optional[BackgroundTask]:
    """
    Find any active (PENDING or RUNNING) task for a monthly analysis.
    Used to prevent duplicate concurrent tasks for the same month/employee.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        month: Month for the analysis
        
    Returns:
        Active task if found, None otherwise
    """
    active_task = db.query(BackgroundTask).filter(
        BackgroundTask.employee_id == employee_id,
        BackgroundTask.year == year,
        BackgroundTask.month == month,
        BackgroundTask.task_type == TaskType.MONTHLY_ANALYSIS.value,
        BackgroundTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
    ).first()
    
    if active_task:
        # Check if any monthly analysis exists for these parameters
        analysis_exists = db.query(MonthlyAnalysis).filter(
            MonthlyAnalysis.employee_id == employee_id,
            MonthlyAnalysis.year == year,
            MonthlyAnalysis.month == month
        ).first() is not None
        
        if not analysis_exists:
            # If no analysis was created despite having an active task, consider it failed
            logger.warning(f"Found task {active_task.task_id} for monthly analysis ({employee_id}, {year}-{month}) with no analysis. Marking as failed.")
            active_task.status = TaskStatus.FAILED.value
            active_task.error_message = "Task failed to produce monthly analysis"
            active_task.completed_at = datetime.now()
            db.commit()
            return None  # Return None so a new task will be created
    
    return active_task

def find_active_task_for_quarterly_analysis(db: Session, employee_id: int, year: int, quarter: int) -> Optional[BackgroundTask]:
    """
    Find any active (PENDING or RUNNING) task for a quarterly analysis.
    Used to prevent duplicate concurrent tasks for the same quarter/employee.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        quarter: Quarter for the analysis (1-4)
        
    Returns:
        Active task if found, None otherwise
    """
    active_task = db.query(BackgroundTask).filter(
        BackgroundTask.employee_id == employee_id,
        BackgroundTask.year == year,
        BackgroundTask.quarter == quarter,
        BackgroundTask.task_type == TaskType.QUARTERLY_ANALYSIS.value,
        BackgroundTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
    ).first()
    
    if active_task:
        # Check if any quarterly analysis exists for these parameters
        analysis_exists = db.query(QuarterlyAnalysis).filter(
            QuarterlyAnalysis.employee_id == employee_id,
            QuarterlyAnalysis.year == year,
            QuarterlyAnalysis.quarter == quarter
        ).first() is not None
        
        if not analysis_exists:
            # If no analysis was created despite having an active task, consider it failed
            logger.warning(f"Found task {active_task.task_id} for quarterly analysis ({employee_id}, {year}-Q{quarter}) with no analysis. Marking as failed.")
            active_task.status = TaskStatus.FAILED.value
            active_task.error_message = "Task failed to produce quarterly analysis"
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
            task_type=TaskType.REPORT_ANALYSIS.value,
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
            task_type=TaskType.REPORT_ANALYSIS.value,
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

def create_task_for_monthly_analysis(
    db: Session,
    employee_id: int,
    year: int,
    month: int,
    existing_analysis: Optional[Dict[str, Any]] = None
) -> BackgroundTask:
    """
    Create a background task for monthly analysis.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        month: Month for the analysis
        existing_analysis: Optional existing analysis data from get_monthly_analysis_by_params
        
    Returns:
        The created BackgroundTask instance
    """
    # First check if there's already an active task
    active_task = find_active_task_for_monthly_analysis(db, employee_id, year, month)
    if active_task:
        logger.info(f"Found existing active task {active_task.task_id} for monthly analysis ({employee_id}, {year}-{month})")
        return active_task
    
    # Check if the employee exists
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        logger.error(f"Employee with ID {employee_id} not found")
        raise ValueError(f"Employee with ID {employee_id} not found")
    
    if existing_analysis:
        # Store reference for existing analysis to avoid reprocessing
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="immediate",
            task_type=TaskType.MONTHLY_ANALYSIS.value,
            employee_id=employee_id,
            year=year,
            month=month,
            status=TaskStatus.COMPLETED.value,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result_data={
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "month": month
            }
        )
    else:
        # Create a new pending task
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="pending",
            task_type=TaskType.MONTHLY_ANALYSIS.value,
            employee_id=employee_id,
            year=year,
            month=month,
            status=TaskStatus.PENDING.value
        )
    
    # Save to database
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Submit to Celery if it's a new task - will add analyze_monthly_reports_task
    if not existing_analysis:
        # Will add this task when we create analysis_tasks.py
        from app.tasks.analysis_tasks import analyze_monthly_reports_task
        analyze_monthly_reports_task.delay(str(task.task_id))
        
    return task

def create_task_for_quarterly_analysis(
    db: Session,
    employee_id: int,
    year: int,
    quarter: int,
    existing_analysis: Optional[Dict[str, Any]] = None
) -> BackgroundTask:
    """
    Create a background task for quarterly analysis.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        quarter: Quarter for the analysis (1-4)
        existing_analysis: Optional existing analysis data from get_quarterly_analysis_by_params
        
    Returns:
        The created BackgroundTask instance
    """
    # First check if there's already an active task
    active_task = find_active_task_for_quarterly_analysis(db, employee_id, year, quarter)
    if active_task:
        logger.info(f"Found existing active task {active_task.task_id} for quarterly analysis ({employee_id}, {year}-Q{quarter})")
        return active_task
    
    # Check if the employee exists
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        logger.error(f"Employee with ID {employee_id} not found")
        raise ValueError(f"Employee with ID {employee_id} not found")
    
    if existing_analysis:
        # Store reference for existing analysis to avoid reprocessing
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="immediate",
            task_type=TaskType.QUARTERLY_ANALYSIS.value,
            employee_id=employee_id,
            year=year,
            quarter=quarter,
            status=TaskStatus.COMPLETED.value,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result_data={
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "quarter": quarter
            }
        )
    else:
        # Create a new pending task
        task = BackgroundTask(
            task_id=uuid.uuid4(),
            celery_task_id="pending",
            task_type=TaskType.QUARTERLY_ANALYSIS.value,
            employee_id=employee_id,
            year=year,
            quarter=quarter,
            status=TaskStatus.PENDING.value
        )
    
    # Save to database
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Submit to Celery if it's a new task
    if not existing_analysis:
        # Import will be at the top of this file
        from app.tasks.analysis_tasks import analyze_quarterly_reports_task
        analyze_quarterly_reports_task.delay(str(task.task_id))
        
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
    
    # Get the task result data
    result_data = task.result_data
    
    # Check task type and handle appropriately
    if task.task_type == TaskType.REPORT_ANALYSIS.value:
        # Weekly report analysis task
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
                        },
                        "performance_assessment": {
                            "rating": analysis.performance_rating or "medium",
                            "summary": analysis.performance_summary or "No performance assessment was performed for this analysis.",
                            "key_strengths": analysis.performance_strengths or [],
                            "improvement_areas": analysis.performance_improvement_areas or []
                        }
                    }
    elif task.task_type == TaskType.MONTHLY_ANALYSIS.value:
        # Monthly analysis task - always fetch from database for complete data
        if result_data and "analysis_id" in result_data:
            # Always fetch complete data from database, don't use cached result_data
            employee_id = task.employee_id
            year = task.year
            month = task.month
            
            # Use db_service function to get full analysis data
            monthly_analysis = get_monthly_analysis_by_params(employee_id, year, month)
            
            if monthly_analysis:
                # Get employee info for the result
                employee = db.query(Employee).filter(
                    Employee.id == employee_id
                ).first()
                
                # Format the result data with updated field structure
                result_data = {
                    "analysis_id": monthly_analysis["analysis_id"],
                    "employee_id": employee_id,
                    "employee_name": employee.name if employee else None,
                    "year": year,
                    "month": month,
                    "period_start": monthly_analysis["period_start"],
                    "period_end": monthly_analysis["period_end"],
                    
                    # Progress trends (aligned with new structure)
                    "progress_trends": {
                        "performance_trend": monthly_analysis["performance_trend"],
                        "sentiment_trend": monthly_analysis["sentiment_trend"],
                        "risk_level_pattern": monthly_analysis["risk_level_pattern"],
                        "challenge_resolution_progress": monthly_analysis["challenge_resolution_progress"]
                    },
                    
                    # Monthly achievements
                    "monthly_achievements": monthly_analysis["monthly_achievements"],
                    
                    # Recurring challenges with status field
                    "recurring_challenges": monthly_analysis["recurring_challenges"],
                    
                    # Consistency assessment (detailed fields)
                    "consistency_assessment": {
                        "task_completion_reliability": monthly_analysis["task_completion_reliability"],
                        "work_quality_consistency": monthly_analysis["work_quality_consistency"],
                        "performance_stability": monthly_analysis["performance_stability"],
                        "notable_strengths": monthly_analysis["consistency_notable_strengths"],
                        "notable_weaknesses": monthly_analysis["consistency_notable_weaknesses"]
                    },
                    
                    # Growth indicators (detailed fields)
                    "growth_indicators": {
                        "complexity_of_tasks": monthly_analysis["complexity_of_tasks"],
                        "skill_development_evidence": monthly_analysis["skill_development_evidence"],
                        "confidence_level_change": monthly_analysis["confidence_level_change"],
                        "approach_to_challenges": monthly_analysis["approach_to_challenges"]
                    },
                    
                    # Focus areas
                    "focus_areas": monthly_analysis["focus_areas"],
                    
                    # Risk assessment (nested structure)
                    "monthly_risk_assessment": {
                        "overall_risk_level": monthly_analysis["risk_level"],
                        "risk_explanation": monthly_analysis["risk_explanation"],
                        "significant_risks": monthly_analysis.get("significant_risks", []),
                        "escalating_risks": monthly_analysis.get("escalating_risks", []),
                        "risk_mitigation_recommendations": monthly_analysis.get("risk_mitigation_recommendations", [])
                    },
                    
                    # Strategic recommendations
                    "strategic_recommendations": monthly_analysis["strategic_recommendations"],
                    
                    # Monthly summary
                    "monthly_summary": monthly_analysis["monthly_summary"],
                    
                    # Full analysis for reference
                    "full_analysis_json": monthly_analysis["full_analysis_json"]
                }
    elif task.task_type == TaskType.QUARTERLY_ANALYSIS.value:
        # Quarterly analysis task - always fetch from database for complete data
        if result_data and "analysis_id" in result_data:
            # Always fetch complete data from database, don't use cached result_data
            employee_id = task.employee_id
            year = task.year
            quarter = task.quarter
            
            # Use db_service function to get full analysis data
            quarterly_analysis = get_quarterly_analysis_by_params(employee_id, year, quarter)
            
            if quarterly_analysis:
                # Get employee info for the result
                employee = db.query(Employee).filter(
                    Employee.id == employee_id
                ).first()
                
                # Format the result data with updated field structure
                result_data = {
                    "analysis_id": quarterly_analysis["analysis_id"],
                    "employee_id": employee_id,
                    "employee_name": employee.name if employee else None,
                    "year": year,
                    "quarter": quarter,
                    "period_start": quarterly_analysis["period_start"],
                    "period_end": quarterly_analysis["period_end"],
                    "monthly_analysis_ids": quarterly_analysis["monthly_analysis_ids"],
                    "analysis_date": quarterly_analysis["analysis_date"],
                    
                    # Strategic alignment
                    "organizational_impact": quarterly_analysis["organizational_impact"],
                    "strategic_alignment": quarterly_analysis["strategic_alignment_json"],
                    
                    # Performance assessment
                    "performance_trend": quarterly_analysis["performance_trend"],
                    "task_completion_reliability": quarterly_analysis["task_completion_reliability"],
                    "work_quality_consistency": quarterly_analysis["work_quality_consistency"],
                    "performance_stability": quarterly_analysis["performance_stability"],
                    "achievement_themes": quarterly_analysis["achievement_themes_json"],
                    "performance_trajectory": quarterly_analysis["performance_trajectory_json"],
                    
                    # Cross-functional and challenge data
                    "collaboration_effectiveness": quarterly_analysis["collaboration_effectiveness"],
                    "stakeholder_count": quarterly_analysis["stakeholder_count"],
                    "challenge_patterns": quarterly_analysis["challenge_patterns_json"],
                    "cross_functional_impact": quarterly_analysis["cross_functional_impact_json"],
                    "adaptation_effectiveness": quarterly_analysis["adaptation_effectiveness"],
                    
                    # Risk assessment
                    "risk_level": quarterly_analysis["risk_level"],
                    "risk_trend": quarterly_analysis["risk_trend"],
                    "risk_assessment": quarterly_analysis["risk_assessment_json"],
                    
                    # Skills and development
                    "learning_agility": quarterly_analysis["learning_agility"],
                    "autonomy_level": quarterly_analysis["autonomy_level"],
                    "development_focus": quarterly_analysis["development_focus"],
                    "skill_development": quarterly_analysis["skill_development_json"],
                    "behavioral_assessment": quarterly_analysis["behavioral_assessment_json"],
                    
                    # Credibility assessment
                    "credibility_rating": quarterly_analysis["credibility_rating"],
                    "vision_data_alignment": quarterly_analysis["vision_data_alignment"],
                    "credibility_assessment": quarterly_analysis["credibility_assessment_json"],
                    
                    # Forward planning
                    "forward_planning": quarterly_analysis["forward_planning_json"],
                    
                    # Summary
                    "quarterly_summary": quarterly_analysis["quarterly_summary"],
                    
                    # Full analysis for reference
                    "full_analysis_json": quarterly_analysis["full_analysis_json"]
                }
    
    return {
        "status": task.status,
        "result": result_data
    }
