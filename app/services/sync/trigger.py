"""Starting syncs on request: record the sync jobs, then queue the Celery task that runs them."""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.sync_models import SyncHistory, SyncType
from app.repositories import sync_history
from app.services.sync.sync_tracker import SyncTracker, clear_stale_syncs
from app.tasks import dispatch

SYNC_TYPES = [SyncType.EMPLOYEE_REPORTS, SyncType.VISION_DATA, SyncType.JOB_DESCRIPTIONS, SyncType.SUPERVISOR_FEEDBACK]


class SyncAlreadyRunning(Exception):
    """A sync of the requested type is already PENDING or RUNNING."""


def _fail_undispatched(db: Session, sync_ids: List, dispatch_error: Exception) -> None:
    """Mark sync rows FAILED when their Celery task could not be queued.

    Without this a PENDING row would block new triggers until it goes stale.
    """
    tracker = SyncTracker(None)
    for sync_id in sync_ids:
        tracker.mark_sync_failed(sync_id, f"Could not queue the sync task: {dispatch_error}", session=db)
    db.commit()


def trigger_sync(db: Session, sync_type: SyncType, is_full_sync: bool, label: str):
    """Start one sync type. Returns (sync job, Celery result).

    Raises SyncAlreadyRunning when that type is already in progress.
    """
    # Clear stale syncs before checking for running syncs
    clear_stale_syncs(db, sync_type.value)
    running_sync = next(iter(sync_history.find_active_syncs(db, [sync_type.value])), None)
    if running_sync:
        raise SyncAlreadyRunning(f"{label.capitalize()} sync already in progress (sync_id: {running_sync.sync_id})")

    # The job is recorded before its task is queued, so the task finds it
    sync_job = SyncTracker(None).create_sync_job(sync_type=sync_type, session=db, is_full_sync=is_full_sync)
    try:
        task = dispatch.queue_sync(sync_type, is_full_sync, str(sync_job.sync_id))
    except Exception as dispatch_error:
        _fail_undispatched(db, [sync_job.sync_id], dispatch_error)
        raise
    return sync_job, task


def trigger_full_sync(db: Session):
    """Start a full sync of all four types in one task. Returns ({sync type: sync job}, Celery result).

    Raises SyncAlreadyRunning when any of them is already in progress.
    """
    for sync_type in SYNC_TYPES:
        clear_stale_syncs(db, sync_type.value)
    running_syncs = sync_history.find_active_syncs(db, [sync_type.value for sync_type in SYNC_TYPES])
    if running_syncs:
        raise SyncAlreadyRunning(f"Sync already in progress for: {', '.join(s.sync_type for s in running_syncs)}")

    tracker = SyncTracker(None)
    jobs: Dict[SyncType, SyncHistory] = {
        sync_type: tracker.create_sync_job(sync_type=sync_type, session=db, is_full_sync=True)
        for sync_type in SYNC_TYPES
    }
    try:
        task = dispatch.queue_full_sync(
            employee_sync_id=str(jobs[SyncType.EMPLOYEE_REPORTS].sync_id),
            vision_sync_id=str(jobs[SyncType.VISION_DATA].sync_id),
            jd_sync_id=str(jobs[SyncType.JOB_DESCRIPTIONS].sync_id),
            sf_sync_id=str(jobs[SyncType.SUPERVISOR_FEEDBACK].sync_id)
        )
    except Exception as dispatch_error:
        _fail_undispatched(db, [job.sync_id for job in jobs.values()], dispatch_error)
        raise
    logger.info(f"Queued full sync task {task.id}")
    return jobs, task
