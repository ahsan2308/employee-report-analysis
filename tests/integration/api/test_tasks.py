"""Characterization of the /tasks router."""
from datetime import date, datetime

import pytest

from tests.integration.api.seed import (
    add_analysis,
    add_monthly,
    add_quarterly,
    add_report,
    add_task,
    fixed_uuid,
    seed_employees,
)

STARTED = datetime(2025, 3, 14, 9, 0, 0)
FINISHED = datetime(2025, 3, 14, 9, 2, 30, 500000)


# --------------------------------------------------------------------------- GET /tasks/{task_id}

def test_status_pending_task(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="pending", celery_task_id="pending")
    snap("tasks_status_pending", api.get(f"/tasks/{fixed_uuid(1)}"))


def test_status_running_task_has_no_duration(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="running", started_at=STARTED)
    snap("tasks_status_running", api.get(f"/tasks/{fixed_uuid(1)}"))


def test_status_completed_task_has_duration(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="completed", started_at=STARTED, completed_at=FINISHED)
    snap("tasks_status_completed", api.get(f"/tasks/{fixed_uuid(1)}"))


def test_status_failed_task_is_complete(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="failed", started_at=STARTED, completed_at=FINISHED,
             error_message="LLM timeout")
    snap("tasks_status_failed", api.get(f"/tasks/{fixed_uuid(1)}"))


def test_status_null_celery_task_id_fails_response_validation(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), celery_task_id=None)
    snap("tasks_status_null_celery_id", api.get(f"/tasks/{fixed_uuid(1)}"))


def test_status_missing_task_returns_404(api, snap):
    snap("tasks_status_missing", api.get(f"/tasks/{fixed_uuid(404)}"))


def test_status_invalid_uuid_422(api, snap):
    snap("tasks_status_invalid_uuid", api.get("/tasks/not-a-uuid"))


# --------------------------------------------------------------------------- GET /tasks/{task_id}/result

def test_result_missing_task_returns_404(api, snap):
    snap("tasks_result_missing", api.get(f"/tasks/{fixed_uuid(404)}/result"))


def test_result_invalid_uuid_422(api, snap):
    snap("tasks_result_invalid_uuid", api.get("/tasks/xyz/result"))


@pytest.mark.parametrize("status", ["pending", "running"])
def test_result_not_complete_422(api, db_session, snap, status):
    add_task(db_session, task_id=fixed_uuid(1), status=status)
    snap(f"tasks_result_not_complete_{status}", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_failed_task(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="failed", error_message="LLM timeout",
             result_data={"partial": True})
    snap("tasks_result_failed", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_report_analysis_reference_is_expanded(api, db_session, snap):
    seed_employees(db_session)
    report = add_report(db_session, 1, date(2025, 1, 6), report_id=fixed_uuid(10))
    analysis = add_analysis(db_session, report)
    add_task(db_session, task_id=fixed_uuid(1), status="completed", report_id=report.report_id,
             result_data={"analysis_id": analysis.analysis_id, "report_id": str(report.report_id)})
    snap("tasks_result_report_reference", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_report_analysis_defaults_for_missing_assessments(api, db_session, snap):
    seed_employees(db_session)
    report = add_report(db_session, 1, date(2025, 1, 6), report_id=fixed_uuid(10))
    analysis = add_analysis(
        db_session, report,
        credibility_rating=None, credibility_explanation=None, exaggeration_flags=None, consistency_score=None,
        performance_rating=None, performance_summary=None, performance_strengths=None,
        performance_improvement_areas=None,
    )
    add_task(db_session, task_id=fixed_uuid(1), status="completed", report_id=report.report_id,
             result_data={"analysis_id": analysis.analysis_id})
    snap("tasks_result_report_reference_defaults", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_report_analysis_full_payload_returned_verbatim(api, db_session, snap):
    seed_employees(db_session)
    report = add_report(db_session, 1, date(2025, 1, 6), report_id=fixed_uuid(10))
    analysis = add_analysis(db_session, report)
    add_task(db_session, task_id=fixed_uuid(1), status="completed", report_id=report.report_id,
             result_data={"analysis_id": analysis.analysis_id, "report_id": "r", "sentiment": 0.1})
    snap("tasks_result_report_full_payload", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_report_analysis_dangling_reference(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="completed", result_data={"analysis_id": 999})
    snap("tasks_result_report_dangling", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_completed_without_result_data(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="completed", result_data=None)
    snap("tasks_result_no_data", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_monthly_reference_is_expanded(api, db_session, snap):
    seed_employees(db_session)
    monthly = add_monthly(db_session, 1, 2025, 2)
    add_task(db_session, task_id=fixed_uuid(1), status="completed", task_type="MONTHLY_ANALYSIS",
             employee_id=1, year=2025, month=2, result_data={"analysis_id": monthly.analysis_id})
    snap("tasks_result_monthly", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_monthly_reference_missing_analysis(api, db_session, snap):
    seed_employees(db_session)
    add_task(db_session, task_id=fixed_uuid(1), status="completed", task_type="MONTHLY_ANALYSIS",
             employee_id=1, year=2025, month=2, result_data={"analysis_id": 5, "cached": "value"})
    snap("tasks_result_monthly_missing", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_quarterly_reference_is_expanded(api, db_session, snap):
    seed_employees(db_session)
    quarterly = add_quarterly(db_session, 1, 2025, 1)
    add_task(db_session, task_id=fixed_uuid(1), status="completed", task_type="QUARTERLY_ANALYSIS",
             employee_id=1, year=2025, quarter=1, result_data={"analysis_id": quarterly.analysis_id})
    snap("tasks_result_quarterly", api.get(f"/tasks/{fixed_uuid(1)}/result"))


def test_result_unknown_task_type_returns_raw_data(api, db_session, snap):
    add_task(db_session, task_id=fixed_uuid(1), status="completed", task_type="SOMETHING_ELSE",
             result_data={"analysis_id": 1, "x": [1, 2]})
    snap("tasks_result_unknown_type", api.get(f"/tasks/{fixed_uuid(1)}/result"))
