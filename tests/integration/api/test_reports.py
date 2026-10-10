"""Characterization of the /reports router (vector store patched in conftest)."""
from datetime import date

from unittest import mock

from app.models.db_models import Report
from tests.integration.api.seed import add_report, dump_rows, fixed_uuid, seed_employees


class _FixedDate(date):
    @classmethod
    def today(cls):
        return date(2025, 3, 14)


def _reports(db):
    return dump_rows(db, Report, order_by=[Report.employee_id, Report.report_date])


# --------------------------------------------------------------------------- POST /reports/create

def test_create_report(api, db_session, snap, vector_store, dispatch):
    seed_employees(db_session)
    resp = api.post("/reports/create", json={"employee_id": 1, "report_date": "2025-03-10", "report_text": "Did things"})
    snap("reports_create", resp, db=_reports(db_session), vector_store=vector_store.calls, dispatch=dispatch.calls)


def test_create_report_unknown_employee_404(api, db_session, snap, vector_store):
    resp = api.post("/reports/create", json={"employee_id": 42, "report_date": "2025-03-10", "report_text": "x"})
    snap("reports_create_unknown_employee", resp, db=_reports(db_session), vector_store=vector_store.calls)


def test_create_report_duplicate_date_500(api, db_session, snap, vector_store):
    seed_employees(db_session)
    add_report(db_session, 1, date(2025, 3, 10), text="first", report_id=fixed_uuid(1))
    resp = api.post("/reports/create", json={"employee_id": 1, "report_date": "2025-03-10", "report_text": "second"})
    snap("reports_create_duplicate", resp, db=_reports(db_session), vector_store=vector_store.calls)


def test_create_report_vector_store_failure_is_swallowed(api, db_session, snap, vector_store):
    seed_employees(db_session)
    vector_store.side_effect = RuntimeError("qdrant down")
    resp = api.post("/reports/create", json={"employee_id": 2, "report_date": "2025-03-11", "report_text": "ok"})
    snap("reports_create_vector_store_error", resp, db=_reports(db_session))


def test_create_report_invalid_date_422(api, db_session, snap):
    seed_employees(db_session)
    resp = api.post("/reports/create", json={"employee_id": 1, "report_date": "10/03/2025", "report_text": "x"})
    snap("reports_create_invalid_date", resp, db=_reports(db_session))


def test_create_report_missing_fields_422(api, snap):
    snap("reports_create_missing_fields", api.post("/reports/create", json={"employee_id": 1}))


# --------------------------------------------------------------------------- POST /reports/form

FORM = {
    "employee_id": 1,
    "key_tasks_completed": "Closed 5 tickets",
    "impact_outcome": "Faster support",
    "challenges_faced": "None",
    "support_required": "No",
    "tasks_planned_next_week": "Refactor",
    "confidence_level": 4,
}


def test_submit_form(api, db_session, snap, vector_store):
    seed_employees(db_session)
    with mock.patch("app.api.reports.date", _FixedDate):
        resp = api.post("/reports/form", json=FORM)
    snap("reports_form", resp, db=_reports(db_session), vector_store=vector_store.calls)


def test_submit_form_nothing_to_report(api, db_session, snap, vector_store):
    seed_employees(db_session)
    with mock.patch("app.api.reports.date", _FixedDate):
        resp = api.post("/reports/form", json={"employee_id": 2, "nothing_to_report_reason": "On leave"})
    snap("reports_form_nothing_to_report", resp, db=_reports(db_session), vector_store=vector_store.calls)


def test_submit_form_requires_tasks_or_reason_422(api, db_session, snap):
    seed_employees(db_session)
    resp = api.post("/reports/form", json={"employee_id": 1, "impact_outcome": "only this"})
    snap("reports_form_missing_tasks_and_reason", resp, db=_reports(db_session))


def test_submit_form_confidence_out_of_range_422(api, db_session, snap):
    seed_employees(db_session)
    resp = api.post("/reports/form", json={**FORM, "confidence_level": 6})
    snap("reports_form_confidence_out_of_range", resp, db=_reports(db_session))


def test_submit_form_unknown_employee_404(api, db_session, snap, vector_store):
    resp = api.post("/reports/form", json={**FORM, "employee_id": 77})
    snap("reports_form_unknown_employee", resp, db=_reports(db_session), vector_store=vector_store.calls)


def test_submit_form_twice_same_day_500(api, db_session, snap, vector_store):
    seed_employees(db_session)
    with mock.patch("app.api.reports.date", _FixedDate):
        first = api.post("/reports/form", json=FORM)
        second = api.post("/reports/form", json=FORM)
    assert first.status_code == 200
    snap("reports_form_duplicate_day", second, db=_reports(db_session), vector_store=vector_store.calls)


def test_submit_form_vector_store_failure_is_swallowed(api, db_session, snap, vector_store):
    seed_employees(db_session)
    vector_store.side_effect = RuntimeError("qdrant down")
    with mock.patch("app.api.reports.date", _FixedDate):
        resp = api.post("/reports/form", json=FORM)
    snap("reports_form_vector_store_error", resp, db=_reports(db_session))


# --------------------------------------------------------------------------- GET /reports/{employee_id}

def test_get_reports_for_employee(api, db_session, snap):
    seed_employees(db_session)
    add_report(db_session, 1, date(2025, 1, 6), text="week 2", report_id=fixed_uuid(2))
    add_report(db_session, 1, date(2024, 12, 30), text="week 1", report_id=fixed_uuid(1))
    add_report(db_session, 2, date(2025, 1, 6), text="bob", report_id=fixed_uuid(3))
    snap("reports_get_for_employee", api.get("/reports/1"))


def test_get_reports_employee_without_reports(api, db_session, snap):
    seed_employees(db_session)
    snap("reports_get_no_reports", api.get("/reports/3"))


def test_get_reports_unknown_employee_404(api, snap):
    snap("reports_get_unknown_employee", api.get("/reports/5"))


def test_get_reports_non_integer_id_422(api, snap):
    snap("reports_get_non_integer", api.get("/reports/abc"))
