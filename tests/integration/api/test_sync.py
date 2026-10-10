"""Characterization of the /sync router.

celery_app.send_task is patched in conftest; create_sqlserver_connector is
patched per test so SQL Server is never contacted.
"""
from datetime import datetime, timedelta
from unittest import mock

import pytest

from app.models.sync_models import SyncHistory
from tests.integration.api.seed import add_sync, dump_rows, fixed_uuid, seed_sync_history
from tests.support.scrub import scrub

SYNC_TYPES = ["employee_reports", "vision_data", "job_descriptions", "supervisor_feedback"]


def _history(db):
    return dump_rows(db, SyncHistory, order_by=[SyncHistory.started_at, SyncHistory.sync_type])


def _resp(resp):
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    return {"status": resp.status_code, "body": body}


# =========================================================================== POST /sync/trigger/{type}

@pytest.mark.parametrize("is_full_sync", [None, "false", "true"], ids=["default", "incremental", "full"])
@pytest.mark.parametrize("sync_type", SYNC_TYPES)
def test_trigger_creates_pending_sync(api, db_session, snap, dispatch, sync_type, is_full_sync):
    params = {} if is_full_sync is None else {"is_full_sync": is_full_sync}
    resp = api.post(f"/sync/trigger/{sync_type}", params=params)
    label = {None: "default", "false": "incremental", "true": "full"}[is_full_sync]
    snap(f"sync_trigger_{sync_type}_{label}", resp,
         db=_history(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("running_status", ["pending", "running"])
@pytest.mark.parametrize("sync_type", SYNC_TYPES)
def test_trigger_conflicts_with_recent_in_flight_sync(api, db_session, snap, dispatch, sync_type, running_status):
    add_sync(db_session, sync_type=sync_type, status=running_status, sync_id=fixed_uuid(1),
             started_at=datetime.now() - timedelta(minutes=5))
    resp = api.post(f"/sync/trigger/{sync_type}")
    snap(f"sync_trigger_{sync_type}_conflict_{running_status}", resp, db=_history(db_session),
         dispatch=dispatch.calls)


@pytest.mark.parametrize("sync_type", SYNC_TYPES)
def test_trigger_clears_stale_sync_then_starts(api, db_session, snap, dispatch, sync_type):
    add_sync(db_session, sync_type=sync_type, status="running", sync_id=fixed_uuid(1),
             started_at=datetime.now() - timedelta(minutes=61))
    resp = api.post(f"/sync/trigger/{sync_type}", params={"is_full_sync": "true"})
    snap(f"sync_trigger_{sync_type}_stale_cleared", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_other_type_in_flight_does_not_block(api, db_session, snap, dispatch):
    add_sync(db_session, sync_type="vision_data", status="running", sync_id=fixed_uuid(1),
             started_at=datetime.now() - timedelta(minutes=5))
    resp = api.post("/sync/trigger/employee_reports")
    snap("sync_trigger_other_type_running", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_completed_and_failed_syncs_do_not_block(api, db_session, snap, dispatch):
    add_sync(db_session, sync_type="employee_reports", status="completed", sync_id=fixed_uuid(1))
    add_sync(db_session, sync_type="employee_reports", status="failed", sync_id=fixed_uuid(2),
             started_at=datetime(2025, 3, 14, 10, 0))
    resp = api.post("/sync/trigger/employee_reports")
    snap("sync_trigger_finished_syncs_ignored", resp, db=_history(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("sync_type", SYNC_TYPES)
def test_trigger_invalid_flag_422(api, db_session, snap, dispatch, sync_type):
    resp = api.post(f"/sync/trigger/{sync_type}", params={"is_full_sync": "maybe"})
    snap(f"sync_trigger_{sync_type}_invalid_flag", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_unknown_type_404(api, snap):
    snap("sync_trigger_unknown_type", api.post("/sync/trigger/payroll"))


def test_trigger_get_method_not_allowed(api, snap):
    snap("sync_trigger_get_405", api.get("/sync/trigger/vision_data"))


def test_trigger_dispatch_failure_500_leaves_pending_row(api, db_session, snap, dispatch):
    with mock.patch("app.api.sync_routes.celery_app") as broken:
        broken.send_task.side_effect = RuntimeError("broker unreachable")
        resp = api.post("/sync/trigger/vision_data")
    snap("sync_trigger_dispatch_failure", resp, db=_history(db_session))


# =========================================================================== POST /sync/trigger/full

def test_trigger_full(api, db_session, snap, dispatch):
    resp = api.post("/sync/trigger/full")
    snap("sync_trigger_full", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_full_ignores_is_full_sync_param(api, db_session, snap, dispatch):
    resp = api.post("/sync/trigger/full", params={"is_full_sync": "false"})
    snap("sync_trigger_full_with_param", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_full_conflict_lists_running_types(api, db_session, snap, dispatch):
    recent = datetime.now() - timedelta(minutes=5)
    add_sync(db_session, sync_type="vision_data", status="running", sync_id=fixed_uuid(1), started_at=recent)
    add_sync(db_session, sync_type="supervisor_feedback", status="pending", sync_id=fixed_uuid(2),
             started_at=recent + timedelta(seconds=1))
    resp = api.post("/sync/trigger/full")
    snap("sync_trigger_full_conflict", resp, db=_history(db_session), dispatch=dispatch.calls)


def test_trigger_full_clears_stale_syncs_of_every_type(api, db_session, snap, dispatch):
    stale = datetime.now() - timedelta(hours=3)
    for i, sync_type in enumerate(SYNC_TYPES, start=1):
        add_sync(db_session, sync_type=sync_type, status="running" if i % 2 else "pending",
                 sync_id=fixed_uuid(i), started_at=stale + timedelta(seconds=i))
    resp = api.post("/sync/trigger/full")
    snap("sync_trigger_full_stale_cleared", resp, db=_history(db_session), dispatch=dispatch.calls)


# =========================================================================== GET /sync/status/{sync_id}

def test_status_completed(api, db_session, snap):
    add_sync(db_session, sync_id=fixed_uuid(1), status="completed",
             started_at=datetime(2025, 3, 14, 9, 0, 0), completed_at=datetime(2025, 3, 14, 9, 0, 5, 700000),
             last_sync_timestamp=datetime(2025, 3, 13, 23, 0, 0), records_queried=3, records_synced=2,
             records_created=1, records_updated=1, records_skipped=1, error_count=1,
             error_message=None, sync_options={"is_full_sync": True},
             sync_metadata={"reports_created": 1, "employees_updated": 2})
    snap("sync_status_completed", api.get(f"/sync/status/{fixed_uuid(1)}"))


def test_status_pending_without_options(api, db_session, snap):
    add_sync(db_session, sync_id=fixed_uuid(1), status="pending", sync_type="vision_data",
             records_queried=None, records_synced=None, sync_options=None, sync_metadata=None)
    snap("sync_status_pending_no_options", api.get(f"/sync/status/{fixed_uuid(1)}"))


def test_status_failed_with_message(api, db_session, snap):
    add_sync(db_session, sync_id=fixed_uuid(1), status="failed", sync_type="job_descriptions",
             error_message="Login failed", sync_options={"is_full_sync": False}, records_queried=0)
    snap("sync_status_failed", api.get(f"/sync/status/{fixed_uuid(1)}"))


def test_status_partial(api, db_session, snap):
    add_sync(db_session, sync_id=fixed_uuid(1), status="partial", sync_type="vision_data",
             records_queried=10, records_synced=8)
    snap("sync_status_partial", api.get(f"/sync/status/{fixed_uuid(1)}"))


def test_status_not_found_404(api, snap):
    snap("sync_status_missing", api.get(f"/sync/status/{fixed_uuid(404)}"))


def test_status_invalid_uuid_422(api, snap):
    snap("sync_status_invalid_uuid", api.get("/sync/status/abc"))


# =========================================================================== GET /sync/last-successful/{sync_type}

@pytest.mark.parametrize("sync_type", SYNC_TYPES)
def test_last_successful_none(api, snap, sync_type):
    snap(f"sync_last_successful_{sync_type}_none", api.get(f"/sync/last-successful/{sync_type}"))


def test_last_successful_picks_latest_watermark(api, db_session, snap):
    add_sync(db_session, sync_id=fixed_uuid(1), status="completed", records_synced=10,
             last_sync_timestamp=datetime(2025, 1, 1), completed_at=datetime(2025, 1, 2))
    add_sync(db_session, sync_id=fixed_uuid(2), status="completed", records_synced=20,
             last_sync_timestamp=datetime(2025, 2, 1), completed_at=datetime(2025, 2, 2))
    add_sync(db_session, sync_id=fixed_uuid(3), status="failed", last_sync_timestamp=datetime(2025, 3, 1))
    add_sync(db_session, sync_id=fixed_uuid(4), status="partial", last_sync_timestamp=datetime(2025, 4, 1))
    add_sync(db_session, sync_id=fixed_uuid(5), status="completed", last_sync_timestamp=None)
    add_sync(db_session, sync_id=fixed_uuid(6), status="completed", sync_type="vision_data",
             last_sync_timestamp=datetime(2025, 5, 1))
    resp = api.get("/sync/last-successful/employee_reports")
    snap("sync_last_successful_latest", resp, expected_sync_id=str(fixed_uuid(2)))


def test_last_successful_invalid_type_400(api, snap):
    snap("sync_last_successful_invalid", api.get("/sync/last-successful/full"))


# =========================================================================== GET /sync/history

def test_history_empty(api, snap):
    snap("sync_history_empty", api.get("/sync/history"))


def test_history_default(api, db_session, snap):
    seed_sync_history(db_session)
    snap("sync_history_default", api.get("/sync/history"))


HISTORY_CASES = {
    "type_vision_data": {"sync_type": "vision_data"},
    "status_failed": {"status": "failed"},
    "status_running_none": {"status": "running"},
    "type_and_status": {"sync_type": "employee_reports", "status": "completed"},
    "start_date": {"start_date": "2025-01-04T00:00:00"},
    "end_date": {"end_date": "2025-01-02T12:00:00"},
    "date_window": {"start_date": "2025-01-02", "end_date": "2025-01-04T23:59:59"},
    "page1_size2": {"page": 1, "page_size": 2},
    "page3_size2": {"page": 3, "page_size": 2},
    "page_past_end": {"page": 9, "page_size": 2},
    "sort_asc": {"sort_order": "asc"},
    "sort_unknown_order_is_asc": {"sort_order": "sideways"},
    "sort_desc_uppercase": {"sort_order": "DESC"},
    "sort_records_synced_desc": {"sort_by": "records_synced"},
    "sort_records_queried_asc_page2": {"sort_by": "records_queried", "sort_order": "asc", "page": 2, "page_size": 3},
}


def test_history_filters_and_pagination(api, db_session, snapshot):
    seed_sync_history(db_session)
    results = {name: _resp(api.get("/sync/history", params=params)) for name, params in HISTORY_CASES.items()}
    snapshot("sync_history_filters", scrub(results))


@pytest.mark.known_bug("B2")
@pytest.mark.parametrize("flag", ["true", "false"])
def test_history_is_full_sync_filter_500(api, db_session, snap, flag):
    seed_sync_history(db_session)
    snap(f"sync_history_is_full_sync_{flag}", api.get("/sync/history", params={"is_full_sync": flag}))


@pytest.mark.known_bug("B2")
@pytest.mark.parametrize("sort_by", ["nope", "__table__"])
def test_history_unvalidated_sort_by_500(api, db_session, snap, sort_by):
    seed_sync_history(db_session)
    snap(f"sync_history_sort_by_{sort_by.strip('_')}", api.get("/sync/history", params={"sort_by": sort_by}))


def test_history_includes_partial_rows(api, db_session, snapshot):
    seed_sync_history(db_session)
    add_sync(db_session, status="partial", sync_id=fixed_uuid(1), started_at=datetime(2025, 2, 1))
    results = {
        "status_partial": _resp(api.get("/sync/history", params={"status": "partial"})),
        "unfiltered": _resp(api.get("/sync/history")),
        "partial_not_on_page": _resp(api.get("/sync/history", params={"sort_order": "asc", "page_size": 2})),
    }
    snapshot("sync_history_partial_row", scrub(results))


@pytest.mark.parametrize("params", [
    {"sync_type": "full"},
    {"status": "done"},
    {"page": 0},
    {"page_size": 101},
    {"start_date": "yesterday"},
    {"is_full_sync": "maybe"},
], ids=["bad_type_400", "bad_status_400", "page0_422", "page_size101_422", "bad_date_422", "bad_flag_422"])
def test_history_invalid_input(api, snap, params, request):
    snap(f"sync_history_invalid_{request.node.callspec.id}", api.get("/sync/history", params=params))


# =========================================================================== GET /sync/{sync_id}/errors

def _seed_errors(db, error_details):
    add_sync(db, sync_id=fixed_uuid(1), status="failed", error_count=5, error_details=error_details)


ERRORS = {"errors": [
    {"row_number": 1, "field_name": "Name", "error_message": "missing", "error_category": "validation",
     "row_data": {"Name": None}},
    {"row_number": 4, "error_message": "bad date"},
    {"field_name": "BPS"},
    {"row_number": 9, "error_message": "dup", "row_data": {"id": 9}},
    {"row_number": 12, "error_message": "late", "error_category": "db"},
]}


def test_errors_default_page(api, db_session, snap):
    _seed_errors(db_session, ERRORS)
    snap("sync_errors_default", api.get(f"/sync/{fixed_uuid(1)}/errors"))


@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_errors_pagination(api, db_session, snap, page):
    _seed_errors(db_session, ERRORS)
    snap(f"sync_errors_page_{page}", api.get(f"/sync/{fixed_uuid(1)}/errors", params={"page": page, "page_size": 2}))


@pytest.mark.parametrize("details", [None, {}, {"errors": []}, {"other": [1]}, ["not", "a", "dict"]],
                         ids=["null", "empty_dict", "empty_list", "no_errors_key", "list_payload"])
def test_errors_without_error_list(api, db_session, snap, details, request):
    _seed_errors(db_session, details)
    snap(f"sync_errors_none_{request.node.callspec.id}", api.get(f"/sync/{fixed_uuid(1)}/errors"))


def test_errors_not_found_404(api, snap):
    snap("sync_errors_missing", api.get(f"/sync/{fixed_uuid(404)}/errors"))


@pytest.mark.parametrize("path,params", [
    ("/sync/abc/errors", {}),
    (f"/sync/{fixed_uuid(1)}/errors", {"page": 0}),
    (f"/sync/{fixed_uuid(1)}/errors", {"page_size": 1001}),
], ids=["bad_uuid", "page0", "page_size1001"])
def test_errors_invalid_input_422(api, snap, path, params, request):
    snap(f"sync_errors_invalid_{request.node.callspec.id}", api.get(path, params=params))


# =========================================================================== GET /sync/config, /sync/test-connection

def _connector(connected=True):
    connector = mock.MagicMock(name="SQLServerConnector")
    connector.server = "sql.test.local\\SQLEXPRESS"
    connector.database = "EmployeeTestDB"
    connector.max_batch_size = 5000
    connector.test_connection.return_value = connected
    connector.get_allowed_tables.return_value = {"dbo.Reports", "dbo.VisionData", "dbo.JD"}
    connector.get_allowed_timestamp_columns.return_value = {"Modified_At", "Created_At"}
    return connector


def _sorted_lists(body):
    """Allowed tables/columns come from Python sets: their order is unspecified."""
    if isinstance(body, dict):
        for key in ("allowed_tables", "allowed_timestamp_columns", "available_tables"):
            if isinstance(body.get(key), list):
                body[key] = sorted(body[key])
    return body


@pytest.fixture
def no_sync_env(monkeypatch):
    monkeypatch.delenv("SYNC_ENABLED", raising=False)
    monkeypatch.delenv("SYNC_ERROR_THRESHOLD_PERCENT", raising=False)


def test_config_connected(api, snapshot, no_sync_env):
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=_connector(True)):
        resp = api.get("/sync/config")
    snapshot("sync_config_connected", scrub({"status": resp.status_code, "body": _sorted_lists(resp.json())}))


def test_config_disconnected_and_env_overrides(api, snapshot, monkeypatch):
    monkeypatch.setenv("SYNC_ENABLED", "FALSE")
    monkeypatch.setenv("SYNC_ERROR_THRESHOLD_PERCENT", "2.5")
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=_connector(False)):
        resp = api.get("/sync/config")
    snapshot("sync_config_disconnected_env", scrub({"status": resp.status_code, "body": _sorted_lists(resp.json())}))


def test_config_connector_raises_500(api, snap, no_sync_env):
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", side_effect=RuntimeError("ODBC driver missing")):
        snap("sync_config_error", api.get("/sync/config"))


def test_config_invalid_threshold_env_500(api, snap, monkeypatch):
    monkeypatch.setenv("SYNC_ERROR_THRESHOLD_PERCENT", "ten")
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=_connector(True)):
        snap("sync_config_bad_threshold_env", api.get("/sync/config"))


def _fake_clock():
    clock = mock.MagicMock(name="time")
    clock.time.side_effect = [1000.0, 1000.25]
    return clock


def test_test_connection_success(api, snapshot):
    connector = _connector(True)
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=connector), \
            mock.patch("app.api.sync_routes.time", _fake_clock()):
        resp = api.get("/sync/test-connection")
    snapshot("sync_test_connection_success",
             scrub({"status": resp.status_code, "body": _sorted_lists(resp.json()),
                    "test_connection_calls": connector.test_connection.call_count}))


def test_test_connection_failed(api, snapshot):
    connector = _connector(False)
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=connector), \
            mock.patch("app.api.sync_routes.time", _fake_clock()):
        resp = api.get("/sync/test-connection")
    snapshot("sync_test_connection_disconnected",
             scrub({"status": resp.status_code, "body": resp.json(),
                    "get_allowed_tables_calls": connector.get_allowed_tables.call_count}))


def test_test_connection_factory_raises_returns_200(api, snap):
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", side_effect=RuntimeError("ODBC driver missing")):
        snap("sync_test_connection_factory_error", api.get("/sync/test-connection"))


def test_test_connection_probe_raises_returns_200(api, snap):
    connector = _connector(True)
    connector.test_connection.side_effect = TimeoutError("login timeout")
    with mock.patch("app.api.sync_routes.create_sqlserver_connector", return_value=connector):
        snap("sync_test_connection_probe_error", api.get("/sync/test-connection"))
