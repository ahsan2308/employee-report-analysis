"""Characterization of GET / and the /employees router."""
from unittest import mock

from app.models.db_models import Employee
from tests.integration.api.seed import dump_rows, seed_employees


def test_root(api, snap):
    snap("root", api.get("/"))


def test_list_employees_empty_db_returns_404(api, snap):
    snap("employees_list_empty", api.get("/employees/"))


def test_list_employees_seeded(api, db_session, snap):
    seed_employees(db_session)
    snap("employees_list_seeded", api.get("/employees/"))


def test_list_employees_without_trailing_slash_redirects(api, db_session, snap):
    seed_employees(db_session)
    resp = api.get("/employees", follow_redirects=False)
    snap("employees_list_no_slash", resp, location=resp.headers.get("location"))


def test_create_employee(api, db_session, snap, dispatch):
    resp = api.post("/employees/", json={"name": "Dana Dev", "wing": "Ops", "position": "SRE"})
    snap("employees_create", resp, db=dump_rows(db_session, Employee), dispatch=dispatch.calls)


def test_create_employee_ignores_extra_fields(api, db_session, snap):
    resp = api.post("/employees/", json={"name": "Eve", "wing": "HR", "position": "Partner", "id": 99})
    snap("employees_create_extra_field", resp, db=dump_rows(db_session, Employee))


def test_create_employee_missing_field_422(api, db_session, snap):
    resp = api.post("/employees/", json={"name": "No Wing", "position": "x"})
    snap("employees_create_missing_field", resp, db=dump_rows(db_session, Employee))


def test_create_employee_wrong_type_422(api, db_session, snap):
    resp = api.post("/employees/", json={"name": 123, "wing": "Ops", "position": "SRE"})
    snap("employees_create_wrong_type", resp, db=dump_rows(db_session, Employee))


def test_create_employee_empty_body_422(api, snap):
    snap("employees_create_no_body", api.post("/employees/"))


def test_create_employee_unexpected_error_500(api, db_session, snap):
    with mock.patch("app.api.employees.Employee", side_effect=RuntimeError("boom")):
        resp = api.post("/employees/", json={"name": "Dana Dev", "wing": "Ops", "position": "SRE"})
    snap("employees_create_error", resp, db=dump_rows(db_session, Employee))
