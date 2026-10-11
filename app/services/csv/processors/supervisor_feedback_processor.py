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
from typing import Dict, Any, Tuple, List
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.services.csv.processors.base import BaseCSVProcessor
from app.services.csv.row_models import SupervisorFeedbackCSVRow
from app.models.db_models import (
    SupervisorFeedbackForm, 
    SupervisorFeedbackMetricDefinition, 
    SupervisorFeedbackResponse
)
from app.services.csv.error_handler import ImportErrorHandler
from app.core.logger import logger
from app.domain.supervisor_feedback import form_cache, metric_max_value, rate_response
from app.repositories import supervisor_feedback as feedback_repo


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

    row_model = SupervisorFeedbackCSVRow
    
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
    
    def validate_row(self, row_data: Dict[str, Any], row_number: int) -> bool:
        """Dry-run check: the row model, then that the employee exists (read-only)."""
        validated = self._validate_model(row_data, row_number)
        if validated is None:
            return False
        employee_id = validated.model_dump().get('Employee_ID')
        if employee_id not in self._get_existing_employee_ids():
            self.error_handler.add_missing_employee_error(
                row_number=row_number,
                error_message=f"Employee ID {employee_id} does not exist",
                row_data=row_data
            )
            return False
        return True

     
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
                self.error_handler.add_missing_employee_error(
                    row_number=row_number,
                    error_message=f"Employee ID {employee_id} does not exist",
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
        first_index = df.index[0] if len(df) else 0  # index of this chunk's first file row
        if df.empty:
            return 0, 0
        
        # Track metrics
        total_rows = len(df)
        self.processed_rows += total_rows
        
        # Validate all rows with Pydantic
        validated_rows = []
        invalid_rows = []
        
        for idx, row in df.iterrows():
            # Chunks keep the file-wide index; dropped duplicates keep their gaps
            row_number = start_row_number + (idx - first_index)
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
        # Every validated row counts as unsaved until the employee check narrows the list
        valid_rows = validated_rows
        try:
            # Get set of existing employee IDs
            existing_employees = self._get_existing_employee_ids()
            
            # Filter out rows with non-existent employees BEFORE bulk processing
            valid_rows = []
            for row_number, row_dict in validated_rows:
                employee_id = row_dict.get('Employee_ID')
                if employee_id not in existing_employees:
                    self.error_handler.add_missing_employee_error(
                        row_number=row_number,
                        error_message=f"Employee ID {employee_id} does not exist in database",
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
                self._record_unsaved_rows(valid_rows)
            
            return successful_rows, total_rows
            
        except Exception as e:
            logger.error(f"Bulk supervisor feedback processing failed: {str(e)}")
            self.db.rollback()
            self._record_unsaved_rows(valid_rows, e)
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
        Extract unique metric definitions from all forms and insert the new ones.
        
        Metric definitions are immutable: an existing one is left as it is.
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
        """
        # Extract unique metric definitions
        unique_metrics = {}
        
        for form_id, rows in forms_by_id.items():
            for row in rows:
                metric_key = (row['Section_ID'], row['Metric_ID'])
                if metric_key not in unique_metrics:
                    unique_metrics[metric_key] = {
                        'section_id': row['Section_ID'],
                        'section': row['Section'],
                        'metric_id': row['Metric_ID'],
                        'metric_name': row['Metric_Title'],
                        'metric_description': row.get('Instructions'),
                        'metric_type': row['Metric_Type'],
                        'possible_values': row.get('Possible_Values'),
                        'max_value': metric_max_value(row['Metric_Type'], row.get('Possible_Values')),
                        'created_at': datetime.now(timezone.utc)
                    }
        
        if not unique_metrics:
            logger.info("No metric definitions to process")
            return
        
        # Count existing metric definitions BEFORE inserting
        metric_keys = [(m['section_id'], m['metric_id']) for m in unique_metrics.values()]
        existing_set = feedback_repo.existing_metric_keys(self.db, metric_keys)
        new_count = len([m for m in unique_metrics.values() if (m['section_id'], m['metric_id']) not in existing_set])
        
        logger.info(f"Metric definitions: {len(existing_set)} existing, {new_count} new")
        
        feedback_repo.insert_metric_definitions(self.db, list(unique_metrics.values()))
        self.metric_definitions_created += new_count
        
        logger.info(f"Processed {len(unique_metrics)} unique metric definitions ({new_count} new)")
    
    def _bulk_process_forms(self, forms_by_id: Dict[int, List[Dict[str, Any]]]) -> Dict[int, int]:
        """
        Upsert the forms (one per RO_Form_ID).
        
        Args:
            forms_by_id: Dictionary mapping RO_Form_ID to list of row dictionaries
            
        Returns:
            Dictionary mapping RO_Form_ID to database form.id
        """
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
        
        # Count existing forms BEFORE upsert
        existing_count = len(feedback_repo.existing_form_ids(self.db, [f['ro_form_id'] for f in form_data]))
        new_count = len(form_data) - existing_count
        
        logger.info(f"Forms: {existing_count} existing, {new_count} new")
        
        form_id_map = feedback_repo.upsert_forms(self.db, form_data)
        
        self.forms_created += new_count
        self.forms_updated += existing_count
        
        logger.info(f"Processed {len(form_data)} forms ({new_count} created, {existing_count} updated)")
        
        return form_id_map
    
    def _response_row(self, row: Dict[str, Any], form_id: int, metric_def, warn_unknown_rating: bool = False) -> Dict[str, Any]:
        """The response to store for a CSV row, with its rating converted to a number."""
        numeric_rating, max_value = rate_response(
            metric_def.metric_type, row.get('Value'), metric_def.possible_values, metric_def.max_value
        )
        if (warn_unknown_rating and numeric_rating is None and metric_def.metric_type == 'R'
                and row.get('Value') and metric_def.possible_values):
            logger.warning(
                f"Rating value '{row.get('Value').strip()}' not found in possible_values "
                f"'{metric_def.possible_values}' for metric {metric_def.metric_id}"
            )
        return {
            'l_ro_form_metric_id': row['L_RO_Form_Metric_ID'],
            'form_id': form_id,
            'metric_definition_id': metric_def.id,
            'text_response': row.get('Value'),
            'numeric_rating': numeric_rating,
            'max_value': max_value,
            'created_at': datetime.now(timezone.utc)
        }
    
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
        total_responses = 0
        
        # Fetch ALL unique metric definitions in ONE query (bulk optimization)
        unique_metric_keys = set()
        for ro_form_id, rows in forms_by_id.items():
            for row in rows:
                unique_metric_keys.add((row['Section_ID'], row['Metric_ID']))
        
        metric_defs = feedback_repo.metric_definitions_for(self.db, unique_metric_keys)
        
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
            existing_count = feedback_repo.count_responses(self.db, form_id)
            incoming_count = len(rows)
            
            # If we have existing data but incoming is less, this might be a batch split
            batch_split = existing_count > 0 and incoming_count < existing_count
            if batch_split:
                logger.warning(
                    f"Form {ro_form_id} has {existing_count} existing responses but only "
                    f"{incoming_count} incoming - possible batch split. Using upsert strategy "
                    f"instead of DELETE+INSERT to prevent data loss."
                )
            else:
                # DELETE existing responses for this form (safe - complete batch or new form)
                feedback_repo.delete_responses(self.db, form_id)
            
            response_data = []
            for row in rows:
                # Look up metric definition from pre-fetched lookup
                metric_def = metric_lookup.get((row['Section_ID'], row['Metric_ID']))
                if not metric_def:
                    logger.error(
                        f"Metric definition not found for Section_ID={row['Section_ID']}, "
                        f"Metric_ID={row['Metric_ID']}, skipping response"
                    )
                    continue
                response_data.append(self._response_row(row, form_id, metric_def, warn_unknown_rating=not batch_split))
            
            if response_data:
                if batch_split:
                    # Upsert each response, keeping the form's other responses
                    for resp in response_data:
                        feedback_repo.upsert_response_row(self.db, resp)
                else:
                    feedback_repo.insert_responses(self.db, response_data)
                total_responses += len(response_data)
        
        self.responses_created += total_responses
        logger.info(f"Processed {total_responses} responses across {len(forms_by_id)} forms")
    
    def _bulk_generate_caches(self, form_id_map: Dict[int, int]) -> None:
        """
        Generate the feedback_cache of every form: fetch all their responses in
        one query, build each cache in memory, and update all forms at once.
        
        Args:
            form_id_map: Dictionary mapping RO_Form_ID to database form.id
        """
        if not form_id_map:
            logger.info("No forms to generate caches for")
            return
        
        form_ids = list(form_id_map.values())
        
        # Group responses by form_id
        responses_by_form = {}
        for response, metric_def in feedback_repo.responses_with_definitions(self.db, form_ids):
            responses_by_form.setdefault(response.form_id, []).append((response, metric_def))
        
        # Calculate caches for each form
        current_time = datetime.now(timezone.utc)
        cache_updates = [
            {
                'id': form_id,
                'feedback_cache': self._calculate_form_cache(form_id, responses_by_form.get(form_id, [])),
                'updated_at': current_time
            }
            for form_id in form_ids
        ]
        
        if cache_updates:
            feedback_repo.update_form_caches(self.db, cache_updates)
        
        logger.info(f"Generated caches for {len(form_id_map)} forms using bulk operations")
    
    def _calculate_form_cache(self, form_id: int, responses: List[Tuple[Any, Any]]) -> Dict[str, Any]:
        """The feedback_cache of one form from its (response, metric definition) pairs."""
        cache, skipped_metric_ids = form_cache(responses)
        for metric_id in skipped_metric_ids:
            logger.warning(
                f"Skipping rating normalization for metric {metric_id} "
                f"in form {form_id}: max_value not set or invalid"
            )
        return cache
    
    def _regenerate_form_cache(self, form_id: int) -> None:
        """
        Regenerate the feedback_cache of a single form (used by single-row processing).
        
        Args:
            form_id: Database form.id
        """
        cache = self._calculate_form_cache(form_id, feedback_repo.responses_with_definitions(self.db, [form_id]))
        form = feedback_repo.get_form(self.db, form_id)
        if form:
            form.feedback_cache = cache
            form.updated_at = datetime.now(timezone.utc)
    
    def _upsert_metric_definition(self, row_dict: Dict[str, Any]) -> SupervisorFeedbackMetricDefinition:
        """
        Return the row's metric definition, creating it if needed (single-row processing).
        
        Metric definitions are immutable: an existing one is returned unchanged,
        as the bulk path leaves it.
        """
        existing_metric = feedback_repo.find_metric_definition(self.db, row_dict['Section_ID'], row_dict['Metric_ID'])
        if existing_metric:
            return existing_metric
        
        new_metric = SupervisorFeedbackMetricDefinition(
            section_id=row_dict['Section_ID'],
            section=row_dict['Section'],
            metric_id=row_dict['Metric_ID'],
            metric_name=row_dict['Metric_Title'],
            metric_description=row_dict.get('Instructions'),
            metric_type=row_dict['Metric_Type'],
            possible_values=row_dict.get('Possible_Values'),
            max_value=metric_max_value(row_dict['Metric_Type'], row_dict.get('Possible_Values')),
            created_at=datetime.now(timezone.utc)
        )
        feedback_repo.add(self.db, new_metric)
        self.metric_definitions_created += 1
        return new_metric
    
    def _upsert_form(self, row_dict: Dict[str, Any]) -> SupervisorFeedbackForm:
        """Update the row's form, or create it (single-row processing)."""
        existing_form = feedback_repo.find_form(self.db, row_dict['RO_Form_ID'])
        
        if existing_form:
            existing_form.employee_id = row_dict['Employee_ID']
            existing_form.from_date = row_dict['From']
            existing_form.to_date = row_dict['To']
            existing_form.updated_at = datetime.now(timezone.utc)
            self.forms_updated += 1
            return existing_form
        
        new_form = SupervisorFeedbackForm(
            ro_form_id=row_dict['RO_Form_ID'],
            employee_id=row_dict['Employee_ID'],
            from_date=row_dict['From'],
            to_date=row_dict['To'],
            feedback_cache={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        feedback_repo.add(self.db, new_form)
        self.forms_created += 1
        return new_form
    
    def _upsert_response(self, row_dict: Dict[str, Any], form_id: int) -> None:
        """Update the row's response, or create it (single-row processing)."""
        metric_def = feedback_repo.find_metric_definition(self.db, row_dict['Section_ID'], row_dict['Metric_ID'])
        if not metric_def:
            logger.error(
                f"Metric definition not found for Section_ID={row_dict['Section_ID']}, "
                f"Metric_ID={row_dict['Metric_ID']}, skipping response"
            )
            return
        
        numeric_rating, max_value = rate_response(
            metric_def.metric_type, row_dict.get('Value'), metric_def.possible_values, metric_def.max_value
        )
        
        existing_response = feedback_repo.find_response(self.db, row_dict['L_RO_Form_Metric_ID'])
        if existing_response:
            existing_response.text_response = row_dict.get('Value')
            existing_response.numeric_rating = numeric_rating
            existing_response.max_value = max_value
            existing_response.updated_at = datetime.now(timezone.utc)
            # Don't increment counter - only count creates in single-row mode
            return
        
        feedback_repo.add(self.db, SupervisorFeedbackResponse(
            l_ro_form_metric_id=row_dict['L_RO_Form_Metric_ID'],
            form_id=form_id,
            metric_definition_id=metric_def.id,
            text_response=row_dict.get('Value'),
            numeric_rating=numeric_rating,
            max_value=max_value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ))
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
