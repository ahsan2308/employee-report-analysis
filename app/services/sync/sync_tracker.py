"""
Sync Tracker

Manages SyncHistory database records for tracking sync operations.
Provides CRUD operations for sync job lifecycle management.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import json
import math

from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.core.logger import logger


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


class SyncTracker:
    """
    Tracks sync operations in the SyncHistory table.
    
    Responsibilities:
    - Create sync job records
    - Query last successful sync timestamps
    - Update sync status and metrics
    - Store error details

    Note: All methods require an active session to be passed.
    This ensures objects remain attached and prevents detachment errors.
    """
    
    def __init__(self, db_instance): 
        """
        Initialize tracker with database instance.
        
        Args:
            db_instance: Database instance from get_database()
        """
        self.db_instance = db_instance
    
    def create_sync_job(self,
                       sync_type: SyncType,
                       session: Session,
                       is_full_sync: bool = False) -> SyncHistory:
        """
        Create a new sync job record in PENDING state.
        
        Args:
            sync_type: Type of sync (EMPLOYEE_REPORTS, VISION_DATA, FULL_SYNC)
            is_full_sync: Whether this is a full sync or incremental
            session: Database session (REQUIRED)
            
        Returns:
            Created SyncHistory instance with generated sync_id
        """
        sync_job = SyncHistory(
            sync_type=sync_type.value,
            status=SyncStatus.PENDING.value,
            sync_options={"is_full_sync": is_full_sync}
        )
        
        session.add(sync_job)
        session.commit()
        session.refresh(sync_job)
        
        logger.info(f"Created sync job {sync_job.sync_id} (type: {sync_type.value}, full_sync: {is_full_sync})")
        return sync_job
    
    def get_last_successful_sync(self, sync_type: SyncType, session: Session) -> Optional[datetime]:
        """
        Get the timestamp of the last successful sync for a given type.
        
        Args:
            sync_type: Type of sync to query
            session: Database session
            
        Returns:
            Datetime of last successful sync, or None if no successful sync exists
        """
        last_sync = last_successful_sync(session, sync_type)
        
        if last_sync:
            logger.info(f"Last successful {sync_type.value} sync: {last_sync.last_sync_timestamp}")
            return last_sync.last_sync_timestamp
        
        logger.info(f"Last successful {sync_type.value} sync: None")
        return None


    def update_sync_status(self, 
                          sync_id, 
                          status: SyncStatus, 
                          session: Session,
                          metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Update sync job status and metrics.
        
        Sets appropriate timestamps based on status transitions:
        - RUNNING: Sets started_at
        - COMPLETED/FAILED: Sets completed_at

        Args:
            sync_id: UUID of the sync job
            status: New status to set
            metrics: Optional metrics dictionary to store
            session: Database session (REQUIRED)
        """
        sync_job = session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_id
        ).first()
        
        if not sync_job:
            logger.error(f"Sync job {sync_id} not found")
            return
        
        # Update status
        sync_job.status = status.value
        
        # Set timestamps based on status
        if status == SyncStatus.RUNNING and not sync_job.started_at:
            sync_job.started_at = datetime.now()
        
        if status in (SyncStatus.COMPLETED, SyncStatus.FAILED, SyncStatus.PARTIAL):
            sync_job.completed_at = datetime.now()
        
        # Update metrics if provided
        if metrics:
            sync_job.records_queried = metrics.get('records_queried', sync_job.records_queried or 0)
            sync_job.records_synced = metrics.get('records_synced', sync_job.records_synced or 0)
            sync_job.records_created = metrics.get('records_created', sync_job.records_created or 0)
            sync_job.records_updated = metrics.get('records_updated', sync_job.records_updated or 0)
            sync_job.records_skipped = metrics.get('records_skipped', sync_job.records_skipped or 0)
            sync_job.error_count = metrics.get('error_count', sync_job.error_count or 0)
            
            # Update last_sync_timestamp for BOTH completed AND partial syncs
            # Partial syncs may have some errors but successfully synced records still need timestamp advancement
            if status in (SyncStatus.COMPLETED, SyncStatus.PARTIAL) and 'last_sync_timestamp' in metrics:
                if metrics['last_sync_timestamp']:
                    sync_job.last_sync_timestamp = metrics['last_sync_timestamp']
                    logger.info(f"Updated last_sync_timestamp to {metrics['last_sync_timestamp']}")
            
            # Store type-specific metrics in sync_metadata JSONB field
            if 'metrics' in metrics:
                sync_job.sync_metadata = metrics['metrics']
        
        # Explicitly mark the object as dirty to ensure SQLAlchemy tracks changes
        session.add(sync_job)
        
        logger.info(f"Updated sync job {sync_id} status to {status.value}")
    
    def mark_sync_failed(self, sync_id, error_message: str, session: Session) -> None:
        """
        Mark a sync job as FAILED with error message.
        
        Args:
            sync_id: UUID of the sync job
            error_message: Error message to store
            session: Database session (REQUIRED)
        """
        sync_job = session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_id
        ).first()
        
        if not sync_job:
            logger.error(f"Sync job {sync_id} not found")
            return
        
        sync_job.status = SyncStatus.FAILED.value
        sync_job.error_message = error_message
        sync_job.completed_at = datetime.now()
        
        # Explicitly mark the object as dirty to ensure SQLAlchemy tracks changes
        session.add(sync_job)
        
        logger.error(f"Sync job {sync_id} failed: {error_message}")
    
    def save_sync_errors(self, sync_id, errors: List[Dict[str, Any]], session: Session) -> None:
        """
        Store sync errors in the error_details JSONB field.
        
        Stores errors from ImportErrorHandler in the same format as import errors
        for consistency with CSV import error handling.

        Args:
            sync_id: UUID of the sync job
            errors: List of error dictionaries with row_number, error_message, etc.
            session: Database session (REQUIRED)
        """
        sync_job = session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_id
        ).first()
        
        if not sync_job:
            logger.error(f"Sync job {sync_id} not found")
            return
        
        # Sanitize errors to make them JSON-serializable
        sanitized_errors = self._sanitize_errors_for_json(errors)
        
        # Store errors in JSONB field
        sync_job.error_details = {"errors": sanitized_errors}
        sync_job.error_count = len(sanitized_errors)
        
        # Don't commit here - let the caller's context manager handle it
        logger.info(f"Saved {len(sanitized_errors)} errors for sync job {sync_id}")
    
    def _sanitize_errors_for_json(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitize error data to make it JSON-serializable.
        
        Converts NaN, Infinity, and other non-JSON values to None.
        
        Args:
            errors: List of error dictionaries
            
        Returns:
            List of sanitized error dictionaries
        """
        def sanitize_value(value):
            """Recursively sanitize a value for JSON serialization."""
            if value is None:
                return None
            
            # Handle float NaN and Infinity
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    return None
                return value
            
            # Handle dictionaries recursively
            if isinstance(value, dict):
                return {k: sanitize_value(v) for k, v in value.items()}
            
            # Handle lists recursively
            if isinstance(value, list):
                return [sanitize_value(item) for item in value]
            
            # Return other types as-is
            return value
        
        sanitized = []
        for error in errors:
            try:
                # Sanitize the entire error dictionary
                sanitized_error = sanitize_value(error)
                
                # Verify it's JSON-serializable
                json.dumps(sanitized_error)
                
                sanitized.append(sanitized_error)
            except (TypeError, ValueError) as e:
                # If still can't serialize, create a minimal error record
                logger.warning(f"Could not sanitize error, creating minimal record: {str(e)}")
                sanitized.append({
                    "row_number": error.get("row_number", 0),
                    "field_name": error.get("field_name"),
                    "error_message": error.get("error_message", "Unknown error"),
                    "row_data": None  # Drop problematic row_data
                })
        
        return sanitized
