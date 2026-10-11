"""Background task records (BackgroundTask), in the caller's session."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task_models import BackgroundTask, TaskStatus, TaskType

ACTIVE_STATUSES = (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)


def get_task(session: Session, task_id: UUID) -> Optional[BackgroundTask]:
    return session.query(BackgroundTask).filter(BackgroundTask.task_id == task_id).first()


def find_active_report_task(session: Session, report_id: UUID) -> Optional[BackgroundTask]:
    """A PENDING or RUNNING task for the report, if any."""
    return session.query(BackgroundTask).filter(
        BackgroundTask.report_id == report_id,
        BackgroundTask.status.in_(ACTIVE_STATUSES)
    ).first()


def find_active_period_task(session: Session, task_type: TaskType, employee_id: int, year: int,
                            month: Optional[int] = None, quarter: Optional[int] = None) -> Optional[BackgroundTask]:
    """A PENDING or RUNNING monthly (month=) or quarterly (quarter=) task for the employee's period."""
    period = BackgroundTask.month == month if quarter is None else BackgroundTask.quarter == quarter
    return session.query(BackgroundTask).filter(
        BackgroundTask.employee_id == employee_id,
        BackgroundTask.year == year,
        period,
        BackgroundTask.task_type == task_type.value,
        BackgroundTask.status.in_(ACTIVE_STATUSES)
    ).first()


def save_task(session: Session, task: BackgroundTask) -> BackgroundTask:
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def mark_running(session: Session, task: BackgroundTask, celery_task_id: str) -> None:
    task.celery_task_id = celery_task_id
    task.status = TaskStatus.RUNNING.value
    task.started_at = datetime.now()
    session.commit()


def mark_completed(session: Session, task: BackgroundTask, result_data: Dict[str, Any]) -> None:
    task.status = TaskStatus.COMPLETED.value
    task.completed_at = datetime.now()
    task.result_data = result_data
    session.commit()


def mark_failed(session: Session, task: BackgroundTask, message: str, at: Optional[datetime] = None) -> None:
    task.status = TaskStatus.FAILED.value
    task.error_message = message
    task.completed_at = at or datetime.now()
    session.commit()
