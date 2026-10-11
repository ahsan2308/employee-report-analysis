"""Supervisor feedback forms, metric definitions and responses, in the caller's session."""
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import delete, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.db_models import (
    SupervisorFeedbackForm,
    SupervisorFeedbackMetricDefinition,
    SupervisorFeedbackResponse,
)

# --- metric definitions (immutable once created)

def existing_metric_keys(session: Session, keys: List[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    """The (section_id, metric_id) keys among keys that already have a definition."""
    rows = session.query(
        SupervisorFeedbackMetricDefinition.section_id,
        SupervisorFeedbackMetricDefinition.metric_id
    ).filter(
        tuple_(SupervisorFeedbackMetricDefinition.section_id, SupervisorFeedbackMetricDefinition.metric_id).in_(keys)
    ).all()
    return {(section_id, metric_id) for section_id, metric_id in rows}


def insert_metric_definitions(session: Session, rows: List[Dict[str, Any]]) -> None:
    """Insert metric definitions; one that exists (same metric_id) is left as it is."""
    stmt = pg_insert(SupervisorFeedbackMetricDefinition).values(rows)
    session.execute(stmt.on_conflict_do_nothing(index_elements=['metric_id']))


def metric_definitions_for(session: Session, keys: Iterable[Tuple[int, int]]) -> List[SupervisorFeedbackMetricDefinition]:
    return session.query(SupervisorFeedbackMetricDefinition).filter(
        tuple_(SupervisorFeedbackMetricDefinition.section_id, SupervisorFeedbackMetricDefinition.metric_id).in_(list(keys))
    ).all()


def find_metric_definition(session: Session, section_id, metric_id) -> Optional[SupervisorFeedbackMetricDefinition]:
    return session.query(SupervisorFeedbackMetricDefinition).filter(
        SupervisorFeedbackMetricDefinition.section_id == section_id,
        SupervisorFeedbackMetricDefinition.metric_id == metric_id
    ).first()


# --- forms

def existing_form_ids(session: Session, ro_form_ids: List[int]) -> Set[int]:
    """The RO_Form_IDs among these that already have a form."""
    rows = session.query(SupervisorFeedbackForm.ro_form_id).filter(
        SupervisorFeedbackForm.ro_form_id.in_(ro_form_ids)
    ).all()
    return {ro_form_id for (ro_form_id,) in rows}


def upsert_forms(session: Session, form_data: List[Dict[str, Any]]) -> Dict[int, int]:
    """Insert forms, updating the employee and period of those that exist; returns {RO_Form_ID: form id}."""
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
    return {ro_form_id: form_id for form_id, ro_form_id in session.execute(stmt)}


def find_form(session: Session, ro_form_id) -> Optional[SupervisorFeedbackForm]:
    return session.query(SupervisorFeedbackForm).filter(SupervisorFeedbackForm.ro_form_id == ro_form_id).first()


def get_form(session: Session, form_id: int) -> Optional[SupervisorFeedbackForm]:
    return session.query(SupervisorFeedbackForm).filter(SupervisorFeedbackForm.id == form_id).first()


def update_form_caches(session: Session, cache_updates: List[Dict[str, Any]]) -> None:
    """Bulk-set feedback_cache and updated_at ({id, feedback_cache, updated_at} per form)."""
    session.bulk_update_mappings(SupervisorFeedbackForm, cache_updates)


# --- responses

def count_responses(session: Session, form_id: int) -> int:
    return session.query(SupervisorFeedbackResponse).filter(SupervisorFeedbackResponse.form_id == form_id).count()


def delete_responses(session: Session, form_id: int) -> None:
    session.execute(delete(SupervisorFeedbackResponse).where(SupervisorFeedbackResponse.form_id == form_id))


def insert_responses(session: Session, rows: List[Dict[str, Any]]) -> None:
    session.bulk_insert_mappings(SupervisorFeedbackResponse, rows)


def upsert_response_row(session: Session, row: Dict[str, Any]) -> None:
    """Insert a response, or update the text and rating of the one with the same L_RO_Form_Metric_ID."""
    stmt = pg_insert(SupervisorFeedbackResponse).values(row)
    stmt = stmt.on_conflict_do_update(
        index_elements=['l_ro_form_metric_id'],
        set_={
            'text_response': stmt.excluded.text_response,
            'numeric_rating': stmt.excluded.numeric_rating,
            'max_value': stmt.excluded.max_value
        }
    )
    session.execute(stmt)


def find_response(session: Session, l_ro_form_metric_id) -> Optional[SupervisorFeedbackResponse]:
    return session.query(SupervisorFeedbackResponse).filter(
        SupervisorFeedbackResponse.l_ro_form_metric_id == l_ro_form_metric_id
    ).first()


def responses_with_definitions(session: Session, form_ids: List[int]) -> List[Tuple[SupervisorFeedbackResponse, SupervisorFeedbackMetricDefinition]]:
    """(response, metric definition) pairs of the given forms."""
    return session.query(SupervisorFeedbackResponse, SupervisorFeedbackMetricDefinition).join(
        SupervisorFeedbackMetricDefinition,
        SupervisorFeedbackResponse.metric_definition_id == SupervisorFeedbackMetricDefinition.id
    ).filter(SupervisorFeedbackResponse.form_id.in_(form_ids)).all()


def add(session: Session, row) -> None:
    """Add a new row and flush it, so it has its id."""
    session.add(row)
    session.flush()
