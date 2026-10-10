"""
Sync Tasks

This module contains Celery tasks for synchronizing data from SQL Server to PostgreSQL.
"""
from typing import Dict, Any, Optional
from celery import shared_task, Task
from datetime import datetime

from app.core.logger import logger
from app.db.database import get_database
from app.models.sync_models import SyncHistory, SyncStatus
from app.services.sync_service import create_sync_service


class SyncTask(Task):
    """Base task class for sync operations with error handling."""
    
    _db = None
    _sync_service = None
    
    @property
    def db(self):
        """Get database session."""
        if self._db is None:
            self._db = get_database().create_session()
        return self._db
    
    @property
    def sync_service(self):
        """Get sync service instance."""
        if self._sync_service is None:
            self._sync_service = create_sync_service()
        return self._sync_service
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failures by updating sync status."""
        sync_id = kwargs.get('sync_id') or (args[0] if args else None)
        if not sync_id:
            logger.error(f"Task {task_id} failed but no sync_id was found in args or kwargs")
            return
            
        try:
            # Get sync job directly from database
            sync_job = self.db.query(SyncHistory).filter(SyncHistory.sync_id == sync_id).first()
            if not sync_job:
                logger.error(f"Could not find sync job {sync_id} when handling failure")
                return
                
            # Update sync job status if not already failed
            if sync_job.status != SyncStatus.FAILED.value:
                sync_job.status = SyncStatus.FAILED.value
                sync_job.error_message = str(exc)
                sync_job.completed_at = datetime.now()
                self.db.commit()
                logger.info(f"Updated sync job {sync_id} status to FAILED due to task error")
                
        except Exception as e:
            logger.error(f"Error handling task failure for sync job {sync_id}: {str(e)}")
        finally:
            # Ensure cleanup even if error handling fails
            self._cleanup_resources()
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up resources after task completion."""
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Centralized cleanup for database and service resources."""
        if self._db:
            try:
                self._db.close()
                logger.debug("Closed database session in SyncTask cleanup")
            except Exception as e:
                logger.error(f"Error closing database session: {str(e)}")
            finally:
                self._db = None
        
        self._sync_service = None


@shared_task(bind=True, base=SyncTask, name="sync.employee_reports")
def sync_employee_reports_task(self, is_full_sync: bool = False, sync_id: Optional[str] = None):
    """
    Sync employee reports from SQL Server to PostgreSQL.
    
    Args:
        is_full_sync: If True, sync all records. If False, incremental sync.
        sync_id: Optional sync_id if already created by API endpoint.
        
    Returns:
        Dictionary containing sync results
    """
    logger.info(f"Starting employee reports sync task, mode: {'full' if is_full_sync else 'incremental'}")
    
    try:
        # If sync_id was provided, use existing sync job
        # Otherwise, create a new one (backward compatibility)
        if sync_id:
            logger.info(f"Using existing sync job: {sync_id}")
            sync_job = self.sync_service.sync_employee_reports(
                is_full_sync=is_full_sync,
                existing_sync_id=sync_id
            )
        else:
            # Old behavior: create sync job inside task
            sync_job = self.sync_service.sync_employee_reports(is_full_sync=is_full_sync)
        
        # Extract attributes IMMEDIATELY after sync returns
        sync_id = str(sync_job.sync_id)
        status = sync_job.status
        sync_type = sync_job.sync_type
        error_count = sync_job.error_count or 0
        
        # Access JSONB field immediately - THIS is where all metrics are stored
        sync_metadata = sync_job.sync_metadata or {}
        
        # Extract top-level metrics from sync_metadata
        records_queried = sync_metadata.get('records_queried', 0)
        records_synced = sync_metadata.get('records_synced', 0)
        
        # Extract the nested "metrics" key which contains processor-specific metrics
        processor_metrics = sync_metadata.get('metrics', {})
        
        # Extract nested metrics
        employees_created = processor_metrics.get('employees_created', 0)
        employees_updated = processor_metrics.get('employees_updated', 0)
        reports_created = processor_metrics.get('reports_created', 0)
        reports_updated = processor_metrics.get('reports_updated', 0)
        
        # Build log message
        metrics_log = f"Completed employee reports sync {sync_id}: " \
                      f"{records_synced}/{records_queried} rows synced, " \
                      f"{error_count} errors"
        
        if employees_created or employees_updated or reports_created or reports_updated:
            metrics_log += f", {employees_created} employees created, {employees_updated} employees updated, " \
                          f"{reports_created} reports created, {reports_updated} reports updated"
        
        logger.info(metrics_log)
        
        # Return dictionary for Celery (NO TIMESTAMPS)
        return {
            "sync_id": sync_id,
            "status": status,
            "sync_type": sync_type,
            "records_queried": records_queried,
            "records_synced": records_synced,
            "error_count": error_count,
            "metrics": {
                "employees_created": employees_created,
                "employees_updated": employees_updated,
                "reports_created": reports_created,
                "reports_updated": reports_updated
            }
        }
        
    except Exception as e:
        logger.error(f"Error in employee reports sync task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, base=SyncTask, name="sync.vision_data")
def sync_vision_data_task(self, is_full_sync: bool = False, sync_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync vision data from SQL Server to PostgreSQL.
    
    Args:
        is_full_sync: If True, sync all records. If False, incremental sync.
        sync_id: Optional sync_id if already created by API endpoint.
        
    Returns:
        Dictionary containing sync results
    """
    logger.info(f"Starting vision data sync task, mode: {'full' if is_full_sync else 'incremental'}")
    
    try:
        # If sync_id was provided, use existing sync job
        # Otherwise, create a new one (backward compatibility)
        if sync_id:
            logger.info(f"Using existing sync job: {sync_id}")
            sync_job = self.sync_service.sync_vision_data(
                is_full_sync=is_full_sync,
                existing_sync_id=sync_id
            )
        else:
            # Old behavior: create sync job inside task
            sync_job = self.sync_service.sync_vision_data(is_full_sync=is_full_sync)
        
        # Extract attributes IMMEDIATELY after sync returns
        sync_id = str(sync_job.sync_id)
        status = sync_job.status
        sync_type = sync_job.sync_type
        error_count = sync_job.error_count or 0
        
        # Access JSONB field immediately - THIS is where all metrics are stored
        sync_metadata = sync_job.sync_metadata or {}
        
        # Extract top-level metrics from sync_metadata
        records_queried = sync_metadata.get('records_queried', 0)
        records_synced = sync_metadata.get('records_synced', 0)
        
        # Extract the nested "metrics" key which contains processor-specific metrics
        processor_metrics = sync_metadata.get('metrics', {})
        
        # Extract type-specific metrics
        vision_records_created = processor_metrics.get('vision_records_created', 0)
        vision_records_updated = processor_metrics.get('vision_records_updated', 0)
        
        # Build log message
        metrics_log = f"Completed vision data sync {sync_id}: " \
                      f"{records_synced}/{records_queried} rows synced, " \
                      f"{error_count} errors"
        
        if vision_records_created or vision_records_updated:
            metrics_log += f", {vision_records_created} vision records created, " \
                          f"{vision_records_updated} vision records updated"
        
        logger.info(metrics_log)
        
        # Return dictionary for Celery (NO TIMESTAMPS)
        return {
            "sync_id": sync_id,
            "status": status,
            "sync_type": sync_type,
            "records_queried": records_queried,
            "records_synced": records_synced,
            "error_count": error_count,
            "metrics": {
                "vision_records_created": vision_records_created,
                "vision_records_updated": vision_records_updated
            }
        }
        
    except Exception as e:
        logger.error(f"Error in vision data sync task: {str(e)}", exc_info=True)
        raise

@shared_task(bind=True, base=SyncTask, name="sync.job_descriptions")
def sync_job_descriptions_task(self, is_full_sync: bool = False, sync_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync job descriptions from SQL Server to PostgreSQL.
    
    Args:
        is_full_sync: If True, sync all records. If False, incremental sync.
        sync_id: Optional sync_id if already created by API endpoint.
        
    Returns:
        Dictionary containing sync results
    """
    logger.info(f"Starting job descriptions sync task, mode: {'full' if is_full_sync else 'incremental'}")
    
    try:
        # If sync_id was provided, use existing sync job
        # Otherwise, create a new one (backward compatibility)
        if sync_id:
            logger.info(f"Using existing sync job: {sync_id}")
            sync_job = self.sync_service.sync_job_descriptions(
                is_full_sync=is_full_sync,
                existing_sync_id=sync_id
            )
        else:
            # Old behavior: create sync job inside task
            sync_job = self.sync_service.sync_job_descriptions(is_full_sync=is_full_sync)
        
        # Extract attributes IMMEDIATELY after sync returns
        sync_id = str(sync_job.sync_id)
        status = sync_job.status
        sync_type = sync_job.sync_type
        error_count = sync_job.error_count or 0
        
        # Access JSONB field immediately - THIS is where all metrics are stored
        sync_metadata = sync_job.sync_metadata or {}
        
        # Extract top-level metrics from sync_metadata
        records_queried = sync_metadata.get('records_queried', 0)
        records_synced = sync_metadata.get('records_synced', 0)
        
        # Extract the nested "metrics" key which contains processor-specific metrics
        processor_metrics = sync_metadata.get('metrics', {})
        
        # Extract type-specific metrics
        jd_records_created = processor_metrics.get('jd_records_created', 0)
        jd_records_updated = processor_metrics.get('jd_records_updated', 0)
        
        # Build log message
        metrics_log = f"Completed job descriptions sync {sync_id}: " \
                      f"{records_synced}/{records_queried} rows synced, " \
                      f"{error_count} errors"
        
        if jd_records_created or jd_records_updated:
            metrics_log += f", {jd_records_created} JD records created, " \
                          f"{jd_records_updated} JD records updated"
        
        logger.info(metrics_log)
        
        # Return dictionary for Celery (NO TIMESTAMPS)
        return {
            "sync_id": sync_id,
            "status": status,
            "sync_type": sync_type,
            "records_queried": records_queried,
            "records_synced": records_synced,
            "error_count": error_count,
            "metrics": {
                "jd_records_created": jd_records_created,
                "jd_records_updated": jd_records_updated
            }
        }
        
    except Exception as e:
        logger.error(f"Error in job descriptions sync task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, base=SyncTask, name="sync.supervisor_feedback")
def sync_supervisor_feedback_task(self, is_full_sync: bool = False, sync_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync supervisor feedback from SQL Server to PostgreSQL.
    
    Args:
        is_full_sync: If True, sync all records. If False, incremental sync.
        sync_id: Optional sync_id if already created by API endpoint.
        
    Returns:
        Dictionary containing sync results
    """
    logger.info(f"Starting supervisor feedback sync task, mode: {'full' if is_full_sync else 'incremental'}")
    
    try:
        # If sync_id was provided, use existing sync job
        # Otherwise, create a new one (backward compatibility)
        if sync_id:
            logger.info(f"Using existing sync job: {sync_id}")
            sync_job = self.sync_service.sync_supervisor_feedback(
                is_full_sync=is_full_sync,
                existing_sync_id=sync_id
            )
        else:
            # Old behavior: create sync job inside task
            sync_job = self.sync_service.sync_supervisor_feedback(is_full_sync=is_full_sync)
        
        # Extract attributes IMMEDIATELY after sync returns
        sync_id = str(sync_job.sync_id)
        status = sync_job.status
        sync_type = sync_job.sync_type
        error_count = sync_job.error_count or 0
        
        # Access JSONB field immediately - THIS is where all metrics are stored
        sync_metadata = sync_job.sync_metadata or {}
        
        # Extract top-level metrics from sync_metadata
        records_queried = sync_metadata.get('records_queried', 0)
        records_synced = sync_metadata.get('records_synced', 0)
        
        # Extract the nested "metrics" key which contains processor-specific metrics
        processor_metrics = sync_metadata.get('metrics', {})
        
        # Extract supervisor feedback specific metrics
        forms_created = processor_metrics.get('forms_created', 0)
        forms_updated = processor_metrics.get('forms_updated', 0)
        responses_created = processor_metrics.get('responses_created', 0)
        metric_definitions_created = processor_metrics.get('metric_definitions_created', 0)
        
        # Build log message
        metrics_log = f"Completed supervisor feedback sync {sync_id}: " \
                      f"{records_synced}/{records_queried} rows synced, " \
                      f"{error_count} errors"
        
        if forms_created or forms_updated or responses_created:
            metrics_log += f", {forms_created} forms created, " \
                          f"{forms_updated} forms updated, " \
                          f"{responses_created} responses created, " \
                          f"{metric_definitions_created} metric definitions created"
        
        logger.info(metrics_log)
        
        # Return dictionary for Celery (NO TIMESTAMPS)
        return {
            "sync_id": sync_id,
            "status": status,
            "sync_type": sync_type,
            "records_queried": records_queried,
            "records_synced": records_synced,
            "error_count": error_count,
            "metrics": {
                "forms_created": forms_created,
                "forms_updated": forms_updated,
                "responses_created": responses_created,
                "metric_definitions_created": metric_definitions_created
            }
        }
        
    except Exception as e:
        logger.error(f"Error in supervisor feedback sync task: {str(e)}", exc_info=True)
        raise

@shared_task(bind=True, base=SyncTask, name="sync.full")
def full_sync_task(self, employee_sync_id: Optional[str] = None, vision_sync_id: Optional[str] = None, jd_sync_id: Optional[str] = None, sf_sync_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run employee reports, vision data, job descriptions, and supervisor feedback syncs in sequence (full mode).
    
    REFACTORED: Calls sync service methods DIRECTLY (no subtask orchestration).
    This eliminates the .apply().get() anti-pattern and ensures sequential execution.
    
    Args:
        employee_sync_id: Optional sync_id for employee reports (if created by API)
        vision_sync_id: Optional sync_id for vision data (if created by API)
        jd_sync_id: Optional sync_id for job descriptions (if created by API)
        sf_sync_id: Optional sync_id for supervisor feedback (if created by API)
    
    Returns:
        Dictionary containing aggregated results from all four syncs
    """
    logger.info("Starting full sync task (employee reports, vision data, job descriptions, and supervisor feedback)")
    
    try:
        # Step 1: Call employee reports sync service DIRECTLY
        logger.info("Step 1: Syncing employee reports...")
        employee_sync_job = self.sync_service.sync_employee_reports(
            is_full_sync=True,
            existing_sync_id=employee_sync_id
        )
        
        # Extract employee results immediately
        employee_result = {
            "sync_id": str(employee_sync_job.sync_id),
            "status": employee_sync_job.status,
            "sync_type": employee_sync_job.sync_type,
            "records_queried": employee_sync_job.records_queried or 0,  # ← Read from column, not JSONB
            "records_synced": employee_sync_job.records_synced or 0,    # ← Read from column, not JSONB
            "error_count": employee_sync_job.error_count or 0,
            "metrics": employee_sync_job.sync_metadata or {}            # ← This is correct (processor metrics)
        }
        
        logger.info(f"Employee reports sync completed: {employee_result['records_synced']} records")
        
        # Step 2: Call vision data sync service DIRECTLY (sequential)
        logger.info("Step 2: Syncing vision data...")
        vision_sync_job = self.sync_service.sync_vision_data(
            is_full_sync=True,
            existing_sync_id=vision_sync_id
        )
        
        # Extract vision results immediately
        vision_result = {
            "sync_id": str(vision_sync_job.sync_id),
            "status": vision_sync_job.status,
            "sync_type": vision_sync_job.sync_type,
            "records_queried": vision_sync_job.records_queried or 0,  # ← Read from column
            "records_synced": vision_sync_job.records_synced or 0,    # ← Read from column
            "error_count": vision_sync_job.error_count or 0,
            "metrics": vision_sync_job.sync_metadata or {}
        }
        
                
        # Step 3: Call job descriptions sync service DIRECTLY (sequential)
        logger.info("Step 3: Syncing job descriptions...")
        jd_sync_job = self.sync_service.sync_job_descriptions(
            is_full_sync=True,
            existing_sync_id=jd_sync_id
        )
        
        # Extract JD results immediately
        jd_result = {
            "sync_id": str(jd_sync_job.sync_id),
            "status": jd_sync_job.status,
            "sync_type": jd_sync_job.sync_type,
            "records_queried": jd_sync_job.records_queried or 0,
            "records_synced": jd_sync_job.records_synced or 0,
            "error_count": jd_sync_job.error_count or 0,
            "metrics": jd_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Job descriptions sync completed: {jd_result['records_synced']} records")

        logger.info(f"Vision data sync completed: {vision_result['records_synced']} records")
        
        # Step 4: Call supervisor feedback sync service DIRECTLY (sequential)
        logger.info("Step 4: Syncing supervisor feedback...")
        sf_sync_job = self.sync_service.sync_supervisor_feedback(
            is_full_sync=True,
            existing_sync_id=sf_sync_id
        )
        
        # Extract supervisor feedback results immediately
        sf_result = {
            "sync_id": str(sf_sync_job.sync_id),
            "status": sf_sync_job.status,
            "sync_type": sf_sync_job.sync_type,
            "records_queried": sf_sync_job.records_queried or 0,
            "records_synced": sf_sync_job.records_synced or 0,
            "error_count": sf_sync_job.error_count or 0,
            "metrics": sf_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Supervisor feedback sync completed: {sf_result['records_synced']} records")
        
        # Step 5: Aggregate results
        total_records = (
            employee_result['records_synced'] + 
            vision_result['records_synced'] + 
            jd_result['records_synced'] +
            sf_result['records_synced']
        )
        total_errors = (
            employee_result['error_count'] + 
            vision_result['error_count'] + 
            jd_result['error_count'] +
            sf_result['error_count']
        )
        logger.info(f"Full sync completed: {total_records} total records synced, {total_errors} total errors")
        
        return {
            "sync_type": "full",
            "employee_reports": employee_result,
            "vision_data": vision_result,
            "job_descriptions": jd_result,
            "supervisor_feedback": sf_result,
            "total_records_synced": total_records,
            "total_errors": total_errors
        }
        
    except Exception as e:
        logger.error(f"Error in full sync task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, base=SyncTask, name="sync.incremental")
def incremental_sync_task(self) -> Dict[str, Any]:
    """
    Run employee reports, vision data, and job descriptions syncs in sequence (incremental mode).
    
    REFACTORED: Calls sync service methods DIRECTLY (no subtask orchestration).
    This eliminates the .apply().get() anti-pattern and ensures sequential execution.
    
    Sync order: Employee Reports → Vision Data → Job Descriptions → Supervisor Feedback.
    
    Returns:
        Dictionary containing aggregated results from all four syncs
    """
    logger.info("Starting incremental sync task (employee reports, vision data, job descriptions, and supervisor feedback)")
    
    try:
        # Step 1: Call employee reports sync service DIRECTLY
        logger.info("Step 1: Syncing employee reports (incremental)...")
        employee_sync_job = self.sync_service.sync_employee_reports(
            is_full_sync=False,
            existing_sync_id=None  # Let service create sync_id
        )
        
        # Extract employee results immediately
        employee_result = {
            "sync_id": str(employee_sync_job.sync_id),
            "status": employee_sync_job.status,
            "sync_type": employee_sync_job.sync_type,
            "records_queried": employee_sync_job.records_queried or 0,  # ← Read from column
            "records_synced": employee_sync_job.records_synced or 0,    # ← Read from column
            "error_count": employee_sync_job.error_count or 0,
            "metrics": employee_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Employee reports sync completed: {employee_result['records_synced']} records")
        
        # Step 2: Call vision data sync service DIRECTLY (sequential)
        logger.info("Step 2: Syncing vision data (incremental)...")
        vision_sync_job = self.sync_service.sync_vision_data(
            is_full_sync=False,
            existing_sync_id=None  # Let service create sync_id
        )
        
        # Extract vision results immediately
        vision_result = {
            "sync_id": str(vision_sync_job.sync_id),
            "status": vision_sync_job.status,
            "sync_type": vision_sync_job.sync_type,
            "records_queried": vision_sync_job.records_queried or 0,  
            "records_synced": vision_sync_job.records_synced or 0,    
            "error_count": vision_sync_job.error_count or 0,
            "metrics": vision_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Vision data sync completed: {vision_result['records_synced']} records")
        
                
        # Step 3: Call job descriptions sync service DIRECTLY (sequential)
        logger.info("Step 3: Syncing job descriptions (incremental)...")
        jd_sync_job = self.sync_service.sync_job_descriptions(
            is_full_sync=False,
            existing_sync_id=None  # Let service create sync_id
        )
        
        # Extract JD results immediately
        jd_result = {
            "sync_id": str(jd_sync_job.sync_id),
            "status": jd_sync_job.status,
            "sync_type": jd_sync_job.sync_type,
            "records_queried": jd_sync_job.records_queried or 0,
            "records_synced": jd_sync_job.records_synced or 0,
            "error_count": jd_sync_job.error_count or 0,
            "metrics": jd_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Job descriptions sync completed: {jd_result['records_synced']} records")


        # Step 4: Call supervisor feedback sync service DIRECTLY (sequential)
        logger.info("Step 4: Syncing supervisor feedback (incremental)...")
        sf_sync_job = self.sync_service.sync_supervisor_feedback(
            is_full_sync=False,
            existing_sync_id=None  # Let service create sync_id
        )
        
        # Extract supervisor feedback results immediately
        sf_result = {
            "sync_id": str(sf_sync_job.sync_id),
            "status": sf_sync_job.status,
            "sync_type": sf_sync_job.sync_type,
            "records_queried": sf_sync_job.records_queried or 0,
            "records_synced": sf_sync_job.records_synced or 0,
            "error_count": sf_sync_job.error_count or 0,
            "metrics": sf_sync_job.sync_metadata or {}
        }
        
        logger.info(f"Supervisor feedback sync completed: {sf_result['records_synced']} records")

        # Step 5: Aggregate results
        total_records = (
            employee_result['records_synced'] + 
            vision_result['records_synced'] + 
            jd_result['records_synced'] +
            sf_result['records_synced']
        )
        total_errors = (
            employee_result['error_count'] + 
            vision_result['error_count'] + 
            jd_result['error_count'] +
            sf_result['error_count']
        )
        logger.info(f"Incremental sync completed: {total_records} total records synced, {total_errors} total errors")
        
        return {
            "sync_type": "incremental",
            "employee_reports": employee_result,
            "vision_data": vision_result,
            "job_descriptions": jd_result,
            "supervisor_feedback": sf_result,
            "total_records_synced": total_records,
            "total_errors": total_errors
        }
        
    except Exception as e:
        logger.error(f"Error in incremental sync task: {str(e)}", exc_info=True)
        raise

