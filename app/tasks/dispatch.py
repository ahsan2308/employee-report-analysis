"""Queueing Celery work: the one place services reach the task queue, so they never import tasks."""
from typing import Any, Dict, Optional

from app.models.sync_models import SyncType
from app.tasks.analysis_tasks import analyze_monthly_reports_task, analyze_quarterly_reports_task, analyze_report_task
from app.tasks.import_tasks import process_csv_import
from app.tasks.sync_tasks import (
    full_sync_task,
    sync_employee_reports_task,
    sync_job_descriptions_task,
    sync_supervisor_feedback_task,
    sync_vision_data_task,
)
from app.worker.celery_app import celery_app

SYNC_TASK_NAMES = {
    SyncType.EMPLOYEE_REPORTS: sync_employee_reports_task.name,
    SyncType.VISION_DATA: sync_vision_data_task.name,
    SyncType.JOB_DESCRIPTIONS: sync_job_descriptions_task.name,
    SyncType.SUPERVISOR_FEEDBACK: sync_supervisor_feedback_task.name,
}


def queue_report_analysis(task_id: str) -> None:
    analyze_report_task.delay(task_id)


def queue_monthly_analysis(task_id: str) -> None:
    analyze_monthly_reports_task.delay(task_id)


def queue_quarterly_analysis(task_id: str) -> None:
    analyze_quarterly_reports_task.delay(task_id)


def queue_csv_import(job_id: str, file_content: bytes, filename: str, options: Dict[str, Any],
                     csv_type: Optional[str]) -> None:
    process_csv_import.delay(
        job_id=job_id,
        file_content=file_content,
        filename=filename,
        options=options,
        csv_type=csv_type
    )


def queue_sync(sync_type: SyncType, is_full_sync: bool, sync_id: str):
    """Queue one sync type; returns the Celery result (its id is the task id)."""
    return celery_app.send_task(
        SYNC_TASK_NAMES[sync_type],
        kwargs={'is_full_sync': is_full_sync, 'sync_id': sync_id}
    )


def queue_full_sync(employee_sync_id: str, vision_sync_id: str, jd_sync_id: str, sf_sync_id: str):
    """Queue the full sync of all four types; returns the Celery result."""
    return celery_app.send_task(
        full_sync_task.name,
        kwargs={
            'employee_sync_id': employee_sync_id,
            'vision_sync_id': vision_sync_id,
            'jd_sync_id': jd_sync_id,
            'sf_sync_id': sf_sync_id
        }
    )
