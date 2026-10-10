"""Characterization of the DB-free parts of app/services/sync_service.py.

The SQL Server connector, the PostgreSQL database and the row processor are all
mocks; SyncService is built with __new__ so get_database() is never called.
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pyodbc as real_pyodbc
import pytest

from app.database import sqlserver_connector as connector_module
from app.services import sync_service as sync_module
from app.services.csv.error_handler import ImportErrorHandler
from app.services.sync_service import SyncService, create_sync_service
from tests.golden.imports_sync.helpers import df_snapshot, handler_errors, outcome, tag


def _service(tables=None, ts_columns=None, threshold=10.0):
    svc = SyncService.__new__(SyncService)
    svc.sqlserver_connector = MagicMock(name="connector")
    svc.sqlserver_connector.get_allowed_tables.return_value = tables
    svc.sqlserver_connector.get_allowed_timestamp_columns.return_value = ts_columns
    svc.error_threshold_percent = threshold
    return svc


FINDERS = ["_get_employee_reports_table_name", "_get_vision_data_table_name",
           "_get_job_descriptions_table_name", "_get_supervisor_feedback_table_name"]

# Lists (not sets) so that the first-match order is deterministic in the snapshot.
TABLE_LISTS = {
    "defaults_sorted": ["EmployeeJobDescriptions", "EmployeeReports", "SupervisorFeedback", "VisionEmployeeData"],
    "defaults_reversed": ["VisionEmployeeData", "SupervisorFeedback", "EmployeeReports", "EmployeeJobDescriptions"],
    "lowercase_schema_qualified": ["dbo.employeereports", "dbo.visionemployeedata", "dbo.jobdescriptions",
                                   "dbo.supervisorfeedback"],
    "feedback_report_first": ["SupervisorFeedbackReport", "EmployeeReports", "VisionEmployeeData", "JD_Table"],
    "jd_substring_traps": ["AdjustedReports", "Vision", "Feedback"],
    "vision_job_combo_first": ["VisionJobData", "EmployeeReports"],
    "reporting_word": ["Reporting_Staging", "EmployeeReports"],
    "empty": [],
    "unrelated": ["Users", "Audit"],
}


def test_table_name_discovery(snapshot):
    out = {}
    for name, tables in TABLE_LISTS.items():
        svc = _service(tables=tables)
        out[name] = {finder: outcome(getattr(svc, finder)) for finder in FINDERS}
    snapshot("sync_table_name_discovery", out)


def test_table_name_discovery_with_real_default_set(snapshot):
    # The real connector returns a set; with the defaults each finder has exactly one match.
    svc = _service(tables=set(connector_module.SQLServerConnector.DEFAULT_ALLOWED_TABLES))
    snapshot("sync_table_name_discovery_default_set", {f: outcome(getattr(svc, f)) for f in FINDERS})


def test_find_timestamp_column(snapshot):
    allowed = {"LastModifiedDate", "ModifiedDate", "UpdatedAt"}
    schemas = {
        "first_allowed_in_schema_order": {"Employee_ID": "int", "ModifiedDate": "datetime", "LastModifiedDate": "x"},
        "none": {"Employee_ID": "int"},
        "case_mismatch": {"lastmodifieddate": "datetime"},
        "empty": {},
    }
    svc = _service(ts_columns=allowed)
    snapshot("sync_find_timestamp_column", {k: svc._find_timestamp_column(v) for k, v in schemas.items()})


EMP_ROW = {
    "Employee_ID": 101, "Name": "Ayesha Khan", "Designation": "Officer", "BPS": "BS-17", "Office_Hierarchy": "A>B",
    "From": date(2024, 3, 1), "To": date(2024, 3, 31), "Draft": None, "Tasks_Completed": "x", "Impact": None,
    "Challenges": None, "Support_Required": None, "Tasks_Planned": None, "Confidence_Level": "3", "NTR": None,
    "LastModifiedDate": datetime(2024, 4, 1, 10, 0, 0, 999000),
}
VISION_ROW = {
    "Employee_ID": 101, "From_Date": date(2024, 4, 1), "To_Date": date(2024, 4, 30), "Main_Entity": "Persons",
    "Sub_Entities": "Persons:1", "Sub_Entities_Content": "Persons:[]", "ModifiedDate": datetime(2024, 5, 1, 9, 0),
}
JD_ROW = {
    "Employee_ID": 101, "JD_ID": 1001, "Job_Description": "x" * 60, "Assigned_Date": date(2024, 1, 15),
    "Is_Current": True, "End_Date": None, "LastModifiedDate": datetime(2024, 2, 1, 8, 0),
}
SF_ROW = {
    "L_RO_Form_Metric_ID": 74, "RO_Form_ID": 15, "Employee_ID": 1012, "Name": "N", "From": date(2024, 11, 1),
    "To": date(2024, 11, 30), "Section_ID": 1, "Section": "S", "Metric_ID": 1, "Metric_Title": "T",
    "Instructions": None, "Metric_Type": "R", "Possible_Values": "A,B", "Value": "A",
    "LastModifiedDate": datetime(2024, 12, 1, 0, 0),
}

BULK = {
    "employee": ("_process_employee_report_batches_bulk", EMP_ROW, "LastModifiedDate"),
    "vision": ("_process_vision_data_batches_bulk", VISION_ROW, "ModifiedDate"),
    "job_description": ("_process_job_description_batches_bulk", JD_ROW, "LastModifiedDate"),
    "supervisor": ("_process_supervisor_feedback_batches_bulk", SF_ROW, "LastModifiedDate"),
}


class RecordingRowProcessor:
    def __init__(self, fail_on_call=None):
        self.frames = []
        self.fail_on_call = fail_on_call

    def process_dataframe(self, df, start_row_number=1, pre_cleaned=True):
        self.frames.append({"start_row_number": start_row_number, "pre_cleaned": pre_cleaned,
                            "frame": df_snapshot(df)})
        if self.fail_on_call == len(self.frames):
            raise RuntimeError("processor exploded")
        return max(len(df) - 1, 0), len(df)


def _ts_attrs(svc):
    return {k: tag(v) for k, v in sorted(vars(svc).items()) if k.startswith("_max_modified_date")}


@pytest.mark.parametrize("kind", sorted(BULK))
def test_bulk_batch_processing(kind, snapshot):
    method, row, ts_col = BULK[kind]
    later = dict(row, **{ts_col: datetime(2025, 1, 1, 0, 0)})
    sparse = {k: (None if k not in ("Employee_ID", ts_col) else v) for k, v in row.items()}
    sparse[ts_col] = None
    batches = [
        [row, later],
        [],
        [sparse, dict(row, Employee_ID=Decimal("102"))],
        ["not-a-dict", row],
        ["only-bad"],
        [dict(row, Employee_ID=None)],
    ]
    svc = _service()
    handler = ImportErrorHandler()
    rp = RecordingRowProcessor(fail_on_call=4)
    result = outcome(lambda: getattr(svc, method)(iter(batches), "sync-1", rp, handler, ts_col))
    snapshot(f"sync_bulk_batches__{kind}", {
        "result": result, "frames": rp.frames, "errors": handler_errors(handler), "max_modified": _ts_attrs(svc)})


def test_bulk_batch_no_timestamps_and_abort(snapshot):
    svc = _service()
    rp = RecordingRowProcessor()
    no_ts = outcome(lambda: svc._process_employee_report_batches_bulk(
        [[dict(EMP_ROW, LastModifiedDate=None)]], "s", rp, ImportErrorHandler(), "LastModifiedDate"))
    out = {"no_timestamps": {"result": no_ts, "max_modified": _ts_attrs(svc)}}

    class ErroringProcessor:
        def __init__(self, handler):
            self.handler = handler

        def process_dataframe(self, df, start_row_number=1, pre_cleaned=True):
            for i in range(len(df)):
                if i % 5 == 0:
                    self.handler.add_validation_error(start_row_number + i, "bad")
            return len(df), len(df)

    for n_rows, label in [(199, "below_minimum_rows"), (250, "above_minimum_rows")]:
        svc = _service(threshold=10.0)
        handler = ImportErrorHandler()
        batches = [[dict(VISION_ROW) for _ in range(n_rows)]]
        res = outcome(lambda: svc._process_vision_data_batches_bulk(
            batches, "s", ErroringProcessor(handler), handler, "ModifiedDate"))
        out[label] = {"result": res, "error_count": handler.get_error_count(), "max_modified": _ts_attrs(svc)}
    snapshot("sync_bulk_no_ts_and_abort", out)


def test_create_sync_service(monkeypatch, snapshot):
    for key in ["SQLSERVER_HOST", "SQLSERVER_PORT", "SQLSERVER_DRIVER", "SQLSERVER_ALLOWED_TABLES",
                "SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS", "SQLSERVER_MAX_BATCH_SIZE", "SYNC_ERROR_THRESHOLD_PERCENT"]:
        monkeypatch.delenv(key, raising=False)
    fake_pyodbc = MagicMock(name="pyodbc")
    fake_pyodbc.Error = real_pyodbc.Error
    fake_pyodbc.drivers.return_value = ["ODBC Driver 17 for SQL Server"]
    monkeypatch.setattr(connector_module, "pyodbc", fake_pyodbc)
    fake_db = MagicMock(name="database")
    monkeypatch.setattr(sync_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(sync_module, "SyncTracker", lambda db: ("tracker", db is fake_db))

    def build(**kw):
        svc = create_sync_service(**kw)
        return {"threshold": svc.error_threshold_percent, "tracker": list(svc.sync_tracker),
                "db_is_fake": svc.db_instance is fake_db, "driver": svc.sqlserver_connector.driver,
                "tables": sorted(svc.sqlserver_connector.get_allowed_tables())}

    out = {"defaults": outcome(build), "explicit": outcome(lambda: build(error_threshold_percent=2.5)),
           "explicit_zero": outcome(lambda: build(error_threshold_percent=0))}
    for value in ["25", "abc", ""]:
        monkeypatch.setenv("SYNC_ERROR_THRESHOLD_PERCENT", value)
        out[f"env={value!r}"] = outcome(build)
    monkeypatch.delenv("SYNC_ERROR_THRESHOLD_PERCENT")
    monkeypatch.setenv("SQLSERVER_ALLOWED_TABLES", "dbo.Reports,VisionX")
    out["env_tables"] = outcome(build)
    assert not fake_pyodbc.connect.called
    snapshot("sync_create_service", out)
