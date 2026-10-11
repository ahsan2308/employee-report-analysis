"""
Service for managing background tasks.
Handles task creation, status tracking, and result retrieval.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task_models import BackgroundTask, TaskStatus, TaskType
from app.models.db_models import Employee, EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis
from app.tasks.analysis_tasks import analyze_report_task
from app.core import settings
from app.core.logger import logger
from app.repositories import tasks as task_repo
from app.repositories.analyses import find_monthly_analysis, find_quarterly_analysis, get_weekly_analysis
from app.repositories.employees import get_employee
from app.repositories.reports import get_report

def _now() -> datetime:
    return datetime.now()


def _stale_after() -> timedelta:
    """How long a task may stay PENDING/RUNNING before it is presumed dead.

    Twice the Celery hard time limit (at least an hour): a task still active
    after that was killed or lost, and no worker will ever finish it.
    """
    time_limit = settings.CELERY_TASK_TIME_LIMIT or 0
    return timedelta(seconds=max(2 * time_limit, 3600))


def _reuse_unless_stale(db: Session, active_task: Optional[BackgroundTask], description: str) -> Optional[BackgroundTask]:
    """Return the in-flight task so callers reuse it, or mark it FAILED and return None if it is stale."""
    if active_task is None:
        return None
    last_activity = active_task.started_at or active_task.created_at
    if last_activity is None or _now() - last_activity < _stale_after():
        return active_task
    logger.warning(f"Task {active_task.task_id} for {description} has been {active_task.status} since {last_activity}. Marking as failed.")
    task_repo.mark_failed(db, active_task, "Task did not finish; the worker running it was stopped or lost", at=_now())
    return None


def find_active_task_for_report(db: Session, report_id: UUID) -> Optional[BackgroundTask]:
    """
    Find any active (PENDING or RUNNING) task for a report.
    Used to prevent duplicate concurrent tasks for the same report.
    
    A task that has been active for longer than any run can take is marked
    FAILED and not returned, so a new one can be created.
    """
    active_task = task_repo.find_active_report_task(db, report_id)

    return _reuse_unless_stale(db, active_task, f"report {report_id}")

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
    active_task = task_repo.find_active_period_task(db, TaskType.MONTHLY_ANALYSIS, employee_id, year, month=month)

    return _reuse_unless_stale(db, active_task, f"monthly analysis ({employee_id}, {year}-{month})")

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
    active_task = task_repo.find_active_period_task(db, TaskType.QUARTERLY_ANALYSIS, employee_id, year, quarter=quarter)

    return _reuse_unless_stale(db, active_task, f"quarterly analysis ({employee_id}, {year}-Q{quarter})")

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
    task_repo.save_task(db, task)
    
    # Submit to Celery if it's a new task
    if not existing_analysis:
        analyze_report_task.delay(str(task.task_id))
        
    return task

def create_task_for_monthly_analysis(
    db: Session,
    employee_id: int,
    year: int,
    month: int,
    existing_analysis: Optional[MonthlyAnalysis] = None
) -> BackgroundTask:
    """
    Create a background task for monthly analysis.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        month: Month for the analysis
        existing_analysis: Optional existing analysis (find_monthly_analysis) to reference instead of running
        
    Returns:
        The created BackgroundTask instance
    """
    # First check if there's already an active task
    active_task = find_active_task_for_monthly_analysis(db, employee_id, year, month)
    if active_task:
        logger.info(f"Found existing active task {active_task.task_id} for monthly analysis ({employee_id}, {year}-{month})")
        return active_task
    
    # Check if the employee exists
    employee = get_employee(db, employee_id)
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
                "analysis_id": existing_analysis.analysis_id,
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
    task_repo.save_task(db, task)
    
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
    existing_analysis: Optional[QuarterlyAnalysis] = None
) -> BackgroundTask:
    """
    Create a background task for quarterly analysis.
    
    Args:
        db: Database session
        employee_id: Employee ID
        year: Year for the analysis
        quarter: Quarter for the analysis (1-4)
        existing_analysis: Optional existing analysis (find_quarterly_analysis) to reference instead of running
        
    Returns:
        The created BackgroundTask instance
    """
    # First check if there's already an active task
    active_task = find_active_task_for_quarterly_analysis(db, employee_id, year, quarter)
    if active_task:
        logger.info(f"Found existing active task {active_task.task_id} for quarterly analysis ({employee_id}, {year}-Q{quarter})")
        return active_task
    
    # Check if the employee exists
    employee = get_employee(db, employee_id)
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
                "analysis_id": existing_analysis.analysis_id,
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
    task_repo.save_task(db, task)
    
    # Submit to Celery if it's a new task
    if not existing_analysis:
        # Import will be at the top of this file
        from app.tasks.analysis_tasks import analyze_quarterly_reports_task
        analyze_quarterly_reports_task.delay(str(task.task_id))
        
    return task

class TaskNotFoundError(ValueError):
    """No task has the requested ID (a ValueError, as this used to be)."""


def get_task_status(db: Session, task_id: UUID) -> Optional[BackgroundTask]:
    """Get a task by ID."""
    return task_repo.get_task(db, task_id)

@dataclass
class TaskResult:
    """A finished task: the analysis row it produced, or else its stored result data."""
    status: str
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    analysis_kind: Optional[str] = None  # "weekly", "monthly" or "quarterly" when analysis is set
    analysis: Any = None
    employee: Optional[Employee] = None


def get_task_result(db: Session, task_id: UUID) -> TaskResult:
    """
    Get task result, including error message if task failed.
    
    For tasks with existing analyses, this looks up the analysis row so the API
    can return it in the same shape as the /analyses endpoints.
    
    Raises:
        TaskNotFoundError: If the task doesn't exist
        ValueError: If the task is not in a terminal state
    """
    task = get_task_status(db, task_id)
    
    if not task:
        raise TaskNotFoundError(f"Task with ID {task_id} not found")
        
    if task.status not in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
        raise ValueError(f"Task is not complete: {task.status}")
    
    if task.status == TaskStatus.FAILED.value:
        return TaskResult(status=task.status, error_message=task.error_message)
    
    result_data = task.result_data
    if not result_data or "analysis_id" not in result_data:
        return TaskResult(status=task.status, result_data=result_data)
    
    if task.task_type == TaskType.REPORT_ANALYSIS.value:
        # Only a bare reference ({"analysis_id": ...}) is expanded; a full stored payload is returned as is
        if len(result_data) <= 2:
            analysis = get_weekly_analysis(db, result_data["analysis_id"])
            report = analysis and get_report(db, analysis.report_id)
            if report:
                employee = get_employee(db, report.employee_id)
                return TaskResult(status=task.status, result_data=result_data,
                                  analysis_kind="weekly", analysis=analysis, employee=employee)
    elif task.task_type in (TaskType.MONTHLY_ANALYSIS.value, TaskType.QUARTERLY_ANALYSIS.value):
        # Looked up by period: the stored analysis_id may be stale after a re-run
        if task.task_type == TaskType.MONTHLY_ANALYSIS.value:
            kind, analysis = "monthly", find_monthly_analysis(db, task.employee_id, task.year, task.month)
        else:
            kind, analysis = "quarterly", find_quarterly_analysis(db, task.employee_id, task.year, task.quarter)
        if analysis:
            employee = get_employee(db, task.employee_id)
            return TaskResult(status=task.status, result_data=result_data,
                              analysis_kind=kind, analysis=analysis, employee=employee)
    
    return TaskResult(status=task.status, result_data=result_data)
