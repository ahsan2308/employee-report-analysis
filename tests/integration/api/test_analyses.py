"""Characterization of the /analyses router (Celery dispatch patched in conftest)."""
from datetime import date
from unittest import mock

import pytest

from app.models.task_models import BackgroundTask
from tests.integration.api.seed import (
    add_analysis,
    add_monthly,
    add_quarterly,
    add_report,
    add_task,
    dump_rows,
    fixed_uuid,
    seed_employees,
)

REPORT_ID = fixed_uuid(10)


def _tasks(db):
    return dump_rows(db, BackgroundTask, order_by=[BackgroundTask.created_at, BackgroundTask.status])


def _seed_report(db, with_analysis=False, **analysis_overrides):
    seed_employees(db)
    report = add_report(db, 1, date(2025, 1, 6), text="Week report", report_id=REPORT_ID)
    analysis = add_analysis(db, report, **analysis_overrides) if with_analysis else None
    return report, analysis


# =========================================================================== POST /analyses/analyze/{report_id}

def test_analyze_new_report_creates_pending_task(api, db_session, snap, dispatch):
    _seed_report(db_session)
    resp = api.post(f"/analyses/analyze/{REPORT_ID}")
    snap("analyses_analyze_new", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_analyze_existing_analysis_returns_completed_task(api, db_session, snap, dispatch):
    _seed_report(db_session, with_analysis=True)
    resp = api.post(f"/analyses/analyze/{REPORT_ID}")
    snap("analyses_analyze_existing_analysis", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_analyze_active_task_with_analysis_is_reused(api, db_session, snap, dispatch):
    _seed_report(db_session, with_analysis=True)
    add_task(db_session, task_id=fixed_uuid(1), report_id=REPORT_ID, status="running")
    resp = api.post(f"/analyses/analyze/{REPORT_ID}")
    snap("analyses_analyze_active_task_reused", resp, db=_tasks(db_session), dispatch=dispatch.calls)


@pytest.mark.known_bug("B1")
def test_analyze_in_flight_task_without_analysis_is_marked_failed(api, db_session, snap, dispatch):
    _seed_report(db_session)
    add_task(db_session, task_id=fixed_uuid(1), report_id=REPORT_ID, status="running")
    resp = api.post(f"/analyses/analyze/{REPORT_ID}")
    snap("analyses_analyze_in_flight_marked_failed", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_analyze_unknown_report_404(api, db_session, snap, dispatch):
    resp = api.post(f"/analyses/analyze/{fixed_uuid(404)}")
    snap("analyses_analyze_unknown_report", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_analyze_invalid_uuid_400(api, db_session, snap, dispatch):
    resp = api.post("/analyses/analyze/not-a-uuid")
    snap("analyses_analyze_invalid_uuid", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_analyze_unexpected_error_500(api, db_session, snap, dispatch):
    _seed_report(db_session)
    with mock.patch("app.api.analyses.create_task_for_analysis", side_effect=RuntimeError("broker down")):
        resp = api.post(f"/analyses/analyze/{REPORT_ID}")
    snap("analyses_analyze_unexpected_error", resp, db=_tasks(db_session), dispatch=dispatch.calls)


# =========================================================================== GET /analyses/results/{report_id}

def test_results_by_report(api, db_session, snap):
    _seed_report(db_session, with_analysis=True)
    snap("analyses_results_by_report", api.get(f"/analyses/results/{REPORT_ID}"))


def test_results_by_report_defaults(api, db_session, snap):
    _seed_report(
        db_session, with_analysis=True, sentiment_score=None,
        credibility_rating=None, credibility_explanation=None, exaggeration_flags=None, consistency_score=None,
        performance_rating=None, performance_summary=None, performance_strengths=None,
        performance_improvement_areas=None,
    )
    snap("analyses_results_by_report_defaults", api.get(f"/analyses/results/{REPORT_ID}"))


@pytest.mark.known_bug("B3")
def test_results_by_report_missing_analysis_500(api, db_session, snap):
    _seed_report(db_session)
    snap("analyses_results_by_report_missing", api.get(f"/analyses/results/{REPORT_ID}"))


def test_results_by_report_invalid_uuid_400(api, snap):
    snap("analyses_results_by_report_invalid_uuid", api.get("/analyses/results/nope"))


# =========================================================================== GET /analyses/employee/{employee_id}

def test_employee_analyses(api, db_session, snap):
    report, _ = _seed_report(db_session, with_analysis=True)
    second = add_report(db_session, 1, date(2025, 1, 13), report_id=fixed_uuid(11))
    add_analysis(db_session, second, sentiment_score=0.3, risk_level="high", performance_rating="low")
    snap("analyses_employee_list", api.get("/analyses/employee/1"))


def test_employee_analyses_empty(api, db_session, snap):
    seed_employees(db_session)
    snap("analyses_employee_list_empty", api.get("/analyses/employee/2"))


@pytest.mark.known_bug("B3")
def test_employee_analyses_unknown_employee_500(api, snap):
    snap("analyses_employee_list_unknown", api.get("/analyses/employee/9"))


def test_employee_analyses_non_integer_422(api, snap):
    snap("analyses_employee_list_non_integer", api.get("/analyses/employee/abc"))


# =========================================================================== GET /analyses/{analysis_id}

def test_analysis_by_id(api, db_session, snap):
    _, analysis = _seed_report(db_session, with_analysis=True)
    snap("analyses_by_id", api.get(f"/analyses/{analysis.analysis_id}"))


@pytest.mark.known_bug("B3")
def test_analysis_by_id_missing_500(api, snap):
    snap("analyses_by_id_missing", api.get("/analyses/12345"))


def test_analysis_by_id_non_integer_422(api, snap):
    snap("analyses_by_id_non_integer", api.get("/analyses/abc"))


def test_analysis_by_id_bad_stored_shape_500(api, db_session, snap):
    _, analysis = _seed_report(db_session, with_analysis=True, topics={"not": "a list"})
    snap("analyses_by_id_bad_stored_shape", api.get(f"/analyses/{analysis.analysis_id}"))


# =========================================================================== POST /analyses/monthly/analyze

def test_monthly_analyze_new(api, db_session, snap, dispatch):
    seed_employees(db_session)
    resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_new", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_monthly_analyze_existing_analysis(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_monthly(db_session, 1, 2025, 2)
    resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_existing", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_monthly_analyze_active_task_with_analysis_reused(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_monthly(db_session, 1, 2025, 2)
    add_task(db_session, task_id=fixed_uuid(1), task_type="MONTHLY_ANALYSIS", employee_id=1, year=2025, month=2)
    resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_active_reused", resp, db=_tasks(db_session), dispatch=dispatch.calls)


@pytest.mark.known_bug("B1")
def test_monthly_analyze_in_flight_without_analysis_marked_failed(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_task(db_session, task_id=fixed_uuid(1), task_type="MONTHLY_ANALYSIS", employee_id=1, year=2025, month=2,
             status="running")
    resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_in_flight_failed", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_monthly_analyze_unknown_employee_404(api, db_session, snap, dispatch):
    resp = api.post("/analyses/monthly/analyze", params={"employee_id": 9, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_unknown_employee", resp, db=_tasks(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("params", [
    {"employee_id": 1, "year": 2025, "month": 13},
    {"employee_id": 1, "year": 1999, "month": 1},
    {"employee_id": 1, "month": 1},
    {"year": 2025, "month": 1},
], ids=["month13", "year1999", "no_year", "no_employee"])
def test_monthly_analyze_invalid_params_422(api, db_session, snap, dispatch, params, request):
    seed_employees(db_session)
    resp = api.post("/analyses/monthly/analyze", params=params)
    snap(f"analyses_monthly_analyze_invalid_{request.node.callspec.id}", resp, dispatch=dispatch.calls)


def test_monthly_analyze_unexpected_error_500(api, db_session, snap, dispatch):
    seed_employees(db_session)
    with mock.patch("app.api.analyses.create_task_for_monthly_analysis", side_effect=RuntimeError("boom")):
        resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_unexpected_error", resp, dispatch=dispatch.calls)


def test_monthly_analyze_value_error_400(api, db_session, snap, dispatch):
    seed_employees(db_session)
    with mock.patch("app.api.analyses.create_task_for_monthly_analysis", side_effect=ValueError("bad")):
        resp = api.post("/analyses/monthly/analyze", params={"employee_id": 1, "year": 2025, "month": 2})
    snap("analyses_monthly_analyze_value_error", resp, dispatch=dispatch.calls)


# =========================================================================== GET /analyses/monthly/{analysis_id}

def test_monthly_by_id(api, db_session, snap):
    seed_employees(db_session)
    monthly = add_monthly(db_session, 1, 2025, 2)
    snap("analyses_monthly_by_id", api.get(f"/analyses/monthly/{monthly.analysis_id}"))


def test_monthly_by_id_minimal_row_fails_validation(api, db_session, snap):
    seed_employees(db_session)
    monthly = add_monthly(db_session, 1, 2025, 2, full=False)
    snap("analyses_monthly_by_id_minimal", api.get(f"/analyses/monthly/{monthly.analysis_id}"))


@pytest.mark.known_bug("B3")
def test_monthly_by_id_missing_500(api, snap):
    snap("analyses_monthly_by_id_missing", api.get("/analyses/monthly/77"))


def test_monthly_by_id_non_integer_422(api, snap):
    snap("analyses_monthly_by_id_non_integer", api.get("/analyses/monthly/abc"))


# =========================================================================== GET /analyses/monthly/employee/{employee_id}

def test_monthly_for_employee(api, db_session, snap):
    seed_employees(db_session)
    add_monthly(db_session, 1, 2024, 12)
    add_monthly(db_session, 1, 2025, 2)
    add_monthly(db_session, 1, 2025, 1, monthly_achievements=None, recurring_challenges=None)
    add_monthly(db_session, 2, 2025, 1)
    snap("analyses_monthly_for_employee", api.get("/analyses/monthly/employee/1"))


def test_monthly_for_employee_empty(api, db_session, snap):
    seed_employees(db_session)
    snap("analyses_monthly_for_employee_empty", api.get("/analyses/monthly/employee/3"))


@pytest.mark.known_bug("B3")
def test_monthly_for_employee_unknown_500(api, snap):
    snap("analyses_monthly_for_employee_unknown", api.get("/analyses/monthly/employee/9"))


# =========================================================================== GET /analyses/monthly/employee/{id}/{year}/{month}

def test_monthly_by_period(api, db_session, snap):
    seed_employees(db_session)
    add_monthly(db_session, 1, 2025, 2)
    snap("analyses_monthly_by_period", api.get("/analyses/monthly/employee/1/2025/2"))


@pytest.mark.known_bug("B3")
def test_monthly_by_period_missing_500(api, db_session, snap):
    seed_employees(db_session)
    snap("analyses_monthly_by_period_missing", api.get("/analyses/monthly/employee/1/2025/3"))


@pytest.mark.known_bug("B3")
def test_monthly_by_period_unknown_employee_500(api, snap):
    snap("analyses_monthly_by_period_unknown_employee", api.get("/analyses/monthly/employee/9/2025/3"))


def test_monthly_by_period_unvalidated_month(api, db_session, snap):
    seed_employees(db_session)
    snap("analyses_monthly_by_period_month13", api.get("/analyses/monthly/employee/1/2025/13"))


# =========================================================================== POST /analyses/quarterly/analyze

def test_quarterly_analyze_new(api, db_session, snap, dispatch):
    seed_employees(db_session)
    resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 1, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_new", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_quarterly_analyze_existing_analysis(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_quarterly(db_session, 1, 2025, 1)
    resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 1, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_existing", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_quarterly_analyze_active_task_with_analysis_reused(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_quarterly(db_session, 1, 2025, 1)
    add_task(db_session, task_id=fixed_uuid(1), task_type="QUARTERLY_ANALYSIS", employee_id=1, year=2025, quarter=1)
    resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 1, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_active_reused", resp, db=_tasks(db_session), dispatch=dispatch.calls)


@pytest.mark.known_bug("B1")
def test_quarterly_analyze_in_flight_without_analysis_marked_failed(api, db_session, snap, dispatch):
    seed_employees(db_session)
    add_task(db_session, task_id=fixed_uuid(1), task_type="QUARTERLY_ANALYSIS", employee_id=1, year=2025, quarter=1)
    resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 1, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_in_flight_failed", resp, db=_tasks(db_session), dispatch=dispatch.calls)


def test_quarterly_analyze_unknown_employee_404(api, db_session, snap, dispatch):
    resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 9, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_unknown_employee", resp, db=_tasks(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("params", [
    {"employee_id": 1, "year": 2025, "quarter": 5},
    {"employee_id": 1, "year": 2101, "quarter": 1},
    {"employee_id": 1, "year": 2025},
], ids=["quarter5", "year2101", "no_quarter"])
def test_quarterly_analyze_invalid_params_422(api, db_session, snap, dispatch, params, request):
    seed_employees(db_session)
    resp = api.post("/analyses/quarterly/analyze", params=params)
    snap(f"analyses_quarterly_analyze_invalid_{request.node.callspec.id}", resp, dispatch=dispatch.calls)


def test_quarterly_analyze_unexpected_error_500(api, db_session, snap, dispatch):
    seed_employees(db_session)
    with mock.patch("app.api.analyses.create_task_for_quarterly_analysis", side_effect=RuntimeError("boom")):
        resp = api.post("/analyses/quarterly/analyze", params={"employee_id": 1, "year": 2025, "quarter": 1})
    snap("analyses_quarterly_analyze_unexpected_error", resp, dispatch=dispatch.calls)


# =========================================================================== GET /analyses/quarterly/{analysis_id}

def test_quarterly_by_id(api, db_session, snap):
    seed_employees(db_session)
    quarterly = add_quarterly(db_session, 1, 2025, 1)
    snap("analyses_quarterly_by_id", api.get(f"/analyses/quarterly/{quarterly.analysis_id}"))


def test_quarterly_by_id_minimal_row_fails_validation(api, db_session, snap):
    seed_employees(db_session)
    quarterly = add_quarterly(db_session, 1, 2025, 1, full=False)
    snap("analyses_quarterly_by_id_minimal", api.get(f"/analyses/quarterly/{quarterly.analysis_id}"))


@pytest.mark.known_bug("B3")
def test_quarterly_by_id_missing_500(api, snap):
    snap("analyses_quarterly_by_id_missing", api.get("/analyses/quarterly/77"))


# =========================================================================== GET /analyses/quarterly/employee/{id}/{year}/{quarter}

def test_quarterly_by_period(api, db_session, snap):
    seed_employees(db_session)
    add_quarterly(db_session, 1, 2025, 1)
    snap("analyses_quarterly_by_period", api.get("/analyses/quarterly/employee/1/2025/1"))


@pytest.mark.known_bug("B3")
def test_quarterly_by_period_missing_500(api, db_session, snap):
    seed_employees(db_session)
    snap("analyses_quarterly_by_period_missing", api.get("/analyses/quarterly/employee/1/2025/2"))


@pytest.mark.known_bug("B3")
def test_quarterly_by_period_unknown_employee_500(api, snap):
    snap("analyses_quarterly_by_period_unknown_employee", api.get("/analyses/quarterly/employee/9/2025/2"))


@pytest.mark.parametrize("path", ["/analyses/quarterly/employee/1/2025/5", "/analyses/quarterly/employee/1/1999/1"],
                         ids=["quarter5", "year1999"])
def test_quarterly_by_period_invalid_path_422(api, db_session, snap, path, request):
    seed_employees(db_session)
    snap(f"analyses_quarterly_by_period_invalid_{request.node.callspec.id}", api.get(path))
