"""
CSV Import Tasks

This module contains Celery tasks for processing CSV imports asynchronously.
"""
import os
import time
import tempfile
from typing import Dict, Any, Optional
from celery import shared_task, Task

from app.core.logger import logger
from app.worker.celery_app import celery_app
from app.database import get_database
from app.models.import_models import CSVImportJob, ImportStatus
from app.services.csv_import_service import get_csv_import_service, CSVImportService
from app.schemas.csv_import_schema import CSVImportOptions

class ImportTask(Task):
    """Base task class for import operations with error handling."""
    
    _db = None
    _import_service = None
    
    @property
    def db(self):
        """Get database session."""
        if self._db is None:
            self._db = get_database().create_session()
        return self._db
    
    @property
    def import_service(self):
        """Get CSV import service instance."""
        if self._import_service is None:
            self._import_service = get_csv_import_service()
        return self._import_service
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failures by updating job status."""
        job_id = kwargs.get('job_id') or (args[0] if args else None)
        if not job_id:
            logger.error(f"Task {task_id} failed but no job_id was found in args or kwargs")
            return
            
        try:
            # Get job directly from database to ensure we have latest state
            job = self.db.query(CSVImportJob).filter(CSVImportJob.job_id == job_id).first()
            if not job:
                logger.error(f"Could not find import job {job_id} when handling failure")
                return
                
            # Update job status if not already failed
            if job.status != ImportStatus.FAILED.value:
                job.status = ImportStatus.FAILED.value
                job.error_count = job.error_count + 1 if job.error_count else 1
                job.completed_at = time.time()
                self.db.commit()
                logger.info(f"Updated job {job_id} status to FAILED due to task error")
                
        except Exception as e:
            logger.error(f"Error handling task failure for job {job_id}: {str(e)}")
        finally:
            if self._db:
                self._db.close()
                self._db = None
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up resources after task completion."""
        if self._db:
            self._db.close()
            self._db = None
        self._import_service = None

# This decorator creates a Celery task that will be picked up by the worker
@shared_task(bind=True, base=ImportTask, name="csv_import.process")
def process_csv_import(self, job_id: str, file_path: Optional[str] = None, 
                      file_content: Optional[bytes] = None, filename: Optional[str] = None,
                      options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a CSV import file asynchronously as a Celery task.
    
    This task runs in a background worker process, separate from the web server.
    """
    logger.info(f"Starting CSV import task for job {job_id}")
    
    # Convert options dict to pydantic model if provided
    options_model = CSVImportOptions(**options) if options else None
    
    # Create a temporary file if we were given file_content
    temp_file = None
    
    try:
        # If we have file content but no file path, create a temporary file
        if file_content and not file_path:
            logger.info(f"Creating temporary file for uploaded content from '{filename}'")
            temp_fd, temp_path = tempfile.mkstemp(suffix='.csv')
            os.write(temp_fd, file_content)
            os.close(temp_fd)
            temp_file = temp_path
            file_path = temp_path
        
        if not file_path:
            raise ValueError("Either file_path or file_content must be provided")
            
        # Process the CSV file - this now returns a dictionary, not a SQLAlchemy object
        job_dict = self.import_service.process_csv_file(
            job_id=job_id,
            file_path=file_path,
            options=options_model
        )
        
        # Log results using dictionary access (not object properties)
        logger.info(
            f"Completed CSV import job {job_id}: "
            f"{job_dict['successful_rows']}/{job_dict['total_rows']} rows processed successfully, "
            f"{job_dict['error_count']} errors, "
            f"{job_dict['employees_created']} employees created, "
            f"{job_dict['reports_created']} reports created"
        )
        
        # Just return the dictionary directly
        return job_dict
        
    except Exception as e:
        logger.error(f"Error processing CSV import job {job_id}: {str(e)}", exc_info=True)
        raise
    
    finally:
        # Clean up temporary file if we created one
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_file}: {str(e)}")
