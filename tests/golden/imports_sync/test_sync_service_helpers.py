"""Characterization of the DB-free parts of app/services/sync_service.py.

The SQL Server connector, the PostgreSQL database and the row processor are all
mocks; SyncService is built with __new__ so get_database() is never called.
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pyodbc as real_pyodbc
import pytest

from app.integrations.sqlserver import connector as connector_module
from app.services import sync_service as sync_module
from app.services.csv.error_handler import ImportErrorHandler
from app.services.sync_service import SyncService, create_sync_service
from tests.golden.imports_sync.helpers import df_snapshot, handler_errors, outcome


def _service(tables=None, ts_columns=None, threshold=10.0):
    svc = SyncService.__new__(SyncService)
    svc.sqlserver_connector = MagicMock(name="connector")
    svc.sqlserver_connector.get_allowed_tables.return_value = tables
    svc.sqlserver_connector.get_allowed_timestamp_columns.return_value = ts_columns
    svc.error_threshold_percent = threshold
    return svc


SPECS = {
    "employee_reports": sync_module._EMPLOYEE_REPORTS,
    "vision_data": sync_module._VISION_DATA,
    "job_descriptions": sync_module._JOB_DESCRIPTIONS,
    "supervisor_feedback": sync_module._SUPERVISOR_FEEDBACK,
}

# Lists (not sets) so that the error message's table order is deterministic.
TABLE_LISTS = {
    "defaults": ["EmployeeJobDescriptions", "EmployeeReports", "SupervisorFeedback", "VisionEmployeeData"],
    # Names the old substring search could confuse: each sync still gets its configured table
    "decoys_alongside_defaults": ["JobReports", "SupervisorFeedbackReport", "VisionJobData", "EmployeeReports",
                                  "VisionEmployeeData", "EmployeeJobDescriptions", "SupervisorFeedback"],
    "lowercase": ["employeereports", "visionemployeedata", "employeejobdescriptions", "supervisorfeedback"],
    "partial": ["EmployeeReports", "VisionEmployeeData"],
    "empty": [],
}


def test_source_table(snapshot):
    out = {}
    for name, tables in TABLE_LISTS.items():
        svc = _service(tables=tables)
        out[name] = {label: outcome(lambda spec=spec: svc._source_table(spec)) for label, spec in SPECS.items()}
    snapshot("sync_source_table", out)


def test_source_table_follows_settings(monkeypatch):
    monkeypatch.setattr(sync_module.settings, "SQLSERVER_TABLE_JOB_DESCRIPTIONS", "JD_Table")
    svc = _service(tables={"JD_Table", "EmployeeJobDescriptions"})
    assert svc._source_table(sync_module._JOB_DESCRIPTIONS) == "JD_Table"


def test_default_allowed_tables_are_the_source_tables():
    assert connector_module.SQLServerConnector.DEFAULT_ALLOWED_TABLES == {
        "EmployeeReports", "VisionEmployeeData", "EmployeeJobDescriptions", "SupervisorFeedback"}


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
    "employee": (sync_module._EMPLOYEE_REPORTS.transformer, EMP_ROW, "LastModifiedDate"),
    "vision": (sync_module._VISION_DATA.transformer, VISION_ROW, "ModifiedDate"),
    "job_description": (sync_module._JOB_DESCRIPTIONS.transformer, JD_ROW, "LastModifiedDate"),
    "supervisor": (sync_module._SUPERVISOR_FEEDBACK.transformer, SF_ROW, "LastModifiedDate"),
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


@pytest.mark.parametrize("kind", sorted(BULK))
def test_bulk_batch_processing(kind, snapshot):
    transformer, row, ts_col = BULK[kind]
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
    result = outcome(lambda: svc._process_batches(iter(batches), transformer, rp, handler, ts_col))
    snapshot(f"sync_bulk_batches__{kind}", {
        "result": result, "frames": rp.frames, "errors": handler_errors(handler)})


def test_bulk_batch_no_timestamps_and_abort(snapshot):
    svc = _service()
    rp = RecordingRowProcessor()
    no_ts = outcome(lambda: svc._process_batches(
        [[dict(EMP_ROW, LastModifiedDate=None)]], sync_module._EMPLOYEE_REPORTS.transformer, rp,
        ImportErrorHandler(), "LastModifiedDate"))
    out = {"no_timestamps": {"result": no_ts}}

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
        res = outcome(lambda: svc._process_batches(
            batches, sync_module._VISION_DATA.transformer, ErroringProcessor(handler), handler, "ModifiedDate"))
        out[label] = {"result": res, "error_count": handler.get_error_count()}
    snapshot("sync_bulk_no_ts_and_abort", out)


class OutcomeProcessor:
    """Saves each frame, except that it records the given error for rows whose Employee_ID is listed."""

    def __init__(self, handler, failures):
        self.handler = handler
        self.failures = failures  # Employee_ID -> "validation" | "database" | "silent"

    def process_dataframe(self, df, start_row_number=1, pre_cleaned=True):
        saved = 0
        for offset, (_, row) in enumerate(df.iterrows()):
            kind = self.failures.get(row["Employee_ID"])
            if kind == "validation":
                self.handler.add_validation_error(start_row_number + offset, "bad value")
            elif kind == "database":
                self.handler.add_database_error(start_row_number + offset, "write failed")
            elif kind is None:
                saved += 1
        return saved, len(df)


def _vision_row(employee_id, day):
    return dict(VISION_ROW, Employee_ID=employee_id, ModifiedDate=datetime(2025, 1, day, 12, 0))


@pytest.mark.parametrize("failures, expected", [
    # Every row saved: just past the newest row
    ({}, datetime(2025, 1, 4, 12, 0, 0, 1000)),
    # Invalid data does not hold the sync back: correcting it at the source gives it a newer timestamp
    ({2: "validation"}, datetime(2025, 1, 4, 12, 0, 0, 1000)),
    # A failed write in the second batch: start again from that batch's oldest row
    ({3: "database"}, datetime(2025, 1, 3, 12, 0)),
    # Rows the processor neither saved nor reported count as unsaved too
    ({4: "silent"}, datetime(2025, 1, 3, 12, 0)),
    # Unsaved rows in both batches: the oldest of them
    ({1: "database", 4: "database"}, datetime(2025, 1, 1, 12, 0)),
])
def test_next_sync_from(failures, expected):
    svc = _service(threshold=100.0)
    handler = ImportErrorHandler()
    batches = [[_vision_row(1, 1), _vision_row(2, 2)], [_vision_row(4, 4), _vision_row(3, 3)]]
    _, total, next_sync_from = svc._process_batches(
        batches, sync_module._VISION_DATA.transformer, OutcomeProcessor(handler, failures), handler, "ModifiedDate")
    assert total == 4
    assert next_sync_from == expected


def test_row_numbers_follow_source_order():
    svc = _service(threshold=100.0)
    handler = ImportErrorHandler()
    rp = RecordingRowProcessor()
    # The second row of the first batch fails to transform; the rows after it keep their own numbers
    batches = [[EMP_ROW, "not-a-dict", EMP_ROW], ["not-a-dict", EMP_ROW]]
    svc._process_batches(batches, sync_module._EMPLOYEE_REPORTS.transformer, rp, handler, "LastModifiedDate")
    assert [e.row_number for e in handler.errors] == [2, 4]
    assert [f["start_row_number"] for f in rp.frames] == [1, 5]


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
