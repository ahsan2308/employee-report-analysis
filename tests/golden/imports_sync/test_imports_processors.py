"""Characterization of CSV-type detection (ProcessorFactory) and the processors'
DB-free behaviour (validation, row -> insert-dict transformation, grouping).

The SQLAlchemy session is a MagicMock(spec=Session); PostgreSQL ``insert`` is
replaced by a recorder so the dictionaries handed to ``.values()`` are visible.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy.orm import Session

import sqlalchemy.dialects.postgresql as pg_dialect
from app.services.csv.csv_reader import PandasCSVReader
from app.services.csv.error_handler import ImportErrorHandler
from app.services.csv.processors import employee_report_processor as erp_module
from app.services.csv.processors.employee_report_processor import EmployeeReportProcessor
from app.services.csv.processors.job_description_processor import JobDescriptionProcessor
from app.services.csv.processors.processor_factory import ProcessorFactory
from app.services.csv.processors.supervisor_feedback_processor import SupervisorFeedbackProcessor
from app.services.csv.processors.vision_data_processor import VisionDataProcessor
from app.services.csv.row_processor import RowProcessor
from tests.golden.imports_sync.helpers import DATA_DIR, df_snapshot, handler_errors, outcome, tag
from tests.support.scrub import scrub

PROCESSORS = [EmployeeReportProcessor, VisionDataProcessor, JobDescriptionProcessor, SupervisorFeedbackProcessor]

EMP_FULL = EmployeeReportProcessor.REQUIRED_HEADERS + EmployeeReportProcessor.OPTIONAL_HEADERS
VISION = VisionDataProcessor.REQUIRED_HEADERS
JD_FULL = ["Employee_ID", "JD_ID", "Job_Description", "Assigned_Date", "Is_Current", "End_Date"]
SF = SupervisorFeedbackProcessor.REQUIRED_HEADERS

HEADER_SETS = {
    "employee_full": EMP_FULL,
    "employee_essential_only": ["Name", "Designation", "From", "To", "Tasks_Completed"],
    "employee_missing_tasks": ["Name", "Designation", "From", "To"],
    "employee_lowercase": [h.lower() for h in EMP_FULL],
    "employee_padded": [f" {h} " for h in EMP_FULL],
    "vision": VISION,
    "vision_lowercase": [h.lower() for h in VISION],
    "vision_plus_extra": VISION + ["ModifiedDate"],
    "job_description_full": JD_FULL,
    "job_description_required_headers_only": JobDescriptionProcessor.REQUIRED_HEADERS,
    "supervisor": SF,
    "supervisor_lowercase": [h.lower() for h in SF],
    "supervisor_uppercase": [h.upper() for h in SF],
    "supervisor_with_optional": SF + ["Designation", "BPS", "Office_Hierarchy", "Executive_Office"],
    "supervisor_plus_tasks_and_designation": SF + ["Designation", "Tasks_Completed"],
    "vision_plus_job_description": VISION + JD_FULL,
    "job_description_plus_supervisor": JD_FULL + SF,
    "everything": EMP_FULL + VISION + JD_FULL + SF,
    "unknown": ["emp_id", "full_name", "period"],
    "empty": [],
}


def _factory(headers, processor_type=None):
    def run():
        proc, csv_type = ProcessorFactory.get_processor(
            headers, MagicMock(spec=Session), ImportErrorHandler(), processor_type=processor_type)
        return {"processor": type(proc).__name__, "csv_type": csv_type}
    return outcome(run)


def test_factory_detection_matrix(snapshot):
    out = {}
    for name, headers in HEADER_SETS.items():
        out[name] = {
            "factory": _factory(headers),
            "can_process": {p.__name__: p.can_process(headers) for p in PROCESSORS},
        }
    snapshot("factory_detection_matrix", out)


def test_factory_explicit_type_and_mapping(snapshot):
    out = {
        "explicit_matching": _factory(SF, "SupervisorFeedbackProcessor"),
        "explicit_with_wrong_headers_raises": _factory(["anything"], "VisionDataProcessor"),
        "explicit_csv_type_value": _factory(VISION, "vision_data"),
        "explicit_csv_type_value_wrong_headers": _factory(SF, "vision_data"),
        "explicit_unknown_falls_back": _factory(VISION, "NoSuchProcessor"),
        "explicit_unknown_unmatched_headers": _factory(["x"], "NoSuchProcessor"),
        "explicit_wrong_case": _factory(VISION, "visiondataprocessor"),
        "explicit_empty_string": _factory(VISION, ""),
        "csv_type_mapping": {n: ProcessorFactory._get_csv_type_for_processor(n) for n in
                             [p.__name__ for p in PROCESSORS] + ["RowProcessor", ""]},
        "registry_order": [p.__name__ for p in ProcessorFactory._processors],
        "required_headers": {p.__name__: p(MagicMock(spec=Session), ImportErrorHandler()).get_required_headers()
                             for p in PROCESSORS},
        "initial_metrics": {p.__name__: p(MagicMock(spec=Session), ImportErrorHandler()).get_metrics()
                            for p in PROCESSORS},
    }
    snapshot("factory_explicit_and_mapping", out)


def test_factory_register_processor(monkeypatch, snapshot):
    monkeypatch.setattr(ProcessorFactory, "_processors", list(ProcessorFactory._processors))

    class CustomProcessor(VisionDataProcessor):
        @classmethod
        def can_process(cls, headers):
            return "custom" in headers

    ProcessorFactory.register_processor(CustomProcessor)
    ProcessorFactory.register_processor(CustomProcessor)  # second call is a no-op
    out = {
        "registry_order": [p.__name__ for p in ProcessorFactory._processors],
        "detect_custom": _factory(["custom"]),
        "detect_vision_still_first": _factory(VISION + ["custom"]),
    }
    snapshot("factory_register_processor", out)


# ---------------------------------------------------------------------------
# Processing with a mocked session
# ---------------------------------------------------------------------------
class InsertRecorder:
    """Stands in for sqlalchemy.dialects.postgresql.insert."""

    def __init__(self):
        self.calls = []

    def __call__(self, table):
        recorder = self

        stmt = MagicMock()

        def values(data):
            recorder.calls.append({"table": table.name, "values": tag(data)})
            return stmt

        stmt.values.side_effect = values
        return stmt


@pytest.fixture
def pg_insert(monkeypatch):
    recorder = InsertRecorder()
    monkeypatch.setattr(pg_dialect, "insert", recorder)
    return recorder


@pytest.fixture
def vector_store(monkeypatch):
    calls = []
    # Like the real function, report success (it returns False when the store rejects the reports)
    monkeypatch.setattr(erp_module, "add_report_to_vector_store", lambda **kw: calls.append(tag(kw)) or True)
    return calls


def _db(existing_employee_ids=(101, 102, 103, 104, 105, 201, 202, 203, 204, 1012, 301)):
    db = MagicMock(spec=Session)
    db.query.return_value.all.return_value = [(i,) for i in existing_employee_ids]
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _added_objects(db):
    out = []
    for call in db.add.call_args_list:
        obj = call.args[0]
        cols = {c.key: getattr(obj, c.key, None) for c in obj.__table__.columns}
        out.append({"type": type(obj).__name__, "columns": tag({k: v for k, v in cols.items() if v is not None})})
    return out


def _read_df(name, **kw):
    return next(PandasCSVReader(**kw).read_dataframes(file_path=str(DATA_DIR / name)))


FILE_PROCESSOR = {
    "employee_reports_bom.csv": EmployeeReportProcessor,
    "employee_reports_semicolon.csv": EmployeeReportProcessor,
    "employee_reports_cp1252.csv": EmployeeReportProcessor,
    "vision_data.tsv": VisionDataProcessor,
    "job_descriptions_pipe.txt": JobDescriptionProcessor,
    "messy_headers.csv": EmployeeReportProcessor,
}


@pytest.mark.parametrize("name", sorted(FILE_PROCESSOR))
def test_processor_process_dataframe_from_file(name, pg_insert, vector_store, snapshot):
    df = _read_df(name)
    handler = ImportErrorHandler()
    db = _db()
    proc = FILE_PROCESSOR[name](db, handler)
    result = outcome(lambda: proc.process_dataframe(df, start_row_number=2, pre_cleaned=True))
    snapshot(f"processor_dataframe__{name}", {
        "result": result,
        "errors": handler_errors(handler),
        "pg_insert_values": pg_insert.calls,
        "db_added": _added_objects(db),
        "vector_store_calls": vector_store,
        "metrics": proc.get_metrics(),
        "commits": db.commit.call_count,
        "rollbacks": db.rollback.call_count,
    })


def test_supervisor_process_dataframe_from_file(monkeypatch, snapshot):
    df = _read_df("supervisor_feedback.csv")
    handler = ImportErrorHandler()
    proc = SupervisorFeedbackProcessor(_db(existing_employee_ids=(1012,)), handler)
    captured = []
    monkeypatch.setattr(proc, "_bulk_process_supervisor_feedback", lambda forms: captured.append(tag(forms)) or True)
    result = outcome(lambda: proc.process_dataframe(df, start_row_number=2))
    snapshot("processor_dataframe__supervisor_feedback.csv", {
        "result": result, "errors": handler_errors(handler), "forms_by_id": captured, "metrics": proc.get_metrics()})


def _rows_df(rows, index=None):
    return pd.DataFrame(rows, index=index)


EMP_ROW = {
    "Employee_ID": "101", "Name": "Ayesha Khan", "Designation": "Deputy Director", "BPS": "BS-18",
    "Office_Hierarchy": "Technical>SOC", "From": "2024-03-01", "To": "2024-03-31", "Draft": None,
    "Tasks_Completed": "Reviewed cases", "Impact": None, "Challenges": None, "Support_Required": None,
    "Tasks_Planned": None, "Confidence_Level": "4", "NTR": None,
}


def test_employee_processor_edge_cases(pg_insert, vector_store, snapshot):
    out = {}
    # Duplicate (Employee_ID, To) rows: last one kept; NTR rows produce no report; index offset row numbers
    rows = [
        dict(EMP_ROW, Tasks_Completed="first version"),
        dict(EMP_ROW, Tasks_Completed="second version"),
        dict(EMP_ROW, Employee_ID="102", NTR="On leave", Tasks_Completed=None),
        dict(EMP_ROW, Employee_ID=None, Name="No Id Person"),
        dict(EMP_ROW, Employee_ID="103", BPS=None, Office_Hierarchy=None),
    ]
    for label, index, pre_cleaned in [("default_index", None, True), ("offset_index", [10, 11, 12, 13, 14], True),
                                      ("nan_values_not_precleaned", None, False)]:
        frame_rows = rows
        if label == "nan_values_not_precleaned":
            frame_rows = [dict(r, Impact=float("nan")) for r in rows]
        handler, db = ImportErrorHandler(), _db()
        pg_insert.calls.clear()
        vector_store.clear()
        proc = EmployeeReportProcessor(db, handler)
        res = outcome(lambda: proc.process_dataframe(_rows_df(frame_rows, index), start_row_number=1,
                                                     pre_cleaned=pre_cleaned))
        out[label] = {"result": res, "errors": handler_errors(handler), "pg_insert_values": list(pg_insert.calls),
                      "db_added": _added_objects(db), "metrics": proc.get_metrics()}

    # A TypeError from the model escapes process_dataframe (only ValidationError is caught)
    handler, db = ImportErrorHandler(), _db()
    proc = EmployeeReportProcessor(db, handler)
    out["type_error_escapes"] = outcome(lambda: proc.process_dataframe(
        _rows_df([dict(EMP_ROW, From="2024/01/01")]), start_row_number=1))
    out["empty_frame"] = outcome(lambda: proc.process_dataframe(pd.DataFrame(), 1))
    snapshot("processor_employee_edge_cases", out)


def test_employee_process_row(pg_insert, vector_store, snapshot):
    out = {}
    cases = {
        "create_new_employee_and_report": (dict(EMP_ROW), None),
        "update_existing_employee": (dict(EMP_ROW), "existing"),
        "ntr_row_no_report": (dict(EMP_ROW, NTR="Training", Tasks_Completed=None), None),
        "missing_employee_id": (dict(EMP_ROW, Employee_ID=None), None),
        "validation_error": (dict(EMP_ROW, Name="<bad>", BPS="X"), None),
        "type_error_dates": (dict(EMP_ROW, From="2024/01/01"), None),
        "unbound_local_dates": (dict(EMP_ROW, From="March 2024"), None),
        "bps_none_in_position": (dict(EMP_ROW, BPS=None), None),
    }
    for name, (row, mode) in cases.items():
        handler, db = ImportErrorHandler(), _db()
        vector_store.clear()
        if mode == "existing":
            existing = SimpleNamespace(position="old", wing="old", report_id=77, report_text="old")
            db.query.return_value.filter.return_value.first.return_value = existing
        proc = EmployeeReportProcessor(db, handler)
        res = outcome(lambda: proc.process_row(row, 5))
        entry = {"result": res, "errors": handler_errors(handler), "db_added": _added_objects(db),
                 "vector_store_calls": list(vector_store), "metrics": proc.get_metrics(),
                 "commits": db.commit.call_count}
        if mode == "existing":
            entry["existing_after"] = tag(vars(existing))
        out[name] = entry
    snapshot("processor_employee_process_row", out)


def test_vision_and_jd_processor_edge_cases(pg_insert, snapshot):
    out = {}
    vision_rows = [
        {"Employee_ID": "101", "From_Date": "2024-04-01", "To_Date": "2024-04-30", "Main_Entity": "Persons",
         "Sub_Entities": "Persons:1", "Sub_Entities_Content": 'Persons:[{"n": 1}]'},
        {"Employee_ID": "999", "From_Date": "2024-04-01", "To_Date": "2024-04-30", "Main_Entity": "Persons",
         "Sub_Entities": "Persons:1", "Sub_Entities_Content": ""},
    ]
    handler, db = ImportErrorHandler(), _db()
    proc = VisionDataProcessor(db, handler)
    out["vision_unknown_employee"] = {
        "result": outcome(lambda: proc.process_dataframe(_rows_df(vision_rows, [5, 6]), start_row_number=1)),
        "errors": handler_errors(handler), "pg_insert_values": list(pg_insert.calls), "metrics": proc.get_metrics()}

    proc = VisionDataProcessor(MagicMock(spec=Session), ImportErrorHandler())
    out["vision_parse_sub_entities_content"] = {
        "dict_passthrough": tag(proc._parse_sub_entities_content({"A": [1]})),
        "none": tag(proc._parse_sub_entities_content(None)),
        "blank": tag(proc._parse_sub_entities_content("   ")),
        "legacy_string": tag(proc._parse_sub_entities_content('Cases:[{"a": 1}], Bad, Tasks:[{\'b\': 2,}], X:notjson')),
    }

    pg_insert.calls.clear()
    jd_text = "Leads the analysis team, prepares monthly performance summaries and coordinates with wings."
    jd_rows = [
        {"Employee_ID": "101", "JD_ID": "1001", "Job_Description": jd_text, "Assigned_Date": "01/15/2024",
         "Is_Current": "yes", "End_Date": "N/A"},
        {"Employee_ID": "102", "JD_ID": "1002.0", "Job_Description": jd_text, "Assigned_Date": "2023-01-01",
         "Is_Current": "0", "End_Date": "31-12-2023"},
        {"Employee_ID": "555", "JD_ID": "1003", "Job_Description": jd_text, "Assigned_Date": "2023-01-01",
         "Is_Current": "1", "End_Date": None},
    ]
    handler, db = ImportErrorHandler(), _db()
    proc = JobDescriptionProcessor(db, handler)
    out["jd_mixed"] = {
        "result": outcome(lambda: proc.process_dataframe(_rows_df(jd_rows), start_row_number=2)),
        "errors": handler_errors(handler), "pg_insert_values": list(pg_insert.calls), "metrics": proc.get_metrics()}
    snapshot("processor_vision_jd_edge_cases", out)


def test_supervisor_pure_helpers(snapshot):
    proc = SupervisorFeedbackProcessor(MagicMock(spec=Session), ImportErrorHandler())
    grouped = proc._group_rows_by_form([
        (1, {"RO_Form_ID": 15, "Metric_ID": 1}),
        (2, {"RO_Form_ID": 16, "Metric_ID": 1}),
        (3, {"RO_Form_ID": 15, "Metric_ID": 2}),
        (4, {"RO_Form_ID": None, "Metric_ID": 3}),
    ])

    def md(metric_id, mtype, possible, max_value, section_id=1, section="Performance"):
        return SimpleNamespace(metric_id=metric_id, metric_type=mtype, possible_values=possible, max_value=max_value,
                               section_id=section_id, section=section, metric_name=f"Metric {metric_id}")

    def resp(text):
        return SimpleNamespace(text_response=text)

    caches = {
        "mixed": proc._calculate_form_cache(1, [
            (resp("Good"), md(1, "R", "Poor, Fair, Good, Excellent", 4)),
            (resp("Excellent"), md(2, "R", "Poor,Fair,Good,Excellent", 4)),
            (resp("good"), md(3, "R", "Poor, Fair, Good", 3)),  # case mismatch: not rated
            (resp("Fair"), md(4, "R", "Poor, Fair, Good", None)),  # no max_value: skipped
            (resp("Steady"), md(5, "T", None, None, 2, "Comments")),
            (resp("   "), md(6, "T", None, None, 2, "Comments")),
            (resp(None), md(7, "R", "A,B", 2)),
            (resp("B"), md(8, "R", "A,B", 5)),  # max_value larger than options
        ]),
        "empty": proc._calculate_form_cache(2, []),
    }
    snapshot("processor_supervisor_pure_helpers", scrub({"grouped": tag(grouped), "caches": tag(caches)}))


# ---------------------------------------------------------------------------
# RowProcessor (auto-detection + error fan-out)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["employee_reports_bom.csv", "missing_columns.csv", "single_column.csv",
                                  "supervisor_feedback.csv"])
def test_row_processor_on_files(name, pg_insert, vector_store, monkeypatch, snapshot):
    monkeypatch.setattr(SupervisorFeedbackProcessor, "_bulk_process_supervisor_feedback", lambda self, f: True)
    df = _read_df(name)
    handler = ImportErrorHandler()
    rp = RowProcessor(_db(), handler)
    res = outcome(lambda: rp.process_dataframe(df, start_row_number=2))
    snapshot(f"row_processor__{name}", {"result": res, "errors": handler_errors(handler), "csv_type": rp._csv_type,
                                        "metrics": outcome(rp.get_metrics), "frame": df_snapshot(df)})


def test_row_processor_type_error_fanout(snapshot):
    handler = ImportErrorHandler()
    rp = RowProcessor(_db(), handler)
    rows = [dict(EMP_ROW, From="2024/01/01"), dict(EMP_ROW, Employee_ID="102")]
    res = outcome(lambda: rp.process_dataframe(_rows_df(rows, [3, 4]), start_row_number=10))
    rp2 = RowProcessor(_db(), ImportErrorHandler())
    res2 = outcome(lambda: rp2.process_dataframe(_rows_df([dict(EMP_ROW, From="soon")]), start_row_number=1))
    snapshot("row_processor_type_error_fanout", {
        "type_error": {"result": res, "errors": handler_errors(handler), "metrics": outcome(rp.get_metrics)},
        "unbound_local_error": {"result": res2, "errors": handler_errors(rp2.error_handler)},
        "no_input": outcome(lambda: RowProcessor(_db(), ImportErrorHandler())._get_processor()),
    })
