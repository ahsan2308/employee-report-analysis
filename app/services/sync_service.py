"""
Sync Service

Main orchestrator for SQL Server to PostgreSQL data synchronization.
Coordinates SQL Server queries, data transformation, and processing through existing CSV import pipeline.
"""
from typing import Any, Callable, Dict, NamedTuple, Optional
from contextlib import contextmanager
import pandas as pd
from datetime import timedelta  # Add to imports at top

from app.integrations.sqlserver.connector import SQLServerConnector, create_sqlserver_connector
from app.services.sync.transformers import EmployeeReportTransformer, VisionDataTransformer, JobDescriptionTransformer, SupervisorFeedbackTransformer
from app.services.sync.sync_tracker import SyncTracker
from app.services.csv.row_processor import RowProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.core import settings
from app.core.logger import logger
from app.db.database import get_database


class _SyncSpec(NamedTuple):
    """What differs between the sync_* methods."""
    sync_type: SyncType
    label: str
    table_name_method: str
    process_batches_method: str
    max_modified_date_attribute: str  # set by the batch processor
    order_by: Callable[[str], str]  # timestamp column -> ORDER BY
    status_metrics: Callable[[Dict[str, Any]], Dict[str, Any]]  # processor metrics -> sync status metrics


_EMPLOYEE_REPORTS = _SyncSpec(
    sync_type=SyncType.EMPLOYEE_REPORTS,
    label="employee reports",
    table_name_method="_get_employee_reports_table_name",
    process_batches_method="_process_employee_report_batches_bulk",
    max_modified_date_attribute="_max_modified_date",
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('employees_created', 0) + m.get('reports_created', 0),
        "records_updated": m.get('employees_updated', 0) + m.get('reports_updated', 0),
    },
)
_VISION_DATA = _SyncSpec(
    sync_type=SyncType.VISION_DATA,
    label="vision data",
    table_name_method="_get_vision_data_table_name",
    process_batches_method="_process_vision_data_batches_bulk",
    max_modified_date_attribute="_max_modified_date_vision",
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('vision_records_created', 0),
        "records_updated": m.get('vision_records_updated', 0),
    },
)
_JOB_DESCRIPTIONS = _SyncSpec(
    sync_type=SyncType.JOB_DESCRIPTIONS,
    label="job descriptions",
    table_name_method="_get_job_descriptions_table_name",
    process_batches_method="_process_job_description_batches_bulk",
    max_modified_date_attribute="_max_modified_date_jd",
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('jd_records_created', 0),
        "records_updated": m.get('jd_records_updated', 0),
    },
)
_SUPERVISOR_FEEDBACK = _SyncSpec(
    sync_type=SyncType.SUPERVISOR_FEEDBACK,
    label="supervisor feedback",
    table_name_method="_get_supervisor_feedback_table_name",
    process_batches_method="_process_supervisor_feedback_batches_bulk",
    max_modified_date_attribute="_max_modified_date_sf",
    # Rows of one form must stay in one batch, so order by form first
    order_by=lambda timestamp_col: 'RO_Form_ID, ' + timestamp_col,
    status_metrics=lambda m: {
        "forms_created": m.get('forms_created', 0),
        "forms_updated": m.get('forms_updated', 0),
        "responses_created": m.get('responses_created', 0),
        "metric_definitions_created": m.get('metric_definitions_created', 0),
    },
)


class SyncService:
    """
    Orchestrates SQL Server to PostgreSQL synchronization.
    
    Design:
    - Queries SQL Server for new/updated records in batches
    - Transforms SQL Server types → Pydantic-compatible format
    - Converts batches to pandas DataFrames
    - Delegates to existing RowProcessor.process_dataframe() for BULK validation/processing
    - Tracks sync progress via SyncTracker
    
    Reuses 100% of CSV import validation and processing logic.
    """
    
    def __init__(self, sqlserver_connector: SQLServerConnector, error_threshold_percent: float = 10.0):
        """
        Initialize sync service.
        
        Args:
            sqlserver_connector: SQL Server connector instance
            error_threshold_percent: Maximum percentage of errors before aborting (default: 10.0)
        """
        self.db_instance = get_database()  
        self.sqlserver_connector = sqlserver_connector
        self.sync_tracker = SyncTracker(self.db_instance)
        self.error_threshold_percent = error_threshold_percent
    
    @contextmanager
    def _sync_session_context(self):
        """Create a dedicated session for sync operations."""
        session = self.db_instance.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _get_employee_reports_table_name(self) -> str:
        """
        Dynamically find the employee reports table name from allowed tables.
        
        Returns:
            Table name for employee reports
            
        Raises:
            ValueError: If no suitable table is found
        """
        allowed_tables = self.sqlserver_connector.get_allowed_tables()
        
        # Look for table containing "EmployeeReports" (case-insensitive)
        for table in allowed_tables:
            if 'employeereports' in table.lower() or 'report' in table.lower():
                return table
        
        raise ValueError(f"No employee reports table found in allowed tables: {allowed_tables}")
    
    def _get_vision_data_table_name(self) -> str:
        """
        Dynamically find the vision data table name from allowed tables.
        
        Returns:
            Table name for vision data
            
        Raises:
            ValueError: If no suitable table is found
        """
        allowed_tables = self.sqlserver_connector.get_allowed_tables()
        
        # Look for table containing "VisionEmployeeData" or "Vision" (case-insensitive)
        for table in allowed_tables:
            table_lower = table.lower()
            if 'visionemployeedata' in table_lower or 'vision' in table_lower:
                return table
        
        raise ValueError(f"No vision data table found in allowed tables: {allowed_tables}")

    def _get_job_descriptions_table_name(self) -> str:
        """
        Dynamically find the job descriptions table name from allowed tables.
        
        Returns:
            Table name for job descriptions
            
        Raises:
            ValueError: If no suitable table is found
        """
        allowed_tables = self.sqlserver_connector.get_allowed_tables()
        
        # Look for table containing "JobDescriptions" or "JD" (case-insensitive)
        for table in allowed_tables:
            table_lower = table.lower()
            if 'jobdescriptions' in table_lower or 'jobdescription' in table_lower or 'jd' in table_lower or 'job' in table_lower:
                return table
        
        raise ValueError(f"No job descriptions table found in allowed tables: {allowed_tables}")
    
    def _get_supervisor_feedback_table_name(self) -> str:
        """
        Dynamically find the supervisor feedback table name from allowed tables.
        
        Returns:
            Table name for supervisor feedback
            
        Raises:
            ValueError: If no suitable table is found
        """
        allowed_tables = self.sqlserver_connector.get_allowed_tables()
        
        # Look for table containing "SupervisorFeedback" or "Supervisor" (case-insensitive)
        for table in allowed_tables:
            table_lower = table.lower()
            if 'supervisorfeedback' in table_lower or 'supervisor' in table_lower or 'feedback' in table_lower:
                return table
        
        raise ValueError(f"No supervisor feedback table found in allowed tables: {allowed_tables}")
    
    def _save_collected_errors(self, sync_id, error_handler, session) -> None:
        """Store the row errors an ImportErrorHandler collected, if there are any."""
        if error_handler.get_error_count() > 0:
            errors = [
                {
                    "row_number": err.row_number,
                    "field_name": err.field_name,
                    "error_message": err.error_message,
                    "row_data": err.row_data
                }
                for err in error_handler.errors
            ]
            self.sync_tracker.save_sync_errors(sync_id, errors, session=session)

    def _run_sync(self, spec: "_SyncSpec", is_full_sync: bool, existing_sync_id: Optional[str]) -> SyncHistory:
        """
        Sync one table from SQL Server to PostgreSQL (shared by the sync_* methods).

        Algorithm:
        1. Create sync job (or use the one the API endpoint created)
        2. Determine sync mode (full vs incremental)
        3. Query SQL Server (with timestamp filter for incremental)
        4. Process the batches in bulk through the type's processor
        5. Track progress and errors
        6. Update sync status (COMPLETED/FAILED/PARTIAL)
        """
        table_name = getattr(self, spec.table_name_method)()
        logger.info(f"Using table '{table_name}' for {spec.label} sync")
        
        with self._sync_session_context() as session:
            sync_job = None
            error_handler = None
            try:
                # Step 1: Create or use existing sync job
                if existing_sync_id:
                    # Use existing sync job created by API endpoint
                    logger.info(f"Using existing sync job: {existing_sync_id}")
                    sync_job = session.query(SyncHistory).filter(
                        SyncHistory.sync_id == existing_sync_id
                    ).first()
                    
                    if not sync_job:
                        raise ValueError(f"Sync job {existing_sync_id} not found")
                else:
                    # Create new sync job (backward compatibility for Celery Beat)
                    sync_job = self.sync_tracker.create_sync_job(
                        sync_type=spec.sync_type,
                        is_full_sync=is_full_sync,
                        session=session
                    )
                
                # Step 2: Determine sync mode
                if is_full_sync:
                    last_sync_timestamp = None
                    logger.info(f"Starting FULL sync for {spec.label} (sync_id: {sync_job.sync_id})")
                else:
                    last_sync_timestamp = self.sync_tracker.get_last_successful_sync(
                        spec.sync_type,
                        session=session
                    )
                    if last_sync_timestamp is None:
                        logger.info("No previous sync found. Performing full sync.")
                        is_full_sync = True
                    else:
                        logger.info(f"Starting INCREMENTAL sync from {last_sync_timestamp}")
                
                # Step 3: Update status to RUNNING
                self.sync_tracker.update_sync_status(
                    sync_job.sync_id, 
                    SyncStatus.RUNNING,
                    session=session
                )
                
                # Get the actual timestamp column from the table schema
                schema = self.sqlserver_connector.get_table_schema(table_name)
                timestamp_col = self._find_timestamp_column(schema)
                
                if not timestamp_col:
                    raise ValueError(f"No valid timestamp column found in {table_name} table")
                
                logger.info(f"Using timestamp column '{timestamp_col}' for {table_name} sync")
                
                # Step 4: Query SQL Server using detected column
                order_by = spec.order_by(timestamp_col)
                if is_full_sync:
                    batches = self.sqlserver_connector.get_all_records(
                        table_name=table_name,
                        batch_size=settings.SYNC_BATCH_SIZE,
                        order_by=order_by
                    )
                else:
                    batches = self.sqlserver_connector.get_records_since(
                        table_name=table_name,
                        timestamp_column=timestamp_col,
                        since_timestamp=last_sync_timestamp,
                        batch_size=settings.SYNC_BATCH_SIZE,
                        order_by=order_by
                    )
                
                # Step 5: Create processors
                error_handler = ImportErrorHandler()
                row_processor = RowProcessor(session, error_handler)
                
                # Process batches using bulk operations
                successful, total = getattr(self, spec.process_batches_method)(
                    batches=batches,
                    sync_id=sync_job.sync_id,
                    row_processor=row_processor,
                    error_handler=error_handler,
                    timestamp_column=timestamp_col
                )
                
                # The newest source timestamp seen, set by the batch processor (for incremental sync)
                max_modified_date = getattr(self, spec.max_modified_date_attribute, None)
                
                # Step 6: Save errors if any
                self._save_collected_errors(sync_job.sync_id, error_handler, session)
                
                # Step 7: Determine final status
                if error_handler.get_error_count() > 0 and successful == 0:
                    final_status = SyncStatus.FAILED
                elif error_handler.get_error_count() > 0:
                    final_status = SyncStatus.PARTIAL
                else:
                    final_status = SyncStatus.COMPLETED
                
                # Step 8: Update final status with metrics
                processor_metrics = row_processor.get_metrics().get('metrics', {})
                self.sync_tracker.update_sync_status(
                    sync_id=sync_job.sync_id,
                    status=final_status,
                    metrics={
                        "records_queried": total,
                        "records_synced": successful,
                        **spec.status_metrics(processor_metrics),
                        "records_skipped": total - successful,
                        "error_count": error_handler.get_error_count(),
                        "metrics": processor_metrics,
                        "last_sync_timestamp": max_modified_date
                    },
                    session=session
                )
                
                # Explicitly flush to ensure changes are written
                session.flush()
                
                logger.info(f"{spec.label.capitalize()} sync completed: {successful}/{total} records synced")
                
                # Refresh AFTER flush to get the committed state
                session.refresh(sync_job)
                
                # Expunge so the object can be safely accessed after session closes
                session.expunge(sync_job)

                return sync_job
                
            except Exception as e:
                logger.error(f"{spec.label.capitalize()} sync failed: {str(e)}", exc_info=True)
                
                # Ensure sync_job exists before marking as failed
                if sync_job:
                    # Keep the row errors collected before the failure (e.g. the ones that triggered an abort)
                    if error_handler is not None:
                        self._save_collected_errors(sync_job.sync_id, error_handler, session)
                    self.sync_tracker.mark_sync_failed(
                        sync_job.sync_id, 
                        str(e),
                        session=session
                    )
                    
                    # Flush and refresh even on failure
                    session.flush()
                    session.refresh(sync_job)
                    session.expunge(sync_job)
                    
                    # Return the FAILED sync_job so caller can inspect it
                    return sync_job
                else:
                    # If sync_job was never created (very early failure), then raise
                    raise

    def sync_employee_reports(self, is_full_sync: bool = False, existing_sync_id: Optional[str] = None) -> SyncHistory:
        """
        Sync employee reports from SQL Server to PostgreSQL.
        
        Args:
            is_full_sync: If True, sync all records. If False, incremental sync.
            existing_sync_id: Optional sync_id if already created by API endpoint
            
        Returns:
            SyncHistory record with sync results
        """
        return self._run_sync(_EMPLOYEE_REPORTS, is_full_sync, existing_sync_id)
    
    def sync_vision_data(self, is_full_sync: bool = False, existing_sync_id: Optional[str] = None) -> SyncHistory:
        """
        Sync vision data from SQL Server to PostgreSQL using BULK processing.
        
        Args:
            is_full_sync: If True, sync all records. If False, incremental sync.
            existing_sync_id: Optional sync_id if already created by API endpoint
            
        Returns:
            SyncHistory record with sync results
        """
        return self._run_sync(_VISION_DATA, is_full_sync, existing_sync_id)

    def sync_job_descriptions(self, is_full_sync: bool = False, existing_sync_id: Optional[str] = None) -> SyncHistory:
        """
        Sync job descriptions from SQL Server to PostgreSQL.
        
        Args:
            is_full_sync: If True, sync all records. If False, incremental sync.
            existing_sync_id: Optional sync_id if already created by API endpoint
            
        Returns:
            SyncHistory record with sync results
        """
        return self._run_sync(_JOB_DESCRIPTIONS, is_full_sync, existing_sync_id)

    def sync_supervisor_feedback(self, is_full_sync: bool = False, existing_sync_id: Optional[str] = None) -> SyncHistory:
        """
        Sync supervisor feedback from SQL Server to PostgreSQL.
        
        Args:
            is_full_sync: If True, sync all records. If False, incremental sync.
            existing_sync_id: Optional sync_id if already created by API endpoint
            
        Returns:
            SyncHistory record with sync results
        """
        return self._run_sync(_SUPERVISOR_FEEDBACK, is_full_sync, existing_sync_id)

    def _find_timestamp_column(self, schema: dict) -> Optional[str]:
        """
        Find the first valid timestamp column in the schema.
        
        Uses the connector's allowed timestamp columns whitelist.
        
        Args:
            schema: Table schema dictionary
            
        Returns:
            Name of the timestamp column, or None if not found
        """
        allowed_cols = self.sqlserver_connector.get_allowed_timestamp_columns()
        
        for col_name in schema.keys():
            if col_name in allowed_cols:
                return col_name
        
        return None
    
    def _process_employee_report_batches_bulk(self, batches, sync_id, row_processor, 
                                             error_handler, timestamp_column: str) -> tuple[int, int]:
        """
        
        
        Process batches of employee report rows using BULK operations.
        
        OPTIMIZED: Converts SQL Server batch → DataFrame → process_dataframe()
        This routes through EmployeeReportProcessor._bulk_process_reports()
        which does bulk INSERT/UPDATE and batched vector store operations.
        
        Returns:
            Tuple of (successful_count, total_count)
        """
        successful = 0
        total = 0
        start_row = 1
        max_modified_date = None
        
        for batch in batches:
            if not batch:
                continue
            
            # Track maximum timestamp in this batch
            for sql_row in batch:
                if timestamp_column in sql_row and sql_row[timestamp_column]:
                    row_modified_date = sql_row[timestamp_column]
                    if max_modified_date is None or row_modified_date > max_modified_date:
                        max_modified_date = row_modified_date
            
            try:
                # Transform entire batch at once
                transformed_rows = []
                for sql_row in batch:
                    try:
                        pydantic_dict = EmployeeReportTransformer.transform(sql_row)
                        transformed_rows.append(pydantic_dict)
                    except Exception as e:
                        logger.warning(f"Failed to transform row in batch: {str(e)}")
                        # Add error for this row but continue with batch
                        error_handler.add_processing_error(
                            row_number=start_row + len(transformed_rows),
                            row_data=sql_row,
                            error_message=f"Transformation error: {str(e)}",
                            exception=e
                        )
                
                if not transformed_rows:
                    logger.warning("No rows to process after transformation")
                    total += len(batch)
                    continue
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(transformed_rows)
                
                # Use bulk processing via process_dataframe
                # This routes to EmployeeReportProcessor.process_dataframe()
                # which calls _bulk_process_reports() for bulk SQL and vector operations
                batch_successful, batch_total = row_processor.process_dataframe(
                    df=df,
                    start_row_number=start_row,
                    pre_cleaned=True  # Already transformed, no NaN cleaning needed
                )
                
                successful += batch_successful
                total += batch_total
                start_row += batch_total
                
                logger.info(f"Processed batch: {batch_successful}/{batch_total} successful (cumulative: {successful}/{total})")
                
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                # Record error for entire batch
                for i, sql_row in enumerate(batch):
                    error_handler.add_processing_error(
                        row_number=start_row + i,
                        row_data=sql_row,
                        error_message=f"Batch processing error: {str(e)}",
                        exception=e
                    )
                total += len(batch)
                start_row += len(batch)
            
            # Check error threshold
            should_abort, reason = error_handler.should_abort(
                total_rows=total,
                error_threshold_percent=self.error_threshold_percent,  
                stop_on_error=False
            )
            if should_abort:
                logger.warning(f"Aborting sync: {reason}")
                raise ValueError(f"Sync aborted: {reason}")
        
        # Store max_modified_date as instance attribute
        if max_modified_date:
            # Remove these debug logs in production:
            # logger.info(f"🔍 DEBUG: Original max_modified_date from records: {max_modified_date}")
            self._max_modified_date = max_modified_date + timedelta(milliseconds=1)
            # logger.info(f"🔍 DEBUG: After adding +1 millisecond: {self._max_modified_date}")
        else:
            # logger.info(f"🔍 DEBUG: No max_modified_date found (no records synced)")
            self._max_modified_date = None
        
        logger.info(f"Bulk processing completed: {successful}/{total} records synced")
        return successful, total
    
    def _process_vision_data_batches_bulk(self, batches, sync_id, row_processor, 
                                         error_handler, timestamp_column: str) -> tuple[int, int]:
        """
        Process batches of vision data rows using BULK operations.
        
        OPTIMIZED: Same as employee reports but uses VisionDataTransformer
        and routes through VisionDataProcessor._bulk_process_vision_data().
        
        Returns:
            Tuple of (successful_count, total_count)
        """
        successful = 0
        total = 0
        start_row = 1
        max_modified_date = None
        
        for batch in batches:
            if not batch:
                continue
            
            # Track maximum timestamp in this batch
            for sql_row in batch:
                if timestamp_column in sql_row and sql_row[timestamp_column]:
                    row_modified_date = sql_row[timestamp_column]
                    if max_modified_date is None or row_modified_date > max_modified_date:
                        max_modified_date = row_modified_date
            
            try:
                # Transform entire batch at once
                transformed_rows = []
                for sql_row in batch:
                    try:
                        pydantic_dict = VisionDataTransformer.transform(sql_row)
                        transformed_rows.append(pydantic_dict)
                    except Exception as e:
                        logger.warning(f"Failed to transform row in batch: {str(e)}")
                        error_handler.add_processing_error(
                            row_number=start_row + len(transformed_rows),
                            row_data=sql_row,
                            error_message=f"Transformation error: {str(e)}",
                            exception=e
                        )
                
                if not transformed_rows:
                    logger.warning("No rows to process after transformation")
                    total += len(batch)
                    continue
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(transformed_rows)
                
                # Use bulk processing via process_dataframe
                # This routes to VisionDataProcessor.process_dataframe()
                # which calls _bulk_process_vision_data() for bulk SQL operations
                batch_successful, batch_total = row_processor.process_dataframe(
                    df=df,
                    start_row_number=start_row,
                    pre_cleaned=True
                )
                
                successful += batch_successful
                total += batch_total
                start_row += batch_total
                
                logger.info(f"Processed batch: {batch_successful}/{batch_total} successful (cumulative: {successful}/{total})")
                
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                for i, sql_row in enumerate(batch):
                    error_handler.add_processing_error(
                        row_number=start_row + i,
                        row_data=sql_row,
                        error_message=f"Batch processing error: {str(e)}",
                        exception=e
                    )
                total += len(batch)
                start_row += len(batch)
            
            # Check error threshold
            should_abort, reason = error_handler.should_abort(
                total_rows=total,
                error_threshold_percent=self.error_threshold_percent,
                stop_on_error=False
            )
            if should_abort:
                logger.warning(f"Aborting sync: {reason}")
                raise ValueError(f"Sync aborted: {reason}")
        
        # Store max_modified_date as instance attribute
        # Add 1 MILLISECOND for SQL Server datetime precision
        if max_modified_date:
            self._max_modified_date_vision = max_modified_date + timedelta(milliseconds=1)
        else:
            self._max_modified_date_vision = None
        
        logger.info(f"Bulk processing completed: {successful}/{total} records synced")
        return successful, total

    @contextmanager
    def _session_context(self):
        """Create isolated session for sync operations."""
        session = self.db_instance.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _process_job_description_batches_bulk(self, batches, sync_id, row_processor, 
                                            error_handler, timestamp_column: str) -> tuple[int, int]:
        """
        Process batches of job description rows using BULK operations.
        
        Returns:
            Tuple of (successful_count, total_count)
        """
        successful = 0
        total = 0
        start_row = 1
        max_modified_date = None
        
        for batch in batches:
            if not batch:
                continue
            
            # Track maximum timestamp in this batch
            for sql_row in batch:
                if timestamp_column in sql_row and sql_row[timestamp_column]:
                    row_modified_date = sql_row[timestamp_column]
                    if max_modified_date is None or row_modified_date > max_modified_date:
                        max_modified_date = row_modified_date
            
            try:
                # Transform entire batch at once                
                transformed_rows = []
                for sql_row in batch:
                    try:
                        pydantic_dict = JobDescriptionTransformer.transform(sql_row)
                        transformed_rows.append(pydantic_dict)
                    except Exception as e:
                        logger.warning(f"Failed to transform row in batch: {str(e)}")
                        error_handler.add_processing_error(
                            row_number=start_row + len(transformed_rows),
                            row_data=sql_row,
                            error_message=f"Transformation error: {str(e)}",
                            exception=e
                        )
                
                if not transformed_rows:
                    logger.warning("No rows to process after transformation")
                    total += len(batch)
                    continue
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(transformed_rows)
                
                # Use bulk processing via process_dataframe
                batch_successful, batch_total = row_processor.process_dataframe(
                    df=df,
                    start_row_number=start_row,
                    pre_cleaned=True
                )
                
                successful += batch_successful
                total += batch_total
                start_row += batch_total
                
                logger.info(f"Processed batch: {batch_successful}/{batch_total} successful (cumulative: {successful}/{total})")
                
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                for i, sql_row in enumerate(batch):
                    error_handler.add_processing_error(
                        row_number=start_row + i,
                        row_data=sql_row,
                        error_message=f"Batch processing error: {str(e)}",
                        exception=e
                    )
                total += len(batch)
                start_row += len(batch)
            
            # Check error threshold
            should_abort, reason = error_handler.should_abort(
                total_rows=total,
                error_threshold_percent=self.error_threshold_percent,
                stop_on_error=False
            )
            if should_abort:
                logger.warning(f"Aborting sync: {reason}")
                raise ValueError(f"Sync aborted: {reason}")
        
        # Store max_modified_date as instance attribute
        if max_modified_date:
            self._max_modified_date_jd = max_modified_date + timedelta(milliseconds=1)
        else:
            self._max_modified_date_jd = None
        
        logger.info(f"Bulk processing completed: {successful}/{total} records synced")
        return successful, total

    def _process_supervisor_feedback_batches_bulk(self, batches, sync_id, row_processor, 
                                                error_handler, timestamp_column: str) -> tuple[int, int]:
        """
        Process batches of supervisor feedback rows using BULK operations.
        
        Returns:
            Tuple of (successful_count, total_count)
        """
        successful = 0
        total = 0
        start_row = 1
        max_modified_date = None
        
        for batch in batches:
            if not batch:
                continue
            
            # Track maximum timestamp in this batch
            for sql_row in batch:
                if timestamp_column in sql_row and sql_row[timestamp_column]:
                    row_modified_date = sql_row[timestamp_column]
                    if max_modified_date is None or row_modified_date > max_modified_date:
                        max_modified_date = row_modified_date
            
            try:
                # Transform entire batch at once                
                transformed_rows = []
                for sql_row in batch:
                    try:
                        pydantic_dict = SupervisorFeedbackTransformer.transform(sql_row)
                        transformed_rows.append(pydantic_dict)
                    except Exception as e:
                        logger.warning(f"Failed to transform row in batch: {str(e)}")
                        error_handler.add_processing_error(
                            row_number=start_row + len(transformed_rows),
                            row_data=sql_row,
                            error_message=f"Transformation error: {str(e)}",
                            exception=e
                        )
                
                if not transformed_rows:
                    logger.warning("No rows to process after transformation")
                    total += len(batch)
                    continue
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(transformed_rows)
                
                # Use bulk processing via process_dataframe
                batch_successful, batch_total = row_processor.process_dataframe(
                    df=df,
                    start_row_number=start_row,
                    pre_cleaned=True
                )
                
                successful += batch_successful
                total += batch_total
                start_row += batch_total
                
                logger.info(f"Processed batch: {batch_successful}/{batch_total} successful (cumulative: {successful}/{total})")
                
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                for i, sql_row in enumerate(batch):
                    error_handler.add_processing_error(
                        row_number=start_row + i,
                        row_data=sql_row,
                        error_message=f"Batch processing error: {str(e)}",
                        exception=e
                    )
                total += len(batch)
                start_row += len(batch)
            
            # Check error threshold
            should_abort, reason = error_handler.should_abort(
                total_rows=total,
                error_threshold_percent=self.error_threshold_percent,
                stop_on_error=False
            )
            if should_abort:
                logger.warning(f"Aborting sync: {reason}")
                raise ValueError(f"Sync aborted: {reason}")
        
        # Store max_modified_date as instance attribute
        if max_modified_date:
            self._max_modified_date_sf = max_modified_date + timedelta(milliseconds=1)
        else:
            self._max_modified_date_sf = None
        
        logger.info(f"Bulk processing completed: {successful}/{total} records synced")
        return successful, total


def create_sync_service(error_threshold_percent: float = None) -> SyncService:
    """
    Factory function to create SyncService from environment configuration.
    
    Returns:
        Configured SyncService instance
    """
    sqlserver_connector = create_sqlserver_connector()
    
    # Read from environment variable if not provided
    if error_threshold_percent is None:
        error_threshold_percent = settings.sync_error_threshold_percent()
    
    return SyncService(sqlserver_connector, error_threshold_percent=error_threshold_percent)
