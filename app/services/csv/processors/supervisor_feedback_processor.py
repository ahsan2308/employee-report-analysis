"""
Supervisor Feedback Processor

Handles the transformation and processing of Supervisor Feedback CSV rows into database operations.
Supports both manual CSV imports and SQL Server sync operations.

Design:
- Groups denormalized rows (one per metric) into normalized 3-table structure
- Processes metric definitions → forms → responses in sequence
- Uses DELETE+INSERT strategy for responses (cleaner than individual upserts)
- Generates JSONB cache for form-level aggregations
"""
from typing import Dict, Any, Tuple, List, Set
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import delete, tuple_
from pydantic import ValidationError

from app.base.base_csv_processor import BaseCSVProcessor
from app.schemas.csv_import_schema import SupervisorFeedbackCSVRow
from app.models.db_models import (
    Employee, 
    SupervisorFeedbackForm, 
    SupervisorFeedbackMetricDefinition, 
    SupervisorFeedbackResponse
)
from app.services.csv.error_handler import ImportErrorHandler
from app.core.logger import logger


class SupervisorFeedbackProcessor(BaseCSVProcessor):
    """
    Processes supervisor feedback CSV rows into database operations.
    
    Design follows existing processor patterns with adaptations for 3-table normalized structure:
    - Employee existence validation BEFORE bulk processing
    - Groups denormalized rows by RO_Form_ID (variable metrics per form)
    - Bulk upsert for metric definitions (INSERT ... ON CONFLICT DO NOTHING)
    - Bulk upsert for forms (INSERT ... ON CONFLICT DO UPDATE)
    - DELETE+INSERT strategy for responses (cleaner than individual upserts)
    - Generates JSONB cache with metric aggregations
    - Tracks metrics (forms created/updated, responses created, metric definitions created)
    """
    
    # Required headers for supervisor feedback CSV format
    REQUIRED_HEADERS = [
        "L_RO_Form_Metric_ID", "RO_Form_ID", "Employee_ID", "Name",
        "From", "To", "Section_ID", "Section", "Metric_ID", "Metric_Title",
        "Instructions", "Metric_Type", "Possible_Values", "Value"
    ]
    
    def __init__(self, db: Session, error_handler: ImportErrorHandler):
        """Initialize the processor."""
        super().__init__(db, error_handler)
        self.forms_created = 0
        self.forms_updated = 0
        self.responses_created = 0
        self.metric_definitions_created = 0
        self._existing_employee_ids = None
    
    def _get_existing_employee_ids(self) -> Set[int]:
        """
        Get a set of existing employee IDs for validation.
        
        Caches results to avoid repeated queries within the same import.
        Pattern copied from VisionDataProcessor.
        
        Returns:
            Set of existing employee IDs
        """
        if self._existing_employee_ids is None:
            self._existing_employee_ids = set()
            
            # Query all employee IDs
            employee_ids = self.db.query(Employee.id).all()
            self._existing_employee_ids = {emp_id[0] for emp_id in employee_ids}
            
            logger.info(f"Cached {len(self._existing_employee_ids)} existing employee IDs for supervisor feedback validation")
                
        return self._existing_employee_ids
     
    def process_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """
        Process a single supervisor feedback CSV row.
        
        NOTE: Single-row processing is not ideal for supervisor feedback since each form
        requires multiple metric rows. This method is provided for API compatibility but will result
        in incomplete forms. Use process_dataframe() for proper bulk processing.
        
        Args:
            row_data: Row data from CSV
            row_number: Row number for error reporting (1-based)
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Validate row data using Pydantic model
            validated_data = SupervisorFeedbackCSVRow(**row_data)
            row_dict = validated_data.model_dump()
            
            # Check if employee exists
            employee_id = row_dict.get('Employee_ID')
            if employee_id not in self._get_existing_employee_ids():
                self.error_handler.add_validation_error(
                    row_number=row_number,
                    error_message=f"Employee ID {employee_id} does not exist",
                    field_name="Employee_ID",
                    row_data=row_data
                )
                return False
            
            # WARNING: Single-row processing creates incomplete forms
            # This is a limitation of the row-by-row API
            logger.warning(
                f"Processing individual supervisor feedback row {row_number}. "
                f"Form {row_dict.get('RO_Form_ID')} will be incomplete without all metric rows. "
                f"Use bulk CSV import for complete forms."
            )
            
            # Process metric definition
            self._upsert_metric_definition(row_dict)
            
            # Process form (will be incomplete)
            form = self._upsert_form(row_dict)
            
            # Process single response
            self._upsert_response(row_dict, form.id)
            
            # Regenerate cache (will be incomplete)
            self._regenerate_form_cache(form.id)
            
            self.db.commit()
            self.successful_rows += 1
            return True
            
        except ValidationError as e:
            # Handle validation errors from Pydantic
            self.error_handler.normalize_pydantic_errors(e, row_number, row_data)
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing supervisor feedback row {row_number}: {str(e)}")
            self.error_handler.add_processing_error(
                row_number=row_number,
                row_data=row_data,
                error_message=f"Unexpected error: {str(e)}",
                exception=e
            )
            return False
    
    def process_dataframe(self, df: pd.DataFrame, start_row_number: int = 1, pre_cleaned: bool = True) -> Tuple[int, int]:
        """
        Process a DataFrame of supervisor feedback rows in bulk.
        
        Algorithm:
        1. Validate all rows with Pydantic
        2. Filter for existing employees BEFORE bulk operations
        3. Group rows by RO_Form_ID (Multiple rows → 1 form)
        4. Process metric definitions in bulk (all unique metrics)
        5. Process forms in bulk (one per RO_Form_ID)
        6. Process responses in bulk (DELETE existing + INSERT new for each form)
        7. Generate caches for all forms
        
        Args:
            df: Pandas DataFrame with CSV data
            start_row_number: Starting row number for error reporting
            pre_cleaned: Whether the DataFrame has already been cleaned (NaN → None)
            
        Returns:
            Tuple of (successful_rows, total_rows)
        """
        if df.empty:
            return 0, 0
        
        # Track metrics
        total_rows = len(df)
        self.processed_rows += total_rows
        
        # Validate all rows with Pydantic
        validated_rows = []
        invalid_rows = []
        
        for idx, row in df.iterrows():
            row_number = start_row_number + idx
            try:
                validated_data = SupervisorFeedbackCSVRow(**row.to_dict())
                row_dict = validated_data.model_dump()
                validated_rows.append((row_number, row_dict))
            except ValidationError as e:
                self.error_handler.normalize_pydantic_errors(e, row_number, row.to_dict())
                invalid_rows.append(row_number)
        
        if not validated_rows:
            logger.warning("No valid rows to process after validation")
            return 0, total_rows
        
        # Check employee existence BEFORE bulk processing
        try:
            # Get set of existing employee IDs
            existing_employees = self._get_existing_employee_ids()
            
            # Filter out rows with non-existent employees BEFORE bulk processing
            valid_rows = []
            for row_number, row_dict in validated_rows:
                employee_id = row_dict.get('Employee_ID')
                if employee_id not in existing_employees:
                    self.error_handler.add_validation_error(
                        row_number=row_number,
                        error_message=f"Employee ID {employee_id} does not exist in database",
                        field_name="Employee_ID",
                        row_data=row_dict
                    )
                    invalid_rows.append(row_number)
                else:
                    valid_rows.append((row_number, row_dict))
            
            # If no valid rows after filtering, return early
            if not valid_rows:
                logger.warning("No valid rows remaining after employee validation")
                return 0, total_rows
            
            # Group rows by RO_Form_ID
            forms_by_id = self._group_rows_by_form(valid_rows)
            
            logger.info(f"Grouped {len(valid_rows)} rows into {len(forms_by_id)} forms")
            
            # Process all data in bulk
            bulk_success = self._bulk_process_supervisor_feedback(forms_by_id)
            
            if bulk_success:
                successful_rows = len(valid_rows)
                self.successful_rows += successful_rows
                logger.info(f"Successfully processed {successful_rows}/{total_rows} supervisor feedback rows")
            else:
                successful_rows = 0
            
            return successful_rows, total_rows
            
        except Exception as e:
            logger.error(f"Bulk supervisor feedback processing failed: {str(e)}")
            self.db.rollback()
            return 0, total_rows
    
    def _group_rows_by_form(self, validated_rows: List[Tuple[int, Dict[str, Any]]]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Group validated rows by RO_Form_ID.
        
        Each form should have multiple metric rows. Logs info for forms with unusual counts.
        
        Args:
            validated_rows: List of (row_number, row_dict) tuples
            
        Returns:
            Dictionary mapping RO_Form_ID to list of row dictionaries
        """
        forms = {}
        
        for row_number, row_dict in validated_rows:
            form_id = row_dict.get('RO_Form_ID')
            if form_id not in forms:
                forms[form_id] = []
            forms[form_id].append(row_dict)
        
        # Log info about form sizes (for monitoring, not as errors)
        for form_id, rows in forms.items():
            logger.debug(f"Form {form_id} has {len(rows)} metric rows")
        
        return forms
    
    def _bulk_process_supervisor_feedback(self, forms_by_id: Dict[int, List[Dict[str, Any]]]) -> bool:
        """
        Process supervisor feedback data in bulk.
        
        Strategy:
        1. Extract and upsert all unique metric definitions (INSERT ... ON CONFLICT DO NOTHING)
        2. Upsert all forms (INSERT ... ON CONFLICT DO UPDATE)
        3. For each form: DELETE existing responses + INSERT new responses
        4. Generate JSONB caches for all forms
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Process metric definitions
            self._bulk_process_metric_definitions(forms_by_id)
            
            # Step 2: Process forms
            form_id_map = self._bulk_process_forms(forms_by_id)
            
            # Step 3: Process responses (DELETE + INSERT for each form)
            self._bulk_process_responses(forms_by_id, form_id_map)
            
            # Step 4: Generate caches
            self._bulk_generate_caches(form_id_map)
            
            self.db.commit()
            logger.info(
                f"Bulk processing complete: "
                f"{self.forms_created} forms created, "
                f"{self.forms_updated} forms updated, "
                f"{self.responses_created} responses created, "
                f"{self.metric_definitions_created} metric definitions created"
            )
            return True
            
        except Exception as e:
            logger.error(f"Bulk supervisor feedback processing failed: {str(e)}")
            self.db.rollback()
            return False
    
    def _bulk_process_metric_definitions(self, forms_by_id: Dict[int, List[Dict[str, Any]]]) -> None:
        """
        Extract unique metric definitions from all forms and upsert in bulk.
        
        Uses INSERT ... ON CONFLICT DO NOTHING since metric definitions are immutable.
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        # Extract unique metric definitions
        unique_metrics = {}
        
        for form_id, rows in forms_by_id.items():
            for row in rows:
                metric_key = (row['Section_ID'], row['Metric_ID'])
                if metric_key not in unique_metrics:
                    # Count possible values to calculate max_value
                    possible_values = row.get('Possible_Values')
                    max_value = None
                    if possible_values and row['Metric_Type'] == 'R':
                        max_value = len([v.strip() for v in possible_values.split(',') if v.strip()])
                    
                    unique_metrics[metric_key] = {
                        'section_id': row['Section_ID'],
                        'section': row['Section'],
                        'metric_id': row['Metric_ID'],
                        'metric_name': row['Metric_Title'],
                        'metric_description': row.get('Instructions'),
                        'metric_type': row['Metric_Type'],
                        'possible_values': possible_values,
                        'max_value': max_value,
                        'created_at': datetime.now(timezone.utc)
                    }
        
        if not unique_metrics:
            logger.info("No metric definitions to process")
            return
        
        # Query existing metric definitions BEFORE upsert
        metric_keys = [(m['section_id'], m['metric_id']) for m in unique_metrics.values()]
        existing_metrics = self.db.query(
            SupervisorFeedbackMetricDefinition.section_id,
            SupervisorFeedbackMetricDefinition.metric_id
        ).filter(
            tuple_(
                SupervisorFeedbackMetricDefinition.section_id,
                SupervisorFeedbackMetricDefinition.metric_id
            ).in_(metric_keys)
        ).all()
        
        existing_set = {(section_id, metric_id) for section_id, metric_id in existing_metrics}
        new_count = len([m for m in unique_metrics.values() if (m['section_id'], m['metric_id']) not in existing_set])
        
        logger.info(f"Metric definitions: {len(existing_set)} existing, {new_count} new")
        
        # Bulk upsert using INSERT ... ON CONFLICT DO NOTHING
        stmt = pg_insert(SupervisorFeedbackMetricDefinition).values(list(unique_metrics.values()))
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['metric_id']
        )
        
        result = self.db.execute(stmt)
        self.metric_definitions_created += new_count
        
        logger.info(f"Processed {len(unique_metrics)} unique metric definitions ({new_count} new)")
    
    def _bulk_process_forms(self, forms_by_id: Dict[int, List[Dict[str, Any]]]) -> Dict[int, int]:
        """
        Process forms in bulk using INSERT ... ON CONFLICT DO UPDATE.
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
            
        Returns:
            Dictionary mapping RO_Form_ID to database form.id
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        # Prepare form data (one per RO_Form_ID, extract from first row)
        form_data = []
        
        for ro_form_id, rows in forms_by_id.items():
            # All rows for a form have the same form-level data, use first row
            first_row = rows[0]
            
            form_data.append({
                'ro_form_id': ro_form_id,
                'employee_id': first_row['Employee_ID'],
                'from_date': first_row['From'],
                'to_date': first_row['To'],
                'feedback_cache': {},  # Will be populated after responses are processed
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
        
        if not form_data:
            logger.info("No forms to process")
            return {}
        
        # Query existing forms BEFORE upsert
        ro_form_ids = [f['ro_form_id'] for f in form_data]
        existing_forms = self.db.query(
            SupervisorFeedbackForm.ro_form_id
        ).filter(
            SupervisorFeedbackForm.ro_form_id.in_(ro_form_ids)
        ).all()
        
        existing_set = {ro_form_id for (ro_form_id,) in existing_forms}
        existing_count = len(existing_set)
        new_count = len(form_data) - existing_count
        
        logger.info(f"Forms: {existing_count} existing, {new_count} new")
        
        # Bulk upsert using INSERT ... ON CONFLICT DO UPDATE
        stmt = pg_insert(SupervisorFeedbackForm).values(form_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['ro_form_id'],
            set_={
                'employee_id': stmt.excluded.employee_id,
                'from_date': stmt.excluded.from_date,
                'to_date': stmt.excluded.to_date,
                'updated_at': stmt.excluded.updated_at
            }
        ).returning(SupervisorFeedbackForm.id, SupervisorFeedbackForm.ro_form_id)
        
        result = self.db.execute(stmt)
        
        # Build mapping of RO_Form_ID to database ID
        form_id_map = {}
        for form_id, ro_form_id in result:
            form_id_map[ro_form_id] = form_id
        
        self.forms_created += new_count
        self.forms_updated += existing_count
        
        logger.info(f"Processed {len(form_data)} forms ({new_count} created, {existing_count} updated)")
        
        return form_id_map
    
    def _bulk_process_responses(
        self, 
        forms_by_id: Dict[int, List[Dict[str, Any]]], 
        form_id_map: Dict[int, int]
    ) -> None:
        """
        Process responses using DELETE+INSERT strategy with batch idempotency protection.
        
        For each form:
        1. Check if incoming batch is complete (prevent form splitting across batches)
        2. DELETE all existing responses (only if batch is complete or new form)
        3. INSERT all new responses with rating conversion
        
        Batch Idempotency: If existing_count > incoming_count, uses upsert instead of DELETE
        to prevent data loss when forms are split across batch boundaries.
        
        Rating Conversion: Converts text ratings ("Good") to numeric (3) using position-based
        indexing from possible_values. Fetches metric definitions once for efficiency.
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
            form_id_map: Dictionary mapping RO_Form_ID to database form.id
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        total_responses = 0
        
        # Fetch ALL unique metric definitions in ONE query (bulk optimization)
        unique_metric_keys = set()
        for ro_form_id, rows in forms_by_id.items():
            for row in rows:
                unique_metric_keys.add((row['Section_ID'], row['Metric_ID']))
        
        metric_defs = self.db.query(SupervisorFeedbackMetricDefinition).filter(
            tuple_(
                SupervisorFeedbackMetricDefinition.section_id,
                SupervisorFeedbackMetricDefinition.metric_id
            ).in_(list(unique_metric_keys))
        ).all()
        
        # Build lookup dict: (section_id, metric_id) -> metric_definition
        metric_lookup = {
            (md.section_id, md.metric_id): md 
            for md in metric_defs
        }
        
        logger.debug(f"Fetched {len(metric_defs)} metric definitions for rating conversion")
        
        for ro_form_id, rows in forms_by_id.items():
            form_id = form_id_map.get(ro_form_id)
            if not form_id:
                logger.error(f"Form ID not found for RO_Form_ID {ro_form_id}, skipping responses")
                continue
            
            # Detect incomplete batches
            existing_count = self.db.query(SupervisorFeedbackResponse).filter(
                SupervisorFeedbackResponse.form_id == form_id
            ).count()
            
            incoming_count = len(rows)
            
            # If we have existing data but incoming is less, this might be a batch split
            if existing_count > 0 and incoming_count < existing_count:
                logger.warning(
                    f"Form {ro_form_id} has {existing_count} existing responses but only "
                    f"{incoming_count} incoming - possible batch split. Using upsert strategy "
                    f"instead of DELETE+INSERT to prevent data loss."
                )
                
                # Use upsert strategy for safety
                response_data = []
                for row in rows:
                    metric_key = (row['Section_ID'], row['Metric_ID'])
                    metric_def = metric_lookup.get(metric_key)
                    
                    if not metric_def:
                        logger.error(
                            f"Metric definition not found for Section_ID={row['Section_ID']}, "
                            f"Metric_ID={row['Metric_ID']}, skipping response"
                        )
                        continue
                    
                    # Convert rating from text to numeric
                    numeric_rating = None
                    max_value = None
                    
                    if metric_def.metric_type == 'R' and row.get('Value') and metric_def.possible_values:
                        options = [opt.strip() for opt in metric_def.possible_values.split(',')]
                        value_clean = row.get('Value').strip()
                        if value_clean in options:
                            numeric_rating = options.index(value_clean) + 1
                            max_value = metric_def.max_value or len(options)
                    
                    response_data.append({
                        'l_ro_form_metric_id': row['L_RO_Form_Metric_ID'],
                        'form_id': form_id,
                        'metric_definition_id': metric_def.id,
                        'text_response': row.get('Value'),
                        'numeric_rating': numeric_rating,
                        'max_value': max_value,
                        'created_at': datetime.now(timezone.utc)
                    })
                
                # Upsert each response
                if response_data:
                    for resp in response_data:
                        stmt = pg_insert(SupervisorFeedbackResponse).values(resp)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['l_ro_form_metric_id'],
                            set_={
                                'text_response': stmt.excluded.text_response,
                                'numeric_rating': stmt.excluded.numeric_rating,
                                'max_value': stmt.excluded.max_value
                            }
                        )
                        self.db.execute(stmt)
                    total_responses += len(response_data)
                
                continue  # Skip DELETE+INSERT logic
            
            # Step 1: DELETE existing responses for this form (safe - complete batch or new form)
            delete_stmt = delete(SupervisorFeedbackResponse).where(
                SupervisorFeedbackResponse.form_id == form_id
            )
            self.db.execute(delete_stmt)
            
            # Step 2: Prepare response data with rating conversion
            response_data = []
            
            for row in rows:
                # Look up metric definition from pre-fetched lookup
                metric_key = (row['Section_ID'], row['Metric_ID'])
                metric_def = metric_lookup.get(metric_key)
                
                if not metric_def:
                    logger.error(
                        f"Metric definition not found for Section_ID={row['Section_ID']}, "
                        f"Metric_ID={row['Metric_ID']}, skipping response"
                    )
                    continue
                
                # Convert rating from text to numeric
                numeric_rating = None
                max_value = None
                
                if metric_def.metric_type == 'R' and row.get('Value') and metric_def.possible_values:
                    options = [opt.strip() for opt in metric_def.possible_values.split(',')]
                    value_clean = row.get('Value').strip()
                    if value_clean in options:
                        numeric_rating = options.index(value_clean) + 1
                        max_value = metric_def.max_value or len(options)
                    else:
                        logger.warning(
                            f"Rating value '{value_clean}' not found in possible_values "
                            f"'{metric_def.possible_values}' for metric {metric_def.metric_id}"
                        )
                
                response_data.append({
                    'l_ro_form_metric_id': row['L_RO_Form_Metric_ID'],
                    'form_id': form_id,
                    'metric_definition_id': metric_def.id,
                    'text_response': row.get('Value'),
                    'numeric_rating': numeric_rating,
                    'max_value': max_value,
                    'created_at': datetime.now(timezone.utc)
                })
            
            # Step 3: Bulk INSERT new responses
            if response_data:
                self.db.bulk_insert_mappings(SupervisorFeedbackResponse, response_data)
                total_responses += len(response_data)
        
        self.responses_created += total_responses
        logger.info(f"Processed {total_responses} responses across {len(forms_by_id)} forms")
    
    def _bulk_generate_caches(self, form_id_map: Dict[int, int]) -> None:
        """
        Generate JSONB caches for all forms using true bulk operations.
        
        Optimized approach:
        1. Fetch ALL responses for ALL forms in single query
        2. Group responses by form_id in Python
        3. Calculate caches for each form in memory
        4. Bulk update all forms in single operation
        
        Cache contains (dynamically calculated based on actual metrics in form):
        - total_score: Sum of numeric ratings for all rating metrics
        - average_rating: Average rating across all rating metrics
        - text_responses_count: Count of text responses
        - metrics_completed: Count of non-null responses
        - completion_percentage: Percentage of metrics with responses
        
        Args:
            form_id_map: Dictionary mapping RO_Form_ID to database form.id
        """
        if not form_id_map:
            logger.info("No forms to generate caches for")
            return
        
        form_ids = list(form_id_map.values())
        
        # Step 1: Fetch ALL responses for ALL forms in ONE query
        responses = self.db.query(
            SupervisorFeedbackResponse,
            SupervisorFeedbackMetricDefinition
        ).join(
            SupervisorFeedbackMetricDefinition,
            SupervisorFeedbackResponse.metric_definition_id == SupervisorFeedbackMetricDefinition.id
        ).filter(
            SupervisorFeedbackResponse.form_id.in_(form_ids)
        ).all()
        
        # Step 2: Group responses by form_id
        responses_by_form = {}
        for response, metric_def in responses:
            form_id = response.form_id
            if form_id not in responses_by_form:
                responses_by_form[form_id] = []
            responses_by_form[form_id].append((response, metric_def))
        
        # Step 3: Calculate caches for each form
        cache_updates = []
        current_time = datetime.now(timezone.utc)
        
        for form_id in form_ids:
            form_responses = responses_by_form.get(form_id, [])
            cache = self._calculate_form_cache(form_id, form_responses)
            
            cache_updates.append({
                'id': form_id,
                'feedback_cache': cache,
                'updated_at': current_time
            })
        
        # Step 4: Bulk UPDATE all forms in ONE operation
        if cache_updates:
            self.db.bulk_update_mappings(SupervisorFeedbackForm, cache_updates)
        
        logger.info(f"Generated caches for {len(form_id_map)} forms using bulk operations")
    
    def _calculate_form_cache(self, form_id: int, responses: List[Tuple[SupervisorFeedbackResponse, SupervisorFeedbackMetricDefinition]]) -> Dict[str, Any]:
        """
        Calculate JSONB cache for a single form from pre-fetched responses.
        
        Pure calculation function (no database queries). Used by bulk cache generation.
        
        Args:
            form_id: Database form.id (for logging only)
            responses: List of (response, metric_def) tuples
            
        Returns:
            Cache dictionary ready to be stored in feedback_cache JSONB column
        """
        # Calculate aggregations
        total_score = 0
        rating_count = 0
        rating_sum = 0  # Will store percentage-normalized ratings
        text_responses_count = 0
        metrics_completed = 0
        total_metrics = len(responses)
        
        # Group responses by section for form_data structure
        sections_dict = {}
        
        for response, metric_def in responses:
            # Count completed metrics (any response with non-empty text_response)
            if response.text_response and response.text_response.strip():
                metrics_completed += 1
            
            # For rating metrics, normalize to percentage (fixes scale comparison issue)
            if metric_def.metric_type == 'R' and response.text_response and metric_def.possible_values:
                try:
                    # Split possible values and find the index of the response
                    possible_vals = [v.strip() for v in metric_def.possible_values.split(',')]
                    if response.text_response in possible_vals:
                        position = possible_vals.index(response.text_response) + 1
                        
                        # Normalize to percentage using max_value
                        # Example: position 4 of 4 = 100%, position 3 of 3 = 100%
                        # This allows comparing different scales (4-point vs 3-point)
                        if metric_def.max_value and metric_def.max_value > 0:
                            normalized_rating = (position / metric_def.max_value) * 100
                        else:
                            # Skip rating if max_value not set (cannot normalize safely)
                            logger.warning(
                                f"Skipping rating normalization for metric {metric_def.metric_id} "
                                f"in form {form_id}: max_value not set or invalid"
                            )
                            continue
                        
                        rating_sum += normalized_rating
                        rating_count += 1
                        total_score += normalized_rating
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse rating from '{response.text_response}': {e}")
            
            # Count text-type responses
            if metric_def.metric_type == 'T' and response.text_response:
                text_responses_count += 1
            
            # Build form_data structure (grouped by section)
            section_key = (metric_def.section_id, metric_def.section)
            if section_key not in sections_dict:
                sections_dict[section_key] = {
                    'section_id': metric_def.section_id,
                    'section_name': metric_def.section,
                    'metrics': []
                }
            
            sections_dict[section_key]['metrics'].append({
                'metric_id': metric_def.metric_id,
                'metric_name': metric_def.metric_name,
                'metric_type': metric_def.metric_type,
                'possible_values': metric_def.possible_values,
                'max_value': metric_def.max_value,
                'response': response.text_response
            })
        
        # Build cache dictionary with stats + full form data
        cache = {
            'stats': {
                'total_score': round(total_score, 2),
                'maximum_score': rating_count * 100,
                'average_rating': round(rating_sum / rating_count, 2) if rating_count > 0 else None,
                'text_responses_count': text_responses_count,
                'metrics_completed': metrics_completed,
                'total_metrics': total_metrics,
                'completion_percentage': round((metrics_completed / total_metrics * 100), 2) if total_metrics > 0 else 0
            },
            'form_data': {
                'sections': list(sections_dict.values())
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return cache
    
    def _regenerate_form_cache(self, form_id: int) -> None:
        """
        Regenerate JSONB cache for a single form (used by single-row processing).
        
        For bulk operations, use _bulk_generate_caches() instead.
        
        Args:
            form_id: Database form.id
        """
        # Query responses for this form
        responses = self.db.query(
            SupervisorFeedbackResponse,
            SupervisorFeedbackMetricDefinition
        ).join(
            SupervisorFeedbackMetricDefinition,
            SupervisorFeedbackResponse.metric_definition_id == SupervisorFeedbackMetricDefinition.id
        ).filter(
            SupervisorFeedbackResponse.form_id == form_id
        ).all()
        
        # Calculate cache
        cache = self._calculate_form_cache(form_id, responses)
        
        # Update form using ORM (single form, so ORM tracking is fine)
        form = self.db.query(SupervisorFeedbackForm).filter(
            SupervisorFeedbackForm.id == form_id
        ).first()
        
        if form:
            form.feedback_cache = cache
            form.updated_at = datetime.now(timezone.utc)
    
    def _upsert_metric_definition(self, row_dict: Dict[str, Any]) -> SupervisorFeedbackMetricDefinition:
        """
        Upsert a single metric definition.
        
        Used for single-row processing (process_row method).
        Uses ORM pattern (like job_description_processor) for accurate metrics tracking.
        
        Args:
            row_dict: Validated row dictionary
            
        Returns:
            Metric definition instance
        """
        # Check if metric definition already exists
        existing_metric = self.db.query(SupervisorFeedbackMetricDefinition).filter(
            SupervisorFeedbackMetricDefinition.section_id == row_dict['Section_ID'],
            SupervisorFeedbackMetricDefinition.metric_id == row_dict['Metric_ID']
        ).first()
        
        # Count possible values to calculate max_value
        possible_values = row_dict.get('Possible_Values')
        max_value = None
        if possible_values and row_dict['Metric_Type'] == 'R':
            max_value = len([v.strip() for v in possible_values.split(',') if v.strip()])
        
        if existing_metric:
            # Metric definitions are immutable - don't update, just return existing
            # (matches INSERT...ON CONFLICT DO NOTHING behavior in bulk mode)
            return existing_metric
        else:
            # Create new metric definition
            new_metric = SupervisorFeedbackMetricDefinition(
                section_id=row_dict['Section_ID'],
                section=row_dict['Section'],
                metric_id=row_dict['Metric_ID'],
                metric_name=row_dict['Metric_Title'],
                metric_description=row_dict.get('Instructions'),
                metric_type=row_dict['Metric_Type'],
                possible_values=possible_values,
                max_value=max_value,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(new_metric)
            self.db.flush()  
            self.metric_definitions_created += 1
            return new_metric
    
    def _upsert_form(self, row_dict: Dict[str, Any]) -> SupervisorFeedbackForm:
        """
        Upsert a single form.
        
        Used for single-row processing (process_row method).
        Uses ORM pattern (like job_description_processor) for accurate metrics tracking.
        
        Args:
            row_dict: Validated row dictionary
            
        Returns:
            Form instance
        """
        # Check if form already exists
        existing_form = self.db.query(SupervisorFeedbackForm).filter(
            SupervisorFeedbackForm.ro_form_id == row_dict['RO_Form_ID']
        ).first()
        
        if existing_form:
            # Update existing form
            existing_form.employee_id = row_dict['Employee_ID']
            existing_form.from_date = row_dict['From']
            existing_form.to_date = row_dict['To']
            existing_form.updated_at = datetime.now(timezone.utc)
            self.forms_updated += 1
            return existing_form
        else:
            # Create new form
            new_form = SupervisorFeedbackForm(
                ro_form_id=row_dict['RO_Form_ID'],
                employee_id=row_dict['Employee_ID'],
                from_date=row_dict['From'],
                to_date=row_dict['To'],
                feedback_cache={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(new_form)
            self.db.flush() 
            self.forms_created += 1
            return new_form
    
    def _upsert_response(self, row_dict: Dict[str, Any], form_id: int) -> None:
        """
        Upsert a single response.
        
        Used for single-row processing (process_row method).
        Uses ORM pattern (like job_description_processor) for accurate metrics tracking.
        
        Args:
            row_dict: Validated row dictionary
            form_id: Database form.id
        """
        # Look up full metric definition (need possible_values for conversion)
        metric_def = self.db.query(SupervisorFeedbackMetricDefinition).filter(
            SupervisorFeedbackMetricDefinition.section_id == row_dict['Section_ID'],
            SupervisorFeedbackMetricDefinition.metric_id == row_dict['Metric_ID']
        ).first()
        
        if not metric_def:
            logger.error(
                f"Metric definition not found for Section_ID={row_dict['Section_ID']}, "
                f"Metric_ID={row_dict['Metric_ID']}, skipping response"
            )
            return
        
        # Convert rating from text to numeric
        numeric_rating = None
        max_value = None
        
        if metric_def.metric_type == 'R' and row_dict.get('Value') and metric_def.possible_values:
            options = [opt.strip() for opt in metric_def.possible_values.split(',')]
            value_clean = row_dict.get('Value').strip()
            if value_clean in options:
                numeric_rating = options.index(value_clean) + 1
                max_value = metric_def.max_value or len(options)
        
        # Check if response already exists
        existing_response = self.db.query(SupervisorFeedbackResponse).filter(
            SupervisorFeedbackResponse.l_ro_form_metric_id == row_dict['L_RO_Form_Metric_ID']
        ).first()
        
        if existing_response:
            # Update existing response
            existing_response.text_response = row_dict.get('Value')
            existing_response.numeric_rating = numeric_rating
            existing_response.max_value = max_value
            existing_response.updated_at = datetime.now(timezone.utc)
            # Don't increment counter - only count creates in single-row mode
        else:
            # Create new response
            new_response = SupervisorFeedbackResponse(
                l_ro_form_metric_id=row_dict['L_RO_Form_Metric_ID'],
                form_id=form_id,
                metric_definition_id=metric_def.id,
                text_response=row_dict.get('Value'),
                numeric_rating=numeric_rating,
                max_value=max_value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(new_response)
            self.db.flush() 
            self.responses_created += 1
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get processing metrics.
        
        Returns dictionary with processor-specific metrics.
        Used by RowProcessor.get_metrics() and sync service.
        """
        return {
            "forms_created": self.forms_created,
            "forms_updated": self.forms_updated,
            "responses_created": self.responses_created,
            "metric_definitions_created": self.metric_definitions_created,
            "processed_rows": self.processed_rows,
            "successful_rows": self.successful_rows
        }
    
    def get_required_headers(self) -> List[str]:
        """Get the list of required headers for this processor."""
        return self.REQUIRED_HEADERS
    
    @classmethod
    def can_process(cls, headers: List[str]) -> bool:
        """
        Determine if this processor can handle the CSV format.
        
        Args:
            headers: List of headers from the CSV file
            
        Returns:
            True if all required headers are present
        """
        headers_lower = [h.lower() for h in headers]
        required_lower = [h.lower() for h in cls.REQUIRED_HEADERS]
        
        return all(req in headers_lower for req in required_lower)
