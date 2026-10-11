"""Sync job records (SyncHistory), in the caller's session."""
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.sync_models import SyncHistory, SyncStatus, SyncType

ACTIVE_STATUSES = (SyncStatus.PENDING.value, SyncStatus.RUNNING.value)
SORTABLE_FIELDS = sorted(SyncHistory.__mapper__.columns.keys())


def get_sync(session: Session, sync_id) -> Optional[SyncHistory]:
    return session.query(SyncHistory).filter(SyncHistory.sync_id == sync_id).first()


def add_sync(session: Session, sync_job: SyncHistory) -> SyncHistory:
    session.add(sync_job)
    session.commit()
    session.refresh(sync_job)
    return sync_job


def find_active_syncs(session: Session, sync_types: Iterable[str]) -> List[SyncHistory]:
    """PENDING or RUNNING syncs of the given types."""
    return session.query(SyncHistory).filter(
        SyncHistory.sync_type.in_(list(sync_types)),
        SyncHistory.status.in_(ACTIVE_STATUSES)
    ).all()


def find_stale_syncs(session: Session, sync_type: str, started_before: datetime) -> List[SyncHistory]:
    """PENDING or RUNNING syncs of a type that started before the cutoff."""
    return session.query(SyncHistory).filter(
        SyncHistory.sync_type == sync_type,
        SyncHistory.status.in_(ACTIVE_STATUSES),
        SyncHistory.started_at < started_before
    ).all()


def last_successful_sync(session: Session, sync_type: SyncType) -> Optional[SyncHistory]:
    """
    The most recent successful sync of a type: the row incremental syncs start from.
    
    Partial syncs count: they still synced some records, so their timestamp is used.
    """
    return session.query(SyncHistory).filter(
        SyncHistory.sync_type == sync_type.value,
        SyncHistory.status.in_([SyncStatus.COMPLETED.value, SyncStatus.PARTIAL.value]),
        SyncHistory.last_sync_timestamp.isnot(None)
    ).order_by(
        SyncHistory.last_sync_timestamp.desc()
    ).first()


def mark_failed(sync_job: SyncHistory, error_message: str) -> None:
    """Set a sync FAILED with its message (the caller commits)."""
    sync_job.status = SyncStatus.FAILED.value
    sync_job.error_message = error_message
    sync_job.completed_at = datetime.now()


def list_sync_history(session: Session,
                      sync_type: Optional[str] = None,
                      status: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      is_full_sync: Optional[bool] = None,
                      sort_by: str = "started_at",
                      descending: bool = True,
                      offset: int = 0,
                      limit: int = 20) -> Tuple[List[SyncHistory], int]:
    """A page of sync history matching the filters, and the total number of matches."""
    query = session.query(SyncHistory)
    if sync_type:
        query = query.filter(SyncHistory.sync_type == sync_type)
    if status:
        query = query.filter(SyncHistory.status == status)
    if start_date:
        query = query.filter(SyncHistory.started_at >= start_date)
    if end_date:
        query = query.filter(SyncHistory.started_at <= end_date)
    if is_full_sync is not None:
        # A missing flag counts as incremental, as in the response
        query = query.filter(
            func.coalesce(SyncHistory.sync_options['is_full_sync'].as_boolean(), False) == is_full_sync
        )
    total = query.count()
    column = getattr(SyncHistory, sort_by)
    items = query.order_by(column.desc() if descending else column.asc()).offset(offset).limit(limit).all()
    return items, total
