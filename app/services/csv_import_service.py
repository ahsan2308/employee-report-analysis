"""
CSV Import Service with enhanced database handling.
"""
from typing import Dict, Any, List, Optional, BinaryIO, Union, Tuple
import os
import time
from datetime import datetime
import traceback
from contextlib import contextmanager
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import logger
from app.database import get_database
from app.services.csv.csv_reader import PandasCSVReader
from app.services.csv.row_processor import RowProcessor
from app.services.csv.error_handler import ImportErrorHandler, ErrorCategory
from app.services.vector_store_service import add_report_to_vector_store
from app.models.import_models import CSVImportJob, ImportStatus, ImportError
from app.schemas.csv_import_schema import CSVImportOptions, CSVImportJobResponse

class CSVImportService:
    """
    Enhanced service for importing CSV data with pandas integration.
    """
    
    def __init__(self):
        """Initialize the service."""
        self.db_instance = get_database()
        self.csv_reader = PandasCSVReader(chunk_size=1000)
    
    @contextmanager
    def _transaction_context(self, session=None):
        """Create a transaction context with better error handling."""
        session = session or self.db_instance.create_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database transaction error: {str(e)}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error in transaction: {str(e)}")
            raise
        finally:
            session.close()
    
    def _update_job_status(self, 
                          session: Session, 
                          job: CSVImportJob, 
                          status: ImportStatus, 
                          metrics: Optional[Dict[str, int]] = None,
                          error_count: Optional[int] = None) -> None:
        """
        Update the status and metrics of an import job.
        """
        job.status = status.value
        
        if status == ImportStatus.RUNNING and not job.started_at:
            job.started_at = datetime.now()
            
        if status in (ImportStatus.COMPLETED, ImportStatus.FAILED):
            job.completed_at = datetime.now()
            
        if metrics:
            job.employees_created = metrics.get('employees_created', job.employees_created)
            job.employees_updated = metrics.get('employees_updated', job.employees_updated)
            job.reports_created = metrics.get('reports_created', job.reports_created)
            job.reports_updated = metrics.get('reports_updated', job.reports_updated)
            job.processed_rows = metrics.get('processed_rows', job.processed_rows)
            job.successful_rows = metrics.get('successful_rows', job.successful_rows)
            
        if error_count is not None:
            job.error_count = error_count
            
        session.commit()
        
    def create_import_job(self, 
                         filename: str, 
                         options: Optional[CSVImportOptions] = None) -> CSVImportJobResponse:
        """
        Create a new import job.
        
        Returns a Pydantic model instance with all calculated fields handled automatically.
        """
        with self._transaction_context() as session:
            job = CSVImportJob(
                filename=filename,
                status=ImportStatus.PENDING.value,
                options=options.model_dump() if options else None
            )
            
            session.add(job)
            session.commit()
            session.refresh(job)
            
            logger.info(f"Created import job {job.job_id} for file {filename}")
            
            # Calculate percent_complete
            total_rows = job.total_rows or 0
            processed_rows = job.processed_rows or 0
            percent_complete = 0.0
            if total_rows > 0:
                percent_complete = round((processed_rows / total_rows) * 100, 1)
            
            # Convert to dictionary with explicit string conversions
            job_dict = {
                "job_id": str(job.job_id),  # Convert UUID to string
                "filename": job.filename,
                "status": job.status,
                "submitted_at": job.submitted_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "total_rows": job.total_rows or 0,
                "processed_rows": job.processed_rows or 0,
                "successful_rows": job.successful_rows or 0,
                "error_count": job.error_count or 0,
                "employees_created": job.employees_created or 0,
                "employees_updated": job.employees_updated or 0, 
                "reports_created": job.reports_created or 0,
                "reports_updated": job.reports_updated or 0,
                "percent_complete": percent_complete,
                "estimated_time_remaining": None
            }
            
            # Create the Pydantic model from our carefully prepared dictionary
            return CSVImportJobResponse.model_validate(job_dict)
            
    def process_csv_file(self, 
                         job_id: str, 
                         file_path: Optional[str] = None,
                         file_obj: Optional[Union[BinaryIO, str]] = None,
                         options: Optional[CSVImportOptions] = None) -> Dict[str, Any]:
        """
        Process a CSV file with pandas optimization.
        
        Returns a dictionary of job attributes rather than the SQLAlchemy model to avoid session binding issues.
        """
        if not file_path and not file_obj:
            raise ValueError("Either file_path or file_obj must be provided")
        
        with self._transaction_context() as session:
            # Get the job
            job = session.query(CSVImportJob).filter(CSVImportJob.job_id == job_id).first()
            if not job:
                raise ValueError(f"Import job {job_id} not found")
            
            # Get options
            if options:
                job_options = options
            elif job.options:
                job_options = CSVImportOptions(**job.options)
            else:
                job_options = CSVImportOptions()
            
            # Auto-select processing mode based on file size if enabled
            processing_mode = getattr(job_options, 'processing_mode', 'row_by_row')
            
            if hasattr(job_options, 'auto_mode_selection') and getattr(job_options, 'auto_mode_selection', False):
                threshold_mb = getattr(job_options, 'file_size_threshold_mb', 10.0)
                
                # For file paths, we can get the size directly
                if file_path:
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb > threshold_mb:
                        processing_mode = "row_by_row"
                        logger.info(f"Auto-selected row_by_row mode for large file ({file_size_mb:.1f} MB)")
                    else:
                        processing_mode = "bulk"
                        logger.info(f"Auto-selected bulk mode for smaller file ({file_size_mb:.1f} MB)")
                
                # For file objects, we need to estimate size if possible
                elif file_obj:
                    # Try to determine file size if file object supports it
                    try:
                        if hasattr(file_obj, 'seek') and hasattr(file_obj, 'tell'):
                            # Save current position
                            current_pos = file_obj.tell()
                            # Go to end of file
                            file_obj.seek(0, 2)  # 2 means end of file
                            # Get size
                            size = file_obj.tell()
                            # Go back to original position
                            file_obj.seek(current_pos)
                            
                            file_size_mb = size / (1024 * 1024)
                            
                            if file_size_mb > threshold_mb:
                                processing_mode = "row_by_row"
                                logger.info(f"Auto-selected row_by_row mode for large file object ({file_size_mb:.1f} MB)")
                            else:
                                processing_mode = "bulk"
                                logger.info(f"Auto-selected bulk mode for smaller file object ({file_size_mb:.1f} MB)")
                        else:
                            # Default to row_by_row for safety with unknown file objects
                            processing_mode = "row_by_row"
                            logger.info("Auto-selected row_by_row mode for file object of unknown size")
                    except Exception as e:
                        # If any error occurs during size detection, default to row_by_row
                        processing_mode = "row_by_row"
                        logger.info(f"Error detecting file object size: {str(e)}. Using row_by_row mode.")
            
            # Update job status to running
            self._update_job_status(session, job, ImportStatus.RUNNING)
            
            # Create error handler
            error_handler = ImportErrorHandler()
            
            try:
                # Initialize the CSV reader with our file
                self.csv_reader._file_obj = self.csv_reader._get_file_obj(file_path, file_obj)
                
                # Try to detect file encoding upfront for better error messages
                try:
                    encoding = self.csv_reader._detect_encoding(file_path, file_obj)
                    logger.info(f"Detected encoding for {job.filename}: {encoding}")
                except Exception as e:
                    logger.warning(f"Error detecting encoding: {str(e)}")
                
                try:
                    # Use existing CSV reader methods to count rows and get headers
                    total_rows = self.csv_reader.get_total_rows()
                    
                    job.total_rows = total_rows
                    session.commit()
                except UnicodeDecodeError as ude:
                    logger.error(f"Encoding error while counting rows: {str(ude)}")
                    raise ValueError(f"Cannot read file {job.filename}: encoding error. The file may not be in UTF-8 format.")
                
                # Process based on selected mode
                if processing_mode == "row_by_row":
                    # Use the CSV reader's generator approach
                    logger.info(f"Using row-by-row processing mode for job {job.job_id}")
                    try:
                        csv_generator = self.csv_reader.read_csv(file_path=file_path, file_obj=file_obj)
                        job_result = self._process_rows(
                            session=session,
                            job=job,
                            csv_generator=csv_generator,
                            error_handler=error_handler,
                            options=job_options
                        )
                    except UnicodeDecodeError as ude:
                        logger.error(f"Encoding error in row-by-row processing: {str(ude)}")
                        raise ValueError(f"Cannot process file {job.filename}: {str(ude)}")
                else:
                    # Use the bulk DataFrame approach with the CSV reader
                    logger.info(f"Using bulk processing mode for job {job.job_id}")
                    try:
                        reader = self.csv_reader.read_dataframes(
                            file_path=file_path, 
                            file_obj=file_obj,
                            chunk_size=job_options.chunk_size
                        )
                        job_result = self._process_with_pandas(
                            session=session,
                            job=job,
                            reader=reader,
                            error_handler=error_handler,
                            options=job_options
                        )
                    except UnicodeDecodeError as ude:
                        logger.error(f"Encoding error in bulk processing: {str(ude)}")
                        raise ValueError(f"Cannot process file {job.filename}: {str(ude)}")
                
                # Convert job to dictionary before returning
                return {
                    "job_id": str(job_result.job_id),
                    "filename": job_result.filename,
                    "status": job_result.status,
                    "submitted_at": job_result.submitted_at,
                    "started_at": job_result.started_at,
                    "completed_at": job_result.completed_at,
                    "total_rows": job_result.total_rows,
                    "processed_rows": job_result.processed_rows,
                    "successful_rows": job_result.successful_rows,
                    "error_count": job_result.error_count,
                    "employees_created": job_result.employees_created,
                    "employees_updated": job_result.employees_updated,
                    "reports_created": job_result.reports_created,
                    "reports_updated": job_result.reports_updated
                }
                
            except Exception as e:
                logger.error(f"Error processing CSV file: {str(e)}\n{traceback.format_exc()}")
                self._update_job_status(session, job, ImportStatus.FAILED)
                
                # Add more descriptive error handling for encoding issues
                if "codec can't decode byte" in str(e):
                    error_handler.add_processing_error(
                        row_number=0,
                        row_data=None,
                        error_message=f"Encoding error: The file {job.filename} appears to use a non-UTF-8 encoding. Try saving the file as UTF-8 in your spreadsheet program.",
                        exception=e
                    )
                    self._save_errors(session, job.job_id, error_handler)
                
                # Return dictionary for failed job too
                return {
                    "job_id": str(job.job_id),
                    "filename": job.filename,
                    "status": job.status,
                    "submitted_at": job.submitted_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "total_rows": job.total_rows,
                    "processed_rows": job.processed_rows,
                    "successful_rows": job.processed_rows,
                    "error_count": job.error_count,
                    "employees_created": job.employees_created,
                    "employees_updated": job.employees_updated,
                    "reports_created": job.reports_created,
                    "reports_updated": job.reports_updated
                }
    
    def _calculate_processing_rate(self, processed_rows: int, total_time: float) -> float:
        """Calculate processing rate in rows per second.""" 
        return processed_rows / total_time if total_time > 0 else 0
        
    def _validate_row(self, row_data: Dict[str, Any], row_number: int, error_handler: ImportErrorHandler) -> bool:
        """Validate a single row without processing it."""
        try:
            from app.schemas.csv_import_schema import CombinedCSVRow
            
            # Debug logging - Log the row data we're about to validate
            logger.debug(f"Validating row {row_number}: {row_data}")
            
            # Check specifically for date fields which often cause issues
            if 'From' in row_data:
                logger.debug(f"Row {row_number} - From date: '{row_data['From']}' (type: {type(row_data['From']).__name__})")
            if 'To' in row_data:
                logger.debug(f"Row {row_number} - To date: '{row_data['To']}' (type: {type(row_data['To']).__name__})")
            
            # Date format handling is now done in the Pydantic field validator
            # No need for manual preprocessing here
            
            # Now try to validate the row
            model = CombinedCSVRow(**row_data)
            logger.debug(f"Row {row_number} validated successfully")
            return True
        except Exception as e:
            # Log detailed error
            logger.warning(f"Validation error in row {row_number}: {str(e)}")
            
            # Add more debugging for specific fields
            for field in ['Name', 'Designation', 'From', 'To', 'Tasks_Completed', 'NTR']:
                if field in row_data:
                    logger.debug(f"  Field '{field}': '{row_data[field]}' (type: {type(row_data[field]).__name__})")
            
            error_handler.add_validation_error(
                row_number=row_number,
                error_message=str(e),
                row_data=row_data
            )
            return False
        
    def _log_completion_info(self, job_id: str, successful_rows: int, processed_rows: int, rate: float) -> None:
        """Log standard completion information."""
        logger.info(f"Completed import job {job_id}: {successful_rows}/{processed_rows} rows successful ({rate:.1f} rows/sec)")
        
    def _process_rows(self,
                     session: Session,
                     job: CSVImportJob,
                     csv_generator,
                     error_handler: ImportErrorHandler,
                     options: CSVImportOptions) -> CSVImportJob:
        """
        Process CSV rows one at a time using the generator approach.
        """
        dry_run = options.dry_run
        processed_rows = 0  
        successful_rows = 0
        last_update_time = time.time()
        update_interval = 1.0  # Update status every 1 second
        row_processor = RowProcessor(session, error_handler)
        start_time = time.time()
        
        try:
            # Process rows one by one
            for row_data in csv_generator:
                processed_rows += 1
                if not dry_run:
                    success = row_processor.process_row(row_data, processed_rows)
                    if success:
                        successful_rows += 1
                else:
                    # In dry run mode, just validate the data without processing
                    if self._validate_row(row_data, processed_rows, error_handler):
                        successful_rows += 1
                
                # Check if we should abort based on errors
                should_abort, reason = error_handler.should_abort(
                    processed_rows, options.error_threshold_percent, options.stop_on_error
                )
                if should_abort:
                    logger.warning(f"Aborting import: {reason}")
                    raise ValueError(f"Import aborted: {reason}")
                
                # Update metrics periodically to avoid excessive database updates
                current_time = time.time()
                if current_time - last_update_time > update_interval:
                    metrics = row_processor.get_metrics()
                    metrics['processed_rows'] = processed_rows
                    metrics['successful_rows'] = successful_rows
                    job.processed_rows = processed_rows
                    job.successful_rows = successful_rows
                    job.error_count = error_handler.get_error_count()
                    job.employees_created = metrics['employees_created']
                    job.employees_updated = metrics['employees_updated']
                    job.reports_created = metrics['reports_created']
                    job.reports_updated = metrics['reports_updated']
                    session.commit()
                    last_update_time = current_time
            
            total_time = time.time() - start_time
            rate = self._calculate_processing_rate(processed_rows, total_time)
            self._log_completion_info(job.job_id, successful_rows, processed_rows, rate)
            
            if error_handler.get_error_count() > 0:
                self._save_errors(session, job.job_id, error_handler)
            
            if error_handler.get_error_count() > 0 and successful_rows == 0:
                status = ImportStatus.FAILED
            else:
                status = ImportStatus.COMPLETED
            
            metrics = row_processor.get_metrics()
            metrics['processed_rows'] = processed_rows
            metrics['successful_rows'] = successful_rows
            
            self._update_job_status(
                session=session,
                job=job,
                status=status,
                metrics=metrics,
                error_count=error_handler.get_error_count()
            )
            return job
        except Exception as e:
            if error_handler.get_error_count() > 0:
                self._save_errors(session, job.job_id, error_handler)
            self._update_job_status(session, job, ImportStatus.FAILED)
            logger.error(f"Import failed: {str(e)}\n{traceback.format_exc()}")
            return job
    
    def _process_with_pandas(self,
                           session: Session,
                           job: CSVImportJob,
                           reader,  # pandas chunked dataframe reader
                           error_handler: ImportErrorHandler,
                           options: CSVImportOptions) -> CSVImportJob:
        """
        Process CSV data using pandas chunks with bulk operations.
        """
        dry_run = options.dry_run
        processed_rows = 0
        successful_rows = 0
        current_chunk = 0
        row_processor = RowProcessor(session, error_handler)
        start_time = time.time()
        
        try:
            for chunk_df in reader:
                current_chunk += 1
                chunk_start_row = processed_rows + 1
                logger.info(f"Processing chunk {current_chunk} ({len(chunk_df)} rows)")
                if not dry_run:
                    # Use bulk processing with pre-cleaned DataFrames
                    chunk_successful, chunk_total = row_processor.process_dataframe(
                        df=chunk_df,
                        start_row_number=chunk_start_row,
                        pre_cleaned=True
                    )
                    successful_rows += chunk_successful
                else:
                    # In dry run mode, use shared validation helper
                    for idx, row in chunk_df.iterrows():
                        row_number = processed_rows + idx + 1
                        if self._validate_row(row.to_dict(), row_number, error_handler):
                            successful_rows += 1
                
                processed_rows += len(chunk_df)
                
                # Check if we should abort
                should_abort, reason = error_handler.should_abort(
                    processed_rows, options.error_threshold_percent, options.stop_on_error
                )
                if should_abort:
                    # Add detailed error reporting before aborting
                    logger.warning(f"Aborting import: {reason}")
                    
                    # Collect and log a summary of errors to help debugging
                    logger.warning(f"Error summary: {error_handler.get_error_count()} errors in {processed_rows} rows")
                    
                    # Log the first few errors to help identify patterns
                    errors = error_handler.get_errors()[:5]  # Get up to 5 errors
                    for i, err in enumerate(errors):
                        logger.warning(f"Sample error {i+1}: {err.error_message}")
                        if hasattr(err, 'row_data') and err.row_data:
                            for field in ['From', 'To', 'Name', 'NTR', 'Tasks_Completed']:
                                if field in err.row_data:
                                    logger.warning(f"  Field '{field}': '{err.row_data.get(field)}'")
                    
                    # Now raise the exception
                    raise ValueError(f"Import aborted: {reason}")
                
                # Update job metrics
                metrics = row_processor.get_metrics()
                metrics['processed_rows'] = processed_rows
                metrics['successful_rows'] = successful_rows
                job.processed_rows = processed_rows
                job.successful_rows = successful_rows
                job.error_count = error_handler.get_error_count()
                job.employees_created += metrics['employees_created']
                job.employees_updated += metrics['employees_updated']
                job.reports_created += metrics['reports_created']
                job.reports_updated += metrics['reports_updated']
                session.commit()
            
            total_time = time.time() - start_time
            rate = self._calculate_processing_rate(processed_rows, total_time)
            self._log_completion_info(job.job_id, successful_rows, processed_rows, rate)
            
            if error_handler.get_error_count() > 0:
                self._save_errors(session, job.job_id, error_handler)
            
            if error_handler.get_error_count() > 0 and successful_rows == 0:
                status = ImportStatus.FAILED    
            else:
                status = ImportStatus.COMPLETED
            
            self._update_job_status(
                session=session,
                job=job,
                status=status,
                error_count=error_handler.get_error_count()
            )
            return job
        except Exception as e:
            if error_handler.get_error_count() > 0:
                self._save_errors(session, job.job_id, error_handler)
            self._update_job_status(session, job, ImportStatus.FAILED)
            logger.error(f"Import failed: {str(e)}\n{traceback.format_exc()}")
            return job
    
    def _save_errors(self, session: Session, job_id: str, error_handler: ImportErrorHandler) -> None:
        """
        Save errors to the database. 
        """
        error_models = error_handler.to_db_models(job_id)
        for error in error_models:
            session.add(error)
        session.commit()
        logger.info(f"Saved {len(error_models)} errors for job {job_id}")
        
    def get_import_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get an import job by ID.
        
        Returns a dictionary of job attributes rather than the SQLAlchemy model to avoid session binding issues.
        """
        with self._transaction_context() as session:
            job = session.query(CSVImportJob).filter(CSVImportJob.job_id == job_id).first()
            
            if not job:
                return None
            
            # Calculate percent_complete:
            total_rows = job.total_rows or 0
            processed_rows = job.processed_rows or 0
            percent_complete = 0.0
            if total_rows > 0:
                percent_complete = round((processed_rows / total_rows) * 100, 1)
            
            # Return a dictionary instead of the SQLAlchemy model
            return {
                "job_id": str(job.job_id),
                "filename": job.filename,
                "status": job.status, 
                "submitted_at": job.submitted_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "total_rows": job.total_rows or 0,
                "processed_rows": job.processed_rows or 0,
                "successful_rows": job.successful_rows or 0,
                "error_count": job.error_count or 0,
                "employees_created": job.employees_created or 0,
                "employees_updated": job.employees_updated or 0,
                "reports_created": job.reports_created or 0,
                "reports_updated": job.reports_updated or 0,
                "percent_complete": percent_complete,
                "estimated_time_remaining": None
            }
        
    def get_job_errors(self, 
                     job_id: str, 
                     page: int = 1,   
                     page_size: int = 100) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get paginated errors for an import job.
        
        Returns a tuple of (total_count, list_of_error_dicts) to avoid session detachment issues.
        """
        with self._transaction_context() as session:
            
            total = int(session.query(ImportError).filter(ImportError.job_id == job_id).count())
            offset = (page - 1) * page_size
            
            errors = session.query(ImportError).filter(
                ImportError.job_id == job_id
            ).order_by(
                ImportError.row_number
            ).offset(offset).limit(page_size).all()
            

            error_dicts = []
            for error in errors:
                error_dicts.append({
                    "error_id": error.error_id,
                    "job_id": str(error.job_id),
                    "row_number": error.row_number,
                    "field_name": error.field_name,
                    "error_message": error.error_message,
                    "row_data": error.row_data
                })
            
            return total, error_dicts

def get_csv_import_service() -> CSVImportService:
    """Get an instance of the CSV import service."""
    return CSVImportService()
