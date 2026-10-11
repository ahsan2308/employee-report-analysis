"""
Sync API Routes

Endpoints for triggering and monitoring SQL Server to PostgreSQL synchronization.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.api.deps import get_db
from app.api.serializers import sync_history_item, sync_status_response
from app.models.sync_models import SyncStatus, SyncType
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
    ConnectionTestResponse
)
from app.repositories import sync_history
from app.services.sync import source as sync_source
from app.services.sync import trigger as sync_trigger
from app.core.logger import logger

# Initialize Router
router = APIRouter(prefix="/sync", tags=["SQL Server Sync"])


def _trigger_sync(db: Session, is_full_sync: bool, sync_type: SyncType, label: str):
    """Shared body of the four single-type trigger endpoints."""
    logger.info(f"Received request to trigger {label} sync (is_full_sync={is_full_sync})")
    
    try:
        sync_job, task = sync_trigger.trigger_sync(db, sync_type, is_full_sync, label)
        return SyncTriggerResponse(
            sync_id=sync_job.sync_id,
            task_id=str(task.id),
            sync_type=sync_type.value,
            status="pending",
            is_full_sync=is_full_sync,
            triggered_at=datetime.now(),
            message=f"{label.capitalize()} sync {'(full)' if is_full_sync else '(incremental)'} started successfully"
        )
    except sync_trigger.SyncAlreadyRunning as running:
        raise HTTPException(status_code=409, detail=str(running))
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
    return _trigger_sync(db, is_full_sync, SyncType.EMPLOYEE_REPORTS, "employee reports")


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
    return _trigger_sync(db, is_full_sync, SyncType.VISION_DATA, "vision data")


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
    return _trigger_sync(db, is_full_sync, SyncType.JOB_DESCRIPTIONS, "job descriptions")


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
    return _trigger_sync(db, is_full_sync, SyncType.SUPERVISOR_FEEDBACK, "supervisor feedback")


@router.post("/trigger/full", response_model=FullSyncTriggerResponse, status_code=202)
def trigger_full_sync(db: Session = Depends(get_db)):
    """
    Trigger full synchronization of employee reports, vision data, job descriptions, and supervisor feedback.
    
    This runs all four sync types sequentially in a single Celery task.
    All syncs will be in FULL mode (all records, not incremental).
    """
    logger.info("Received request to trigger full sync (all four types)")
    
    try:
        jobs, task = sync_trigger.trigger_full_sync(db)
        return FullSyncTriggerResponse(
            sync_type="full",
            employee_reports_sync_id=jobs[SyncType.EMPLOYEE_REPORTS].sync_id,
            vision_data_sync_id=jobs[SyncType.VISION_DATA].sync_id,
            job_descriptions_sync_id=jobs[SyncType.JOB_DESCRIPTIONS].sync_id,
            supervisor_feedback_sync_id=jobs[SyncType.SUPERVISOR_FEEDBACK].sync_id,
            task_id=str(task.id),
            status="pending",
            triggered_at=datetime.now(),
            message="Full sync (employee reports, vision data, job descriptions, and supervisor feedback) started successfully"
        )
    except sync_trigger.SyncAlreadyRunning as running:
        raise HTTPException(status_code=409, detail=str(running))
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
        sync_job = sync_history.get_sync(db, sync_id)
        
        if not sync_job:
            raise HTTPException(status_code=404, detail=f"Sync job {sync_id} not found")
        
        return SyncStatusResponse(**sync_status_response(sync_job))
        
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
        
        # The same rule incremental syncs use to pick their starting point
        last_sync = sync_history.last_successful_sync(db, SyncType(sync_type))
        
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
        # Validate filters (sync_type covers all four types)
        if sync_type and sync_type not in [
            SyncType.EMPLOYEE_REPORTS.value,
            SyncType.VISION_DATA.value,
            SyncType.JOB_DESCRIPTIONS.value,
            SyncType.SUPERVISOR_FEEDBACK.value
        ]:
            raise HTTPException(status_code=400, detail="Invalid sync_type")
        
        if status and status not in [s.value for s in SyncStatus]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        if sort_by not in sync_history.SORTABLE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by. Valid fields: {', '.join(sync_history.SORTABLE_FIELDS)}")
        
        items, total = sync_history.list_sync_history(
            db,
            sync_type=sync_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            is_full_sync=is_full_sync,
            sort_by=sort_by,
            descending=sort_order.lower() == 'desc',
            offset=(page - 1) * page_size,
            limit=page_size
        )
        
        # Calculate total pages
        pages = (total + page_size - 1) // page_size
        
        history_items = [SyncHistoryItem(**sync_history_item(sync_job)) for sync_job in items]
        
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
        sync_job = sync_history.get_sync(db, sync_id)
        
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
        return SyncConfigResponse(**sync_source.sync_configuration())
        
    except Exception as e:
        logger.error(f"Error retrieving sync configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving configuration")


@router.get("/test-connection", response_model=ConnectionTestResponse)
def test_sql_server_connection():
    """
    Test SQL Server connectivity without triggering a sync.
    
    Useful for diagnosing connection issues before attempting a sync.
    """
    return ConnectionTestResponse(**sync_source.check_connection())
