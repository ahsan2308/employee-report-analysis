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
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import logger
from app.repositories import import_jobs
from app.db.database import get_database
from app.services.csv.csv_reader import PandasCSVReader
from app.services.csv.row_processor import RowProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.models.import_models import CSVImportJob, ImportStatus, ImportError
from app.schemas.csv_import_schema import CSVImportOptions, CSVImportJobResponse

def import_job_response(job: CSVImportJob, error_count: int) -> Dict[str, Any]:
    """The API view of an import job; error_count is the number of stored ImportError rows."""
    total_rows = job.total_rows or 0
    processed_rows = job.processed_rows or 0
    percent_complete = round((processed_rows / total_rows) * 100, 1) if total_rows > 0 else 0.0
    return {
        "job_id": str(job.job_id),
        "filename": job.filename,
        "status": job.status,
        "csv_type": job.csv_type,
        "submitted_at": job.submitted_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "total_rows": total_rows,
        "processed_rows": processed_rows,
        "successful_rows": job.successful_rows or 0,
        "error_count": error_count,
        "metrics": job.metrics_json or {},
        "percent_complete": percent_complete,
        "estimated_time_remaining": None
    }


def list_import_jobs(session: Session,
                     status: Optional[str] = None,
                     csv_type: Optional[str] = None,
                     limit: int = 50,
                     offset: int = 0) -> List[Dict[str, Any]]:
    """Import jobs, newest first, counting errors the same way as get_import_job."""
    jobs = import_jobs.list_jobs(session, status=status, csv_type=csv_type, limit=limit, offset=offset)
    error_counts = import_jobs.error_counts(session, [job.job_id for job in jobs])
    return [import_job_response(job, error_counts.get(job.job_id, 0)) for job in jobs]


class CSVImportService:
    """
    Enhanced service for importing CSV data with pandas integration.
    """
    
    def __init__(self):
        """Initialize the service."""
        self.db_instance = get_database()
        # self.csv_reader = PandasCSVReader(chunk_size=1000)
    
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
                  metrics: Optional[Dict[str, Any]] = None,
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
            # Update core metrics
            job.processed_rows = metrics.get('processed_rows', job.processed_rows)
            job.successful_rows = metrics.get('successful_rows', job.successful_rows)
            
            # Store CSV type if provided
            if 'csv_type' in metrics and metrics['csv_type']:
                job.csv_type = metrics['csv_type']
            
            # Store detailed metrics in the JSON field
            if 'metrics' in metrics:
                job.metrics_json = metrics['metrics']
    
        if error_count is not None:
            # If error_count is explicitly provided, use it
            job.error_count = error_count
        elif status == ImportStatus.FAILED:
            # If status is FAILED and no error_count is provided, get the actual count from the database
            actual_error_count = import_jobs.count_errors(session, job.job_id)
            if actual_error_count > 0:
                job.error_count = actual_error_count
            elif job.error_count == 0:
                # If no errors in database but job failed, set to at least 1
                job.error_count = 1
                
        session.commit()

    def create_import_job(self, 
                     filename: str, 
                     options: Optional[CSVImportOptions] = None,
                     csv_type: Optional[str] = None) -> CSVImportJobResponse:
        """
        Create a new import job.
        
        Args:
            filename: Name of the CSV file
            options: Import options
            csv_type: Optional explicit CSV type (from CSVImportType enum)
            
        Returns:
            Pydantic model instance with all calculated fields
        """
        with self._transaction_context() as session:
            job = CSVImportJob(
                filename=filename,
                status=ImportStatus.PENDING.value,
                csv_type=csv_type,
                options=options.model_dump() if options else None
            )
            
            import_jobs.add_job(session, job)
            
            logger.info(f"Created import job {job.job_id} for file {filename}, type: {csv_type or 'auto-detect'}")
            
            job_dict = import_job_response(job, job.error_count or 0)
            
            # Create the Pydantic model from our dictionary
            return CSVImportJobResponse.model_validate(job_dict)
            
    def process_csv_file(self, 
                     job_id: str, 
                     file_path: Optional[str] = None,
                     file_obj: Optional[Union[BinaryIO, str]] = None,
                     options: Optional[CSVImportOptions] = None,
                     csv_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a CSV file with pandas optimization.
        
        Args:
            job_id: Unique identifier for the import job
            file_path: Optional path to the CSV file on disk
            file_obj: Optional file object containing CSV data
            options: Optional import options
            csv_type: Optional CSV type to override auto-detection
            
        Returns a dictionary of job attributes rather than the SQLAlchemy model to avoid session binding issues.
        """
        if not file_path and not file_obj:
            raise ValueError("Either file_path or file_obj must be provided")
        
        with self._transaction_context() as session:
            # Get the job
            job = import_jobs.get_job(session, job_id)
            if not job:
                raise ValueError(f"Import job {job_id} not found")
            
            # Set CSV type if provided
            if csv_type:
                job.csv_type = csv_type
                session.commit()
            
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
                # self.csv_reader._file_obj = self.csv_reader._get_file_obj(file_path, file_obj)
                
                # Create CSV reader with job-specific options
                # Extract delimiter and encoding from options
                delimiter = getattr(job_options, 'delimiter', None)
                encoding = getattr(job_options, 'encoding', None)
                chunk_size = getattr(job_options, 'chunk_size', 1000)
                
                # Create reader with these options
                csv_reader = PandasCSVReader(
                    chunk_size=chunk_size,
                    encoding=encoding,
                    delimiter=delimiter
                )
                
                logger.info(f"Created CSV reader for job {job_id} with delimiter={repr(delimiter)}, encoding={encoding}")
                
                # Initialize the CSV reader with our file
                csv_reader._file_obj = csv_reader._get_file_obj(file_path, file_obj)
                
                # Try to detect file encoding upfront for better error messages
                try:
                    detected_encoding = csv_reader._detect_encoding(file_path, file_obj)
                    logger.info(f"Detected encoding for {job.filename}: {detected_encoding}")
                except Exception as e:
                    logger.warning(f"Error detecting encoding: {str(e)}")
                
                try:
                    # Use CSV reader methods to count rows and get headers
                    total_rows = csv_reader.get_total_rows()
                    
                    job.total_rows = total_rows
                    session.commit()
                except UnicodeDecodeError as ude:
                    logger.error(f"Encoding error while counting rows: {str(ude)}")
                    raise ValueError(f"Cannot read file {job.filename}: encoding error. The file may not be in UTF-8 format.")
                
                # Process based on selected mode
                if processing_mode == "row_by_row":
                    logger.info(f"Using row-by-row processing mode for job {job.job_id}")
                    try:
                        # Pass delimiter and encoding to read_csv
                        csv_generator = csv_reader.read_csv(
                            file_path=file_path,
                            file_obj=file_obj,
                            encoding=encoding,
                            delimiter=delimiter
                        )
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
                    logger.info(f"Using bulk processing mode for job {job.job_id}")
                    try:
                        # Pass delimiter and encoding to read_dataframes
                        reader = csv_reader.read_dataframes(
                            file_path=file_path, 
                            file_obj=file_obj,
                            chunk_size=job_options.chunk_size,
                            encoding=encoding,
                            delimiter=delimiter
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
                    "csv_type": job_result.csv_type,
                    "submitted_at": job_result.submitted_at,
                    "started_at": job_result.started_at,
                    "completed_at": job_result.completed_at,
                    "total_rows": job_result.total_rows,
                    "processed_rows": job_result.processed_rows,
                    "successful_rows": job_result.successful_rows,
                    "error_count": job_result.error_count,
                    "metrics": job_result.metrics_json or {}
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
                    "csv_type": job.csv_type,
                    "submitted_at": job.submitted_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "total_rows": job.total_rows,
                    "processed_rows": job.processed_rows,
                    "successful_rows": job.successful_rows, 
                    "error_count": job.error_count,
                    "metrics": job.metrics_json or {}
                }
    
    def _calculate_processing_rate(self, processed_rows: int, total_time: float) -> float:
        """Calculate processing rate in rows per second.""" 
        return processed_rows / total_time if total_time > 0 else 0
        
    def _validate_row(self, row_data: Dict[str, Any], row_number: int, error_handler: ImportErrorHandler,
                      csv_type: Optional[str] = None) -> bool:
        """
        Validate a single row without processing it.
        
        Uses the factory pattern to determine which validator to use based on the CSV headers.
        """
        try:
            # Create a temporary row processor just for validation
            # Uses the job's CSV type, or detects it from the headers when none was chosen
            temp_processor = RowProcessor(self.db_instance.create_session(), error_handler, csv_type=csv_type)
            
            # Get the correct processor based on the headers in this row
            processor = temp_processor._get_processor(row_data=row_data)
            
            # Debug logging
            headers = list(row_data.keys())
            logger.debug(f"Validating row {row_number} with processor: {processor.__class__.__name__}")
            logger.debug(f"Row headers: {headers}")
            
            # Use a very simple check - just try to instantiate the model without DB operations
            # This is mimicking what the processor would do internally but without DB access
            for field_name, value in row_data.items():
                if pd.isna(value):
                    row_data[field_name] = None
                if value == '':
                    row_data[field_name] = None
                logger.debug(f"  Field '{field_name}': '{value}' (type: {type(value).__name__})")
            
            # Validate only: process_row would write to the database and the vector store
            return processor.validate_row(row_data, row_number)
            
        except Exception as e:
            # Log detailed error
            logger.warning(f"Validation error in row {row_number}: {str(e)}")
            
            error_handler.add_validation_error(
                row_number=row_number,
                error_message=str(e),
                row_data=row_data
            )
            return False
        finally:
            # Close the temporary session
            if 'temp_processor' in locals() and hasattr(temp_processor, 'db'):
                temp_processor.db.close()
        
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
        row_processor = RowProcessor(session, error_handler, csv_type=job.csv_type)
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
                    if self._validate_row(row_data, processed_rows, error_handler, csv_type=job.csv_type):
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
                    job.processed_rows = processed_rows
                    job.successful_rows = successful_rows
                    job.error_count = error_handler.get_error_count()
                    
                    # Set CSV type if determined
                    if 'csv_type' in metrics and metrics['csv_type']:
                        job.csv_type = metrics['csv_type']
                    
                    # Store type-specific metrics
                    if 'metrics' in metrics:
                        job.metrics_json = metrics['metrics']
                        
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
            
            metrics = {
                **row_processor.get_metrics(),
                # The service counts rows itself; most processors do not
                "processed_rows": processed_rows,
                "successful_rows": successful_rows,
            }
            
            self._update_job_status(
                session=session,
                job=job,
                status=status,
                metrics=metrics,
                error_count=error_handler.get_error_count()
            )
            return job
        except Exception as e:
            self._fail_job(session, job, error_handler, e)
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
        row_processor = RowProcessor(session, error_handler, csv_type=job.csv_type)
        start_time = time.time()
        
        try:
            for chunk_df in reader:
                current_chunk += 1
                chunk_start_row = processed_rows + 1
                
                # Log chunk info for debugging
                logger.info(f"Processing chunk {current_chunk} ({len(chunk_df)} rows)")
                if current_chunk == 1:
                    logger.info(f"Chunk columns: {list(chunk_df.columns)}")
                    logger.debug(f"First row of first chunk: {chunk_df.iloc[0].to_dict() if len(chunk_df) > 0 else 'empty'}")
                
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
                    for position, (_, row) in enumerate(chunk_df.iterrows()):
                        row_number = processed_rows + position + 1
                        if self._validate_row(row.to_dict(), row_number, error_handler, csv_type=job.csv_type):
                            successful_rows += 1
                
                processed_rows += len(chunk_df)
                
                # Check if we should abort
                should_abort, reason = error_handler.should_abort(
                    processed_rows, options.error_threshold_percent, options.stop_on_error
                )
                if should_abort:
                    # Add detailed error reporting before aborting
                    logger.warning(f"Aborting import: {reason}")
                    
                    # Better error diagnostics for early failures
                    if processed_rows <= 10:
                        logger.error(f"Import failed on or before row {processed_rows}. This suggests a fundamental format issue.")
                        errors = error_handler.get_errors()[:3]
                        for i, err in enumerate(errors):
                            logger.error(f"Error {i+1} (row {err.row_number}): {err.error_message}")
                            if hasattr(err, 'row_data') and err.row_data:
                                logger.error(f"  Row data fields: {list(err.row_data.keys())}")
                    
                    raise ValueError(f"Import aborted: {reason}")
                
                # Update job metrics
                metrics = row_processor.get_metrics()
                job.processed_rows = processed_rows
                job.successful_rows = successful_rows
                job.error_count = error_handler.get_error_count()
                
                # Set CSV type if determined
                if 'csv_type' in metrics and metrics['csv_type']:
                    job.csv_type = metrics['csv_type']
                
                # Store type-specific metrics
                if 'metrics' in metrics:
                    job.metrics_json = metrics['metrics']
                    
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
            
            metrics = {
                **row_processor.get_metrics(),
                # The service counts rows itself; most processors do not
                "processed_rows": processed_rows,
                "successful_rows": successful_rows,
            }
            
            self._update_job_status(
                session=session,
                job=job,
                status=status,
                metrics=metrics,
                error_count=error_handler.get_error_count()
            )
            return job
        except Exception as e:
            self._fail_job(session, job, error_handler, e)
            return job
    
    def _fail_job(self, session: Session, job: CSVImportJob, error_handler: ImportErrorHandler, exc: Exception) -> None:
        """
        Mark the job FAILED and save its errors.
        
        A failure with no row errors (e.g. the file's columns match no CSV type) is
        saved as one job-level error (row 0), so the job always says why it failed.
        """
        logger.error(f"Import failed: {str(exc)}\n{traceback.format_exc()}")
        if error_handler.get_error_count() == 0:
            error_handler.add_processing_error(row_number=0, error_message=str(exc), exception=exc)
        self._save_errors(session, job.job_id, error_handler)
        self._update_job_status(session, job, ImportStatus.FAILED)

    def _save_errors(self, session: Session, job_id: str, error_handler: ImportErrorHandler) -> None:
        """
        Save errors to the database and update job's error count.
        """
        error_models = error_handler.to_db_models(job_id)
        import_jobs.add_errors(session, error_models)
        
        # Update the job's error_count directly
        job = import_jobs.get_job(session, job_id)
        if job:
            # Get total error count for this job
            actual_error_count = import_jobs.count_errors(session, job_id)
            if job.error_count != actual_error_count:
                job.error_count = actual_error_count
                session.commit()
                logger.info(f"Updated job {job_id} error_count to {actual_error_count}")
        
        logger.info(f"Saved {len(error_models)} errors for job {job_id}")

    def mark_job_failed(self, job_id: str, message: str) -> None:
        """Mark a job FAILED with one job-level error (row 0), e.g. when its task could not be queued."""
        with self._transaction_context() as session:
            job = import_jobs.get_job(session, job_id)
            if not job:
                return
            import_jobs.add_errors(session, [ImportError(job_id=job.job_id, row_number=0, error_message=message)])
            self._update_job_status(session, job, ImportStatus.FAILED)

    def get_import_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get an import job by ID.
        
        Returns a dictionary of job attributes rather than the SQLAlchemy model to avoid session binding issues.
        """
        with self._transaction_context() as session:
            job = import_jobs.get_job(session, job_id)
            
            if not job:
                return None
            
            # Report the stored errors; reading a job never writes to it
            actual_error_count = import_jobs.count_errors(session, job_id)
            
            return import_job_response(job, actual_error_count)
        
    def get_job_errors(self, 
                     job_id: str, 
                     page: int = 1,   
                     page_size: int = 100) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get paginated errors for an import job.
        
        Returns a tuple of (total_count, list_of_error_dicts) to avoid session detachment issues.
        """
        with self._transaction_context() as session:
            
            total = import_jobs.count_errors(session, job_id)
            errors = import_jobs.page_errors(session, job_id, offset=(page - 1) * page_size, limit=page_size)
            

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
