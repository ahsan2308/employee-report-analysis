"""Legacy integration suites carried over from app/tests/.

They run against the disposable Postgres. A few tests construct a real
SQLServerConnector (needs the Microsoft ODBC driver and a reachable SQL
Server), so they are marked ``sqlserver`` and deselected by default.
"""
import pytest

NEEDS_SQLSERVER = {
    "test_full_sync_service.py::TestSQLServerConnectivity",
    "test_full_sync_service.py::TestSyncServiceIntegration",
    "test_full_sync_service.py::TestIncrementalSync::test_incremental_vs_full_sync_detection",
    "test_jd_sync_comprehensive.py::TestPhase5SyncTasks::test_task_metrics_extraction",
    "test_jd_sync_comprehensive.py::TestPhase5SyncTasks::test_task_return_no_timestamps",
    "test_jd_sync_final.py::TestPhase5CeleryTasks::test_task_direct_call",
    "test_jd_sync_service_final.py::TestErrorHandling::test_sql_server_connection_failure",
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        nodeid = item.nodeid.split("tests/integration/legacy/")[-1]
        if any(nodeid == key or nodeid.startswith(key + "::") for key in NEEDS_SQLSERVER):
            item.add_marker(pytest.mark.sqlserver)


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
