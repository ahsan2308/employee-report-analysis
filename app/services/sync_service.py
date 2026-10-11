"""
Sync Service

Main orchestrator for SQL Server to PostgreSQL data synchronization.
Coordinates SQL Server queries, data transformation, and processing through existing CSV import pipeline.
"""
from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple
from contextlib import contextmanager
import pandas as pd
from datetime import datetime, timedelta

from app.integrations.sqlserver.connector import SQLServerConnector, create_sqlserver_connector
from app.services.sync.transformers import EmployeeReportTransformer, VisionDataTransformer, JobDescriptionTransformer, SupervisorFeedbackTransformer
from app.services.sync.sync_tracker import SyncTracker
from app.services.csv.row_processor import RowProcessor
from app.services.csv.error_handler import ErrorCategory, ImportErrorHandler
from app.models.sync_models import SyncHistory, SyncType, SyncStatus
from app.core import settings
from app.repositories import sync_history
from app.core.logger import logger
from app.db.database import get_database


class _SyncSpec(NamedTuple):
    """What differs between the sync_* methods."""
    sync_type: SyncType
    label: str
    table_setting: str  # the app.core.settings name holding the source table
    transformer: Any  # SQL Server row -> row-model dict (app.services.sync.transformers)
    order_by: Callable[[str], str]  # timestamp column -> ORDER BY
    status_metrics: Callable[[Dict[str, Any]], Dict[str, Any]]  # processor metrics -> sync status metrics


_EMPLOYEE_REPORTS = _SyncSpec(
    sync_type=SyncType.EMPLOYEE_REPORTS,
    label="employee reports",
    table_setting="SQLSERVER_TABLE_EMPLOYEE_REPORTS",
    transformer=EmployeeReportTransformer,
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('employees_created', 0) + m.get('reports_created', 0),
        "records_updated": m.get('employees_updated', 0) + m.get('reports_updated', 0),
    },
)
_VISION_DATA = _SyncSpec(
    sync_type=SyncType.VISION_DATA,
    label="vision data",
    table_setting="SQLSERVER_TABLE_VISION_DATA",
    transformer=VisionDataTransformer,
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('vision_records_created', 0),
        "records_updated": m.get('vision_records_updated', 0),
    },
)
_JOB_DESCRIPTIONS = _SyncSpec(
    sync_type=SyncType.JOB_DESCRIPTIONS,
    label="job descriptions",
    table_setting="SQLSERVER_TABLE_JOB_DESCRIPTIONS",
    transformer=JobDescriptionTransformer,
    order_by=lambda timestamp_col: timestamp_col,
    status_metrics=lambda m: {
        "records_created": m.get('jd_records_created', 0),
        "records_updated": m.get('jd_records_updated', 0),
    },
)
# The supervisor feedback column that identifies a form
_FEEDBACK_FORM_ID_COLUMN = "RO_Form_ID"

_SUPERVISOR_FEEDBACK = _SyncSpec(
    sync_type=SyncType.SUPERVISOR_FEEDBACK,
    label="supervisor feedback",
    table_setting="SQLSERVER_TABLE_SUPERVISOR_FEEDBACK",
    transformer=SupervisorFeedbackTransformer,
    # Rows of one form must stay in one batch, so order by form first
    order_by=lambda timestamp_col: f"{_FEEDBACK_FORM_ID_COLUMN}, {timestamp_col}",
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
    
    def _source_table(self, spec: "_SyncSpec") -> str:
        """
        The SQL Server table a sync type reads, as configured in settings.

        SQL Server table names are case-insensitive, so the configured name
        matches an allowed table in any case; the allowed spelling is returned
        because the connector checks names exactly.
        """
        table_name = getattr(settings, spec.table_setting)
        allowed_tables = self.sqlserver_connector.get_allowed_tables()
        for allowed in allowed_tables:
            if allowed.lower() == table_name.lower():
                return allowed
        raise ValueError(
            f"The {spec.label} table '{table_name}' ({spec.table_setting}) is not in "
            f"SQLSERVER_ALLOWED_TABLES: {sorted(allowed_tables)}"
        )

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
        table_name = self._source_table(spec)
        logger.info(f"Using table '{table_name}' for {spec.label} sync")
        
        with self._sync_session_context() as session:
            sync_job = None
            error_handler = None
            try:
                # Step 1: Create or use existing sync job
                if existing_sync_id:
                    # Use existing sync job created by API endpoint
                    logger.info(f"Using existing sync job: {existing_sync_id}")
                    sync_job = sync_history.get_sync(session, existing_sync_id)
                    
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
                successful, total, next_sync_from = self._process_batches(
                    batches=batches,
                    transformer=spec.transformer,
                    row_processor=row_processor,
                    error_handler=error_handler,
                    timestamp_column=timestamp_col
                )
                
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
                        "last_sync_timestamp": next_sync_from
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
    
    def _process_batches(self, batches, transformer, row_processor, error_handler,
                         timestamp_column: str) -> Tuple[int, int, Optional[datetime]]:
        """
        Transform batches of SQL Server rows and save them in bulk.

        Each batch is transformed row by row, then saved through the row
        processor's process_dataframe, the same bulk path CSV imports use. Rows
        are numbered in the order SQL Server returned them.

        Returns (successful, total, next_sync_from). next_sync_from is where the
        next incremental sync starts reading (inclusive):
        - just after the newest timestamp seen, when every row was either saved
          or rejected as invalid data (correcting such a row at the source gives
          it a newer timestamp, so it is read again);
        - otherwise the oldest timestamp of the batches that left rows unsaved
          for another reason (a failed database or vector store write), so those
          rows are read again instead of being skipped for good;
        - None when no row had a timestamp.
        """
        successful = 0
        total = 0
        start_row = 1
        newest = None
        retry_from = None

        for batch in batches:
            if not batch:
                continue

            errors_before = len(error_handler.errors)
            timestamps = [row[timestamp_column] for row in batch
                          if isinstance(row, dict) and row.get(timestamp_column)]
            if timestamps:
                newest = max(timestamps) if newest is None else max(newest, *timestamps)

            positions, transformed_rows = [], []
            for position, sql_row in enumerate(batch):
                try:
                    transformed_rows.append(transformer.transform(sql_row))
                    positions.append(position)
                except Exception as e:
                    logger.warning(f"Failed to transform row in batch: {str(e)}")
                    error_handler.add_validation_error(
                        row_number=start_row + position,
                        row_data=sql_row,
                        error_message=f"Transformation error: {str(e)}"
                    )

            batch_successful = 0
            if transformed_rows:
                try:
                    # Indexed by position, so the processors number each row by its place in the batch
                    df = pd.DataFrame(transformed_rows, index=positions)
                    batch_successful, _ = row_processor.process_dataframe(
                        df=df,
                        start_row_number=start_row + positions[0],
                        pre_cleaned=True  # Already transformed, no NaN cleaning needed
                    )
                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    for position in positions:
                        error_handler.add_processing_error(
                            row_number=start_row + position,
                            row_data=batch[position],
                            error_message=f"Batch processing error: {str(e)}",
                            exception=e
                        )

            # Rows neither saved nor rejected as invalid data are read again by the next sync
            batch_errors = error_handler.errors[errors_before:]
            invalid_rows = {err.row_number for err in batch_errors if err.category == ErrorCategory.VALIDATION}
            left_unsaved = (any(err.category != ErrorCategory.VALIDATION for err in batch_errors)
                            or batch_successful + len(invalid_rows) < len(batch))
            if left_unsaved and timestamps:
                retry_from = min(timestamps) if retry_from is None else min(retry_from, *timestamps)

            successful += batch_successful
            total += len(batch)
            start_row += len(batch)
            logger.info(f"Processed batch: {batch_successful}/{len(batch)} successful (cumulative: {successful}/{total})")

            should_abort, reason = error_handler.should_abort(
                total_rows=total,
                error_threshold_percent=self.error_threshold_percent,
                stop_on_error=False
            )
            if should_abort:
                logger.warning(f"Aborting sync: {reason}")
                raise ValueError(f"Sync aborted: {reason}")

        logger.info(f"Bulk processing completed: {successful}/{total} records synced")
        if retry_from is not None:
            logger.warning(f"Some rows were not saved; the next incremental sync starts again from {retry_from}")
            return successful, total, retry_from
        # 1 millisecond past the newest row: SQL Server datetime precision
        return successful, total, (newest + timedelta(milliseconds=1) if newest else None)


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
