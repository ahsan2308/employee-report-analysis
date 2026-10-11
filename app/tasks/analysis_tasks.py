"""
Celery tasks for asynchronous report analysis.
"""
import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.worker.celery_app import celery_app
from app.db.database import get_database
from app.models.task_models import TaskType
from app.repositories.analyses import get_monthly_analysis_by_params
from app.repositories.analyses import get_quarterly_analysis_by_params
from app.core.logger import logger

from app.repositories import tasks as task_repo
from app.repositories.employees import get_employee
from app.repositories.reports import get_report

from app.services.analysis import runner as analysis_runner
from app.services.analysis.runner import AnalysisFailed


def _mark_task_failed(db, task_id: str, message: str) -> None:
    """Mark the BackgroundTask as FAILED with message, if the row exists."""
    with db.create_session() as session:
        task = task_repo.get_task(session, uuid.UUID(task_id))

        if task:
            task_repo.mark_failed(session, task, message)


def _mark_task_failed_after_error(db, task_id: str, message: str) -> None:
    """Same, for the outer exception handlers: a failure to update is logged, not raised."""
    with db.create_session() as session:
        try:
            task = task_repo.get_task(session, uuid.UUID(task_id))

            if task:
                task_repo.mark_failed(session, task, message)
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
            task = task_repo.get_task(session, uuid.UUID(task_id))
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Update celery_task_id and status
            task_repo.mark_running(session, task, celery_task_id)
            
            report_id = task.report_id
        
        # Get report data outside transaction to avoid holding connection
        with db.create_session() as session:
            report = get_report(session, report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")
            
            employee = get_employee(session, report.employee_id)
            if not employee:
                raise ValueError(f"Employee {report.employee_id} not found")
        
        try:
            result_data = analysis_runner.analyze_report(db, task_id, report, employee)
        except AnalysisFailed as failure:
            _mark_task_failed(db, task_id, str(failure))
            return {"error": str(failure)}
        
        # Update task as completed with result
        with db.create_session() as session:
            task = task_repo.get_task(session, uuid.UUID(task_id))
            task_repo.mark_completed(session, task, result_data)
        
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
            task = task_repo.get_task(session, uuid.UUID(task_id))
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Verify this is a monthly analysis task
            if task.task_type != TaskType.MONTHLY_ANALYSIS.value:
                logger.error(f"Task {task_id} is not a monthly analysis task")
                # Record the outcome, or the row would stay PENDING forever
                task_repo.mark_failed(session, task, f"Incorrect task type {task.task_type} for a monthly analysis")
                return {"error": "Incorrect task type"}
            
            # Update celery_task_id and status
            task_repo.mark_running(session, task, celery_task_id)
            
            # Extract parameters
            employee_id = task.employee_id
            year = task.year
            month = task.month
            
            if not all([employee_id, year, month]):
                raise ValueError(f"Missing required parameters: employee_id={employee_id}, year={year}, month={month}")
        
        # Get employee data outside transaction to avoid holding connection
        with db.create_session() as session:
            employee = get_employee(session, employee_id)
            if not employee:
                raise ValueError(f"Employee {employee_id} not found")
        
        # Check if analysis already exists
        existing_analysis = get_monthly_analysis_by_params(employee_id, year, month)
        if existing_analysis:
            logger.info(f"Monthly analysis for employee {employee_id}, {year}-{month} already exists")
            
            # Update task as completed with reference to existing analysis
            with db.create_session() as session:
                task = task_repo.get_task(session, uuid.UUID(task_id))
                
                if task:
                    task_repo.mark_completed(session, task, {
                        "analysis_id": existing_analysis["analysis_id"],
                        "employee_id": employee_id,
                        "year": year,
                        "month": month,
                        "message": "Analysis already exists"
                    })
                    
            return {
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "month": month,
                "message": "Analysis already exists"
            }
        
        try:
            result_data = analysis_runner.analyze_month(db, task_id, employee, employee_id, year, month)
        except AnalysisFailed as failure:
            _mark_task_failed(db, task_id, str(failure))
            return {"error": str(failure)}
        
        # Update task as completed with result
        with db.create_session() as session:
            task = task_repo.get_task(session, uuid.UUID(task_id))

            if task:
                task_repo.mark_completed(session, task, result_data)

                logger.info(f"Monthly analysis task {task_id} completed successfully")
                return result_data
            else:
                logger.error(f"Task {task_id} not found when updating status")
                return {"error": "Task not found when updating status"}
            
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
            task = task_repo.get_task(session, uuid.UUID(task_id))
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}
            
            # Verify this is a quarterly analysis task
            if task.task_type != TaskType.QUARTERLY_ANALYSIS.value:
                logger.error(f"Task {task_id} is not a quarterly analysis task")
                # Record the outcome, or the row would stay PENDING forever
                task_repo.mark_failed(session, task, f"Incorrect task type {task.task_type} for a quarterly analysis")
                return {"error": "Incorrect task type"}
            
            # Update celery_task_id and status
            task_repo.mark_running(session, task, celery_task_id)
            
            # Extract parameters
            employee_id = task.employee_id
            year = task.year
            quarter = task.quarter
            
            if not all([employee_id, year, quarter]):
                raise ValueError(f"Missing required parameters: employee_id={employee_id}, year={year}, quarter={quarter}")
        
        # Get employee data outside transaction to avoid holding connection
        with db.create_session() as session:
            employee = get_employee(session, employee_id)
            if not employee:
                raise ValueError(f"Employee {employee_id} not found")
        

        existing_analysis = get_quarterly_analysis_by_params(employee_id, year, quarter)
        if existing_analysis:
            logger.info(f"Quarterly analysis for employee {employee_id}, {year}-Q{quarter} already exists")
            
            # Update task as completed with reference to existing analysis
            with db.create_session() as session:
                task = task_repo.get_task(session, uuid.UUID(task_id))
                
                if task:
                    task_repo.mark_completed(session, task, {
                        "analysis_id": existing_analysis["analysis_id"],
                        "employee_id": employee_id,
                        "year": year,
                        "quarter": quarter,
                        "message": "Analysis already exists"
                    })
                    
            return {
                "analysis_id": existing_analysis["analysis_id"],
                "employee_id": employee_id,
                "year": year,
                "quarter": quarter,
                "message": "Analysis already exists"
            }
        
        try:
            result_data = analysis_runner.analyze_quarter(db, task_id, employee, employee_id, year, quarter)
        except AnalysisFailed as failure:
            _mark_task_failed(db, task_id, str(failure))
            return {"error": str(failure)}
        
        # Update task as completed with result
        with db.create_session() as session:
            task = task_repo.get_task(session, uuid.UUID(task_id))

            if task:
                task_repo.mark_completed(session, task, result_data)

                logger.info(f"Quarterly analysis task {task_id} completed successfully")
                return result_data
            else:
                logger.error(f"Task {task_id} not found when updating status")
                return {"error": "Task not found when updating status"}
            
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
