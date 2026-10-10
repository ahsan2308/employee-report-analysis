"""
Sync API Routes

Endpoints for triggering and monitoring SQL Server to PostgreSQL synchronization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import time
import os

from app.api.deps import get_db
from app.models.sync_models import SyncHistory, SyncStatus, SyncType
from app.schemas.sync_schema import (
    SyncTriggerResponse,
    FullSyncTriggerResponse,
    SyncStatusResponse,
    LastSyncResponse,
    SyncHistoryListResponse,
    SyncHistoryItem,
    SyncErrorsResponse,
    SyncErrorItem,
    SyncConfigResponse,
    ConnectionTestResponse,
    SyncProgressMetrics
)
from app.integrations.sqlserver.connector import create_sqlserver_connector
from app.core.logger import logger
from app.worker.celery_app import celery_app 

# Initialize Router
router = APIRouter(prefix="/sync", tags=["SQL Server Sync"])


def _check_and_clear_stale_syncs(db: Session, sync_type: str, timeout_minutes: int = 60):
    """
    Check for stale syncs and mark them as failed if they've been running too long.
    
    Args:
        db: Database session
        sync_type: Type of sync to check
        timeout_minutes: Maximum time a sync can run before being marked stale
    """
    cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
    
    stale_syncs = db.query(SyncHistory).filter(
        SyncHistory.sync_type == sync_type,
        SyncHistory.status.in_([SyncStatus.PENDING.value, SyncStatus.RUNNING.value]),
        SyncHistory.started_at < cutoff_time
    ).all()
    
    for sync in stale_syncs:
        logger.warning(f"Clearing stale sync {sync.sync_id} (started at {sync.started_at})")
        sync.status = SyncStatus.FAILED.value
        sync.error_message = f"Sync timed out after {timeout_minutes} minutes"
        sync.completed_at = datetime.now()
    
    if stale_syncs:
        db.commit()
        logger.info(f"Cleared {len(stale_syncs)} stale {sync_type} syncs")


def _fail_undispatched_syncs(db: Session, sync_tracker, sync_ids, dispatch_error: Exception) -> None:
    """Mark sync rows FAILED when their Celery task could not be queued."""
    for sync_id in sync_ids:
        sync_tracker.mark_sync_failed(sync_id, f"Could not queue the sync task: {dispatch_error}", session=db)
    db.commit()


def _trigger_sync(db: Session, is_full_sync: bool, sync_type: SyncType, task_name: str, label: str):
    """Shared body of the four single-type trigger endpoints."""
    logger.info(f"Received request to trigger {label} sync (is_full_sync={is_full_sync})")
    
    try:
        # Clear stale syncs before checking for running syncs
        _check_and_clear_stale_syncs(db, sync_type.value, timeout_minutes=60)
        
        # Check if there's already a running sync of this type
        running_sync = db.query(SyncHistory).filter(
            SyncHistory.sync_type == sync_type.value,
            SyncHistory.status.in_([SyncStatus.PENDING.value, SyncStatus.RUNNING.value])
        ).first()
        
        if running_sync:
            raise HTTPException(
                status_code=409,
                detail=f"{label.capitalize()} sync already in progress (sync_id: {running_sync.sync_id})"
            )
        
        # Create SyncHistory record HERE in the API endpoint
        from app.services.sync.sync_tracker import SyncTracker
        from app.db.database import get_database
        
        db_instance = get_database()
        sync_tracker = SyncTracker(db_instance)
        
        # Create sync job record BEFORE queuing task
        sync_job = sync_tracker.create_sync_job(
            sync_type=sync_type,
            session=db,
            is_full_sync=is_full_sync
        )
        
        # Get the real sync_id
        real_sync_id = sync_job.sync_id
        
        # Trigger Celery task using registered task name
        try:
            task = celery_app.send_task(
                task_name,
                kwargs={
                    'is_full_sync': is_full_sync,
                    'sync_id': str(real_sync_id)
                }
            )
        except Exception as dispatch_error:
            # Without this the PENDING row would block new triggers until it goes stale
            _fail_undispatched_syncs(db, sync_tracker, [real_sync_id], dispatch_error)
            raise
        
        # Return REAL sync_id (no placeholder!)
        return SyncTriggerResponse(
            sync_id=real_sync_id,
            task_id=str(task.id),
            sync_type=sync_type.value,
            status="pending",
            is_full_sync=is_full_sync,
            triggered_at=datetime.now(),
            message=f"{label.capitalize()} sync {'(full)' if is_full_sync else '(incremental)'} started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering {label} sync: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger sync")


# ============================================================================
# GROUP 1: TRIGGER ENDPOINTS (Manual Sync Initiation)
# ============================================================================

@router.post("/trigger/employee_reports", response_model=SyncTriggerResponse, status_code=202)
def trigger_employee_reports_sync(
    is_full_sync: bool = Query(False, description="If true, perform full sync. If false, incremental sync."),
    db: Session = Depends(get_db)
):
    """
    Trigger employee reports synchronization from SQL Server to PostgreSQL.
    
    """
    return _trigger_sync(db, is_full_sync, SyncType.EMPLOYEE_REPORTS, 'sync.employee_reports', "employee reports")


@router.post("/trigger/vision_data", response_model=SyncTriggerResponse, status_code=202)
def trigger_vision_data_sync(
    is_full_sync: bool = Query(False, description="If true, perform full sync. If false, incremental sync."),
    db: Session = Depends(get_db)
):
    """
    Trigger vision data synchronization from SQL Server to PostgreSQL.
    
    This endpoint queues an asynchronous Celery task and returns immediately.
    Use the returned sync_id to poll for status updates.
    
    - **is_full_sync**: False = incremental (only new/modified records), True = full sync (all records)
    """
    return _trigger_sync(db, is_full_sync, SyncType.VISION_DATA, 'sync.vision_data', "vision data")


@router.post("/trigger/job_descriptions", response_model=SyncTriggerResponse, status_code=202)
def trigger_job_descriptions_sync(
    is_full_sync: bool = Query(False, description="If true, perform full sync. If false, incremental sync."),
    db: Session = Depends(get_db)
):
    """
    Trigger job descriptions synchronization from SQL Server to PostgreSQL.
    
    This endpoint queues an asynchronous Celery task and returns immediately.
    Use the returned sync_id to poll for status updates.
    
    - **is_full_sync**: False = incremental (only new/modified records), True = full sync (all records)
    """
    return _trigger_sync(db, is_full_sync, SyncType.JOB_DESCRIPTIONS, 'sync.job_descriptions', "job descriptions")


@router.post("/trigger/supervisor_feedback", response_model=SyncTriggerResponse, status_code=202)
def trigger_supervisor_feedback_sync(
    is_full_sync: bool = Query(False, description="If true, perform full sync. If false, incremental sync."),
    db: Session = Depends(get_db)
):
    """
    Trigger supervisor feedback synchronization from SQL Server to PostgreSQL.
    
    This endpoint queues an asynchronous Celery task and returns immediately.
    Use the returned sync_id to poll for status updates.
    
    - **is_full_sync**: False = incremental (only new/modified records), True = full sync (all records)
    """
    return _trigger_sync(db, is_full_sync, SyncType.SUPERVISOR_FEEDBACK, 'sync.supervisor_feedback', "supervisor feedback")


@router.post("/trigger/full", response_model=FullSyncTriggerResponse, status_code=202)
def trigger_full_sync(db: Session = Depends(get_db)):
    """
    Trigger full synchronization of employee reports, vision data, job descriptions, and supervisor feedback.
    
    This runs all four sync types sequentially in a single Celery task.
    All syncs will be in FULL mode (all records, not incremental).
    """
    logger.info("Received request to trigger full sync (all four types)")
    
    try:
        # Clear stale syncs for all four types
        _check_and_clear_stale_syncs(db, SyncType.EMPLOYEE_REPORTS.value, timeout_minutes=60)
        _check_and_clear_stale_syncs(db, SyncType.VISION_DATA.value, timeout_minutes=60)
        _check_and_clear_stale_syncs(db, SyncType.JOB_DESCRIPTIONS.value, timeout_minutes=60)
        _check_and_clear_stale_syncs(db, SyncType.SUPERVISOR_FEEDBACK.value, timeout_minutes=60)
        
        # Check if any sync is already running
        running_syncs = db.query(SyncHistory).filter(
            SyncHistory.sync_type.in_([
                SyncType.EMPLOYEE_REPORTS.value, 
                SyncType.VISION_DATA.value,
                SyncType.JOB_DESCRIPTIONS.value,
                SyncType.SUPERVISOR_FEEDBACK.value
            ]),
            SyncHistory.status.in_([SyncStatus.PENDING.value, SyncStatus.RUNNING.value])
        ).all()
        
        if running_syncs:
            running_types = [s.sync_type for s in running_syncs]
            raise HTTPException(
                status_code=409,
                detail=f"Sync already in progress for: {', '.join(running_types)}"
            )
        
        # Create SyncHistory records for ALL THREE sync types
        from app.services.sync.sync_tracker import SyncTracker
        from app.db.database import get_database
        
        db_instance = get_database()
        sync_tracker = SyncTracker(db_instance)
        
        # Create sync job for employee reports (full mode)
        employee_sync_job = sync_tracker.create_sync_job(
            sync_type=SyncType.EMPLOYEE_REPORTS,
            session=db,
            is_full_sync=True
        )
        
        # Create sync job for vision data (full mode)
        vision_sync_job = sync_tracker.create_sync_job(
            sync_type=SyncType.VISION_DATA,
            session=db,
            is_full_sync=True
        )
        
        # Create sync job for job descriptions (full mode)
        jd_sync_job = sync_tracker.create_sync_job(
            sync_type=SyncType.JOB_DESCRIPTIONS,
            session=db,
            is_full_sync=True
        )

        # Create sync job for supervisor feedback (full mode)
        sf_sync_job = sync_tracker.create_sync_job(
            sync_type=SyncType.SUPERVISOR_FEEDBACK,
            session=db,
            is_full_sync=True
        )
        
        # Get the real sync_ids
        employee_sync_id = employee_sync_job.sync_id
        vision_sync_id = vision_sync_job.sync_id
        jd_sync_id = jd_sync_job.sync_id
        sf_sync_id = sf_sync_job.sync_id
        
        # Trigger full sync task with ALL THREE sync_ids
        try:
            task = celery_app.send_task(
                'sync.full',
                kwargs={
                    'employee_sync_id': str(employee_sync_id),
                    'vision_sync_id': str(vision_sync_id),
                    'jd_sync_id': str(jd_sync_id),
                    'sf_sync_id': str(sf_sync_id)
                }
            )
        except Exception as dispatch_error:
            _fail_undispatched_syncs(
                db, sync_tracker, [employee_sync_id, vision_sync_id, jd_sync_id, sf_sync_id], dispatch_error
            )
            raise
        
        # Return ALL FOUR sync_ids
        return FullSyncTriggerResponse(
            sync_type="full",
            employee_reports_sync_id=employee_sync_id,
            vision_data_sync_id=vision_sync_id,
            job_descriptions_sync_id=jd_sync_id,
            supervisor_feedback_sync_id=sf_sync_id,
            task_id=str(task.id),
            status="pending",
            triggered_at=datetime.now(),
            message="Full sync (employee reports, vision data, job descriptions, and supervisor feedback) started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering full sync: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger full sync")


# ============================================================================
# GROUP 2: STATUS & MONITORING ENDPOINTS
# ============================================================================

@router.get("/status/{sync_id}", response_model=SyncStatusResponse)
def get_sync_status(
    sync_id: UUID = Path(..., description="Sync job identifier"),
    db: Session = Depends(get_db)
):
    """
    Get the current status and metrics of a specific sync job.
    
    Use this endpoint to poll for progress while a sync is running,
    or to retrieve final results after completion.
    """
    try:
        sync_job = db.query(SyncHistory).filter(SyncHistory.sync_id == sync_id).first()
        
        if not sync_job:
            raise HTTPException(status_code=404, detail=f"Sync job {sync_id} not found")
        
        # Calculate duration
        duration = None
        if sync_job.started_at and sync_job.completed_at:
            duration = (sync_job.completed_at - sync_job.started_at).total_seconds()
        
        # Calculate percent complete
        percent_complete = 0.0
        if sync_job.records_queried and sync_job.records_queried > 0:
            percent_complete = round((sync_job.records_synced / sync_job.records_queried) * 100, 1)
        
        # Build progress metrics
        progress = SyncProgressMetrics(
            records_queried=sync_job.records_queried or 0,
            records_synced=sync_job.records_synced or 0,
            records_created=sync_job.records_created or 0,
            records_updated=sync_job.records_updated or 0,
            records_skipped=sync_job.records_skipped or 0,
            error_count=sync_job.error_count or 0,
            percent_complete=percent_complete
        )
        
        # Extract is_full_sync from sync_options
        is_full_sync = False
        if sync_job.sync_options and isinstance(sync_job.sync_options, dict):
            is_full_sync = sync_job.sync_options.get('is_full_sync', False)
        
        return SyncStatusResponse(
            sync_id=sync_job.sync_id,
            sync_type=sync_job.sync_type,
            status=sync_job.status,
            is_full_sync=is_full_sync,
            started_at=sync_job.started_at,
            completed_at=sync_job.completed_at,
            duration_seconds=duration,
            progress=progress,
            metrics=sync_job.sync_metadata or {},
            last_sync_timestamp=sync_job.last_sync_timestamp,
            error_message=sync_job.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving sync status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving sync status")


@router.get("/last-successful/{sync_type}", response_model=LastSyncResponse)
def get_last_successful_sync(
    sync_type: str = Path(..., description="Sync type: 'employee_reports', 'vision_data', or 'job_descriptions'"),
    db: Session = Depends(get_db)
):
    """
    Get information about the last successful sync for a specific type.
    
    Returns the timestamp of the last successful sync, which is used
    by incremental syncs to determine where to start.
    """
    try:
        # Validate sync type
        if sync_type not in [
            SyncType.EMPLOYEE_REPORTS.value, 
            SyncType.VISION_DATA.value,
            SyncType.JOB_DESCRIPTIONS.value,
            SyncType.SUPERVISOR_FEEDBACK.value
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sync_type. Must be 'employee_reports', 'vision_data', 'job_descriptions', or 'supervisor_feedback'"
            )
        
        # Query for last successful sync
        last_sync = db.query(SyncHistory).filter(
            SyncHistory.sync_type == sync_type,
            SyncHistory.status == SyncStatus.COMPLETED.value,
            SyncHistory.last_sync_timestamp.isnot(None)
        ).order_by(
            SyncHistory.last_sync_timestamp.desc()
        ).first()
        
        if not last_sync:
            return LastSyncResponse(
                sync_type=sync_type,
                last_successful_sync_id=None,
                last_sync_timestamp=None,
                records_synced=None,
                completed_at=None
            )
        
        return LastSyncResponse(
            sync_type=sync_type,
            last_successful_sync_id=last_sync.sync_id,
            last_sync_timestamp=last_sync.last_sync_timestamp,
            records_synced=last_sync.records_synced,
            completed_at=last_sync.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving last successful sync: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving last sync")


# ============================================================================
# GROUP 3: HISTORY & REPORTING ENDPOINTS
# ============================================================================

@router.get("/history", response_model=SyncHistoryListResponse)
def list_sync_history(
    sync_type: Optional[str] = Query(None, description="Filter by sync type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter syncs after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter syncs before this date"),
    is_full_sync: Optional[bool] = Query(None, description="Filter by sync mode"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("started_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    db: Session = Depends(get_db)
):
    """
    List sync history with optional filtering, sorting, and pagination.
    
    Use this endpoint to view past sync operations and their results.
    """
    try:
        # Build query
        query = db.query(SyncHistory)
        
        # Apply filters
        if sync_type:
            # Validate sync_type includes all four types
            if sync_type not in [
                SyncType.EMPLOYEE_REPORTS.value, 
                SyncType.VISION_DATA.value,
                SyncType.JOB_DESCRIPTIONS.value,
                SyncType.SUPERVISOR_FEEDBACK.value
            ]:
                raise HTTPException(status_code=400, detail=f"Invalid sync_type")
            query = query.filter(SyncHistory.sync_type == sync_type)
        
        if status:
            valid_statuses = [s.value for s in SyncStatus]
            if status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Invalid status")
            query = query.filter(SyncHistory.status == status)
        
        if start_date:
            query = query.filter(SyncHistory.started_at >= start_date)
        
        if end_date:
            query = query.filter(SyncHistory.started_at <= end_date)
        
        if is_full_sync is not None:
            # Filter by sync_options JSONB field; a missing flag counts as incremental, as in the response
            query = query.filter(
                func.coalesce(SyncHistory.sync_options['is_full_sync'].as_boolean(), False) == is_full_sync
            )
        
        sortable = sorted(SyncHistory.__mapper__.columns.keys())
        if sort_by not in sortable:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by. Valid fields: {', '.join(sortable)}")

        # Count total before pagination
        total = query.count()
        
        # Apply sorting
        if sort_order.lower() == 'desc':
            query = query.order_by(getattr(SyncHistory, sort_by).desc())
        else:
            query = query.order_by(getattr(SyncHistory, sort_by).asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        pages = (total + page_size - 1) // page_size
        
        # Build response items
        history_items = []
        for sync_job in items:
            # Calculate duration
            duration = None
            if sync_job.started_at and sync_job.completed_at:
                duration = (sync_job.completed_at - sync_job.started_at).total_seconds()
            
            # Extract is_full_sync
            is_full = False
            if sync_job.sync_options and isinstance(sync_job.sync_options, dict):
                is_full = sync_job.sync_options.get('is_full_sync', False)
            
            history_items.append(SyncHistoryItem(
                sync_id=sync_job.sync_id,
                sync_type=sync_job.sync_type,
                status=sync_job.status,
                is_full_sync=is_full,
                started_at=sync_job.started_at,
                completed_at=sync_job.completed_at,
                duration_seconds=duration,
                records_synced=sync_job.records_synced or 0,
                records_queried=sync_job.records_queried or 0,
                error_count=sync_job.error_count or 0,
                last_sync_timestamp=sync_job.last_sync_timestamp
            ))
        
        return SyncHistoryListResponse(
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            items=history_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sync history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing history")


@router.get("/{sync_id}/errors", response_model=SyncErrorsResponse)
def get_sync_errors(
    sync_id: UUID = Path(..., description="Sync job identifier"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get detailed errors for a specific sync job.
    
    Only returns data if the sync job encountered errors.
    Useful for debugging failed or partial syncs.
    """
    try:
        sync_job = db.query(SyncHistory).filter(SyncHistory.sync_id == sync_id).first()
        
        if not sync_job:
            raise HTTPException(status_code=404, detail=f"Sync job {sync_id} not found")
        
        # Extract errors from error_details JSONB field
        all_errors = []
        if sync_job.error_details and isinstance(sync_job.error_details, dict):
            all_errors = sync_job.error_details.get('errors', [])
        
        # Paginate errors
        total_errors = len(all_errors)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_errors = all_errors[start_idx:end_idx]
        
        # Convert to response format
        error_items = [
            SyncErrorItem(
                row_number=err.get('row_number', 0),
                field_name=err.get('field_name'),
                error_message=err.get('error_message', 'Unknown error'),
                error_category=err.get('error_category'),
                row_data=err.get('row_data')
            )
            for err in paginated_errors
        ]
        
        return SyncErrorsResponse(
            sync_id=sync_id,
            total_errors=total_errors,
            page=page,
            page_size=page_size,
            errors=error_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving sync errors: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving errors")


# ============================================================================
# GROUP 4: CONFIGURATION ENDPOINTS (Read-Only)
# ============================================================================

@router.get("/config", response_model=SyncConfigResponse)
def get_sync_configuration():
    """
    Get current sync service configuration.
    
    Returns read-only configuration information including:
    - SQL Server connection details
    - Allowed tables and columns
    - Sync settings
    - Scheduled sync information
    """
    try:
        connector = create_sqlserver_connector()
        
        # Test connection status
        connection_status = "connected" if connector.test_connection() else "disconnected"
        
        # Get configuration
        sync_enabled = os.getenv('SYNC_ENABLED', 'true').lower() == 'true'
        
        return SyncConfigResponse(
            sql_server={
                "host": connector.server,
                "database": connector.database,
                "connection_status": connection_status
            },
            allowed_tables=list(connector.get_allowed_tables()),
            allowed_timestamp_columns=list(connector.get_allowed_timestamp_columns()),
            sync_settings={
                "max_batch_size": connector.max_batch_size,
                "error_threshold_percent": float(os.getenv('SYNC_ERROR_THRESHOLD_PERCENT', '10.0')),
                "default_chunk_size": 1000
            },
            sync_schedule={
                "incremental_sync": {
                    "enabled": sync_enabled,
                    "schedule": "Monday 2:00 AM",
                    "next_run": None  # Would need to query Celery beat for actual next run
                },
                "full_sync": {
                    "enabled": False,
                    "schedule": "Manual trigger only"
                }
            },
            sync_enabled=sync_enabled
        )
        
    except Exception as e:
        logger.error(f"Error retrieving sync configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving configuration")


@router.get("/test-connection", response_model=ConnectionTestResponse)
def test_sql_server_connection():
    """
    Test SQL Server connectivity without triggering a sync.
    
    Useful for diagnosing connection issues before attempting a sync.
    """
    try:
        connector = create_sqlserver_connector()
        
        start_time = time.time()
        connection_successful = connector.test_connection()
        connection_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        if not connection_successful:
            return ConnectionTestResponse(
                status="disconnected",
                server=connector.server,
                database=connector.database,
                available_tables=[],
                connection_time_ms=connection_time,
                message="Failed to connect to SQL Server"
            )
        
        # Get available tables
        available_tables = list(connector.get_allowed_tables())
        
        return ConnectionTestResponse(
            status="connected",
            server=connector.server,
            database=connector.database,
            available_tables=available_tables,
            connection_time_ms=connection_time,
            message="Successfully connected to SQL Server"
        )
        
    except Exception as e:
        logger.error(f"Error testing SQL Server connection: {str(e)}")
        return ConnectionTestResponse(
            status="error",
            server="unknown",
            database="unknown",
            available_tables=[],
            connection_time_ms=0,
            message=f"Error: {str(e)}"
        )