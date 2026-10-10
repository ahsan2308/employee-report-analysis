"""Characterization of the SQL Server -> PostgreSQL sync pipeline.

Celery sync tasks (run in-process via ``.apply``) -> SyncService -> transformers
-> RowProcessor / CSV processors. The SQL Server connector is a fake serving
fixed rows; Postgres, the processors and the sync tracker are real.
Outcome = task return value, SyncHistory rows, data tables and external calls.
"""
from datetime import date, datetime

import pytest

from app.models.sync_models import SyncHistory, SyncStatus, SyncType
from app.tasks.sync_tasks import (
    full_sync_task,
    incremental_sync_task,
    sync_employee_reports_task,
    sync_vision_data_task,
)
from tests.integration.pipelines.fakes import FakeSQLServerConnector
from tests.integration.pipelines.seed import (
    _plain,
    dump_data_tables,
    dump_sync_history,
    seed_import_employees,
)
from tests.support.scrub import scrub

SCHEMAS = {
    "EmployeeReports": {"Employee_ID": "int", "Name": "nvarchar", "Designation": "nvarchar", "BPS": "nvarchar",
                        "Office_Hierarchy": "nvarchar", "From": "date", "To": "date", "Draft": "nvarchar",
                        "Tasks_Completed": "nvarchar", "Impact": "nvarchar", "Challenges": "nvarchar",
                        "Support_Required": "nvarchar", "Tasks_Planned": "nvarchar", "Confidence_Level": "nvarchar",
                        "NTR": "nvarchar", "LastModifiedDate": "datetime"},
    "VisionEmployeeData": {"Employee_ID": "int", "From_Date": "date", "To_Date": "date", "Main_Entity": "nvarchar",
                           "Sub_Entities": "nvarchar", "Sub_Entities_Content": "nvarchar", "ModifiedDate": "datetime"},
    "EmployeeJobDescriptions": {"Employee_ID": "int", "JD_ID": "int", "Job_Description": "nvarchar",
                                "Assigned_Date": "date", "Is_Current": "bit", "End_Date": "date",
                                "LastModifiedDate": "datetime"},
    "SupervisorFeedback": {"L_RO_Form_Metric_ID": "int", "RO_Form_ID": "int", "Employee_ID": "int",
                           "Name": "nvarchar", "Designation": "nvarchar", "BPS": "nvarchar",
                           "Office_Hierarchy": "nvarchar", "Executive_Office": "nvarchar", "From": "date",
                           "To": "date", "Section_ID": "int", "Section": "nvarchar", "Metric_ID": "int",
                           "Metric_Title": "nvarchar", "Instructions": "nvarchar", "Metric_Type": "char",
                           "Possible_Values": "nvarchar", "Value": "nvarchar", "LastModifiedDate": "datetime"},
}


def report_row(emp, name, frm, to, tasks, modified, **extra):
    row = {"Employee_ID": emp, "Name": name, "Designation": "Analyst", "BPS": "BS-17",
           "Office_Hierarchy": "Technical>Tech-I", "From": frm, "To": to, "Draft": None, "Tasks_Completed": tasks,
           "Impact": "Backlog reduced", "Challenges": "Late inputs", "Support_Required": "None",
           "Tasks_Planned": "Monthly digest", "Confidence_Level": "4 - Confident", "NTR": None,
           "LastModifiedDate": modified}
    row.update(extra)
    return row


def vision_row(emp, frm, to, entity, subs, content, modified):
    return {"Employee_ID": emp, "From_Date": frm, "To_Date": to, "Main_Entity": entity, "Sub_Entities": subs,
            "Sub_Entities_Content": content, "ModifiedDate": modified}


def jd_row(emp, jd, text, assigned, current, end, modified):
    return {"Employee_ID": emp, "JD_ID": jd, "Job_Description": text, "Assigned_Date": assigned,
            "Is_Current": current, "End_Date": end, "LastModifiedDate": modified}


def sf_row(lid, form, emp, metric, title, mtype, value, modified):
    return {"L_RO_Form_Metric_ID": lid, "RO_Form_ID": form, "Employee_ID": emp, "Name": "Sana Malik",
            "Designation": "Analyst", "BPS": "BS-17", "Office_Hierarchy": "Technical", "Executive_Office": "HQ",
            "From": date(2025, 1, 1), "To": date(2025, 3, 31), "Section_ID": 1, "Section": "Performance",
            "Metric_ID": metric, "Metric_Title": title, "Instructions": f"Rate {title}", "Metric_Type": mtype,
            "Possible_Values": "Poor,Fair,Good,Excellent" if mtype == "R" else None, "Value": value,
            "LastModifiedDate": modified}


JD_TEXT = "Analyst: leads backlog reduction, audits archives and drafts monthly performance summaries."


def source_rows():
    return {
        "EmployeeReports": [
            report_row(201, "Sana Malik", date(2025, 3, 1), date(2025, 3, 7), "Closed twelve case files.",
                       datetime(2025, 3, 8, 10, 0, 0)),
            report_row(202, "Omar Farooq", date(2025, 3, 1), date(2025, 3, 7), "Visited two districts.",
                       datetime(2025, 3, 8, 11, 30, 0, 250000)),
            report_row(203, "Hina Raza", date(2025, 3, 1), date(2025, 3, 7), None, datetime(2025, 3, 8, 9, 0),
                       NTR="On leave"),
            report_row(204, "Bad Bps", date(2025, 3, 1), date(2025, 3, 7), "x", datetime(2025, 3, 8, 9, 30),
                       BPS="Grade-7"),
        ],
        "VisionEmployeeData": [
            vision_row(201, date(2025, 3, 1), date(2025, 3, 7), "Persons", "Persons:3, Pictures:1",
                       'Persons:[{"name": "Person A"}], Pictures:[]', datetime(2025, 3, 8, 12, 0)),
            vision_row(202, date(2025, 3, 1), date(2025, 3, 7), "Tasks", "Tasks:2", 'Tasks:[{"title": "T1"}]',
                       datetime(2025, 3, 8, 12, 5)),
            vision_row(999, date(2025, 3, 1), date(2025, 3, 7), "Tasks", "Tasks:2", "Tasks:[]",
                       datetime(2025, 3, 8, 12, 6)),
        ],
        "EmployeeJobDescriptions": [
            jd_row(201, 1001, JD_TEXT, date(2025, 1, 15), True, None, datetime(2025, 1, 16, 8, 0)),
            jd_row(202, 1002, JD_TEXT.replace("Analyst", "Officer"), date(2024, 6, 1), False, date(2025, 2, 28),
                   datetime(2025, 3, 1, 8, 0)),
        ],
        "SupervisorFeedback": [
            sf_row(74, 15, 201, 1, "Quality", "R", "Good", datetime(2025, 4, 2, 9, 0)),
            sf_row(75, 15, 201, 2, "Timeliness", "R", "Excellent", datetime(2025, 4, 2, 9, 0)),
            sf_row(76, 15, 201, 3, "Comments", "T", "Steady performer", datetime(2025, 4, 2, 9, 1)),
        ],
    }


@pytest.fixture
def source(ext):
    ext.sqlserver = FakeSQLServerConnector(ext.recorder, SCHEMAS, source_rows())
    return ext.sqlserver


def _outcome(result):
    if isinstance(result.result, BaseException):
        return {"state": result.state, "exception": repr(result.result)}
    return {"state": result.state, "return": _plain(result.result)}


def snapshot_world(snapshot, name, db_session, ext, outcomes, full_tables=True):
    tables = dump_data_tables(db_session, ext.vector_store.document_order)
    if not full_tables:
        tables = {k: len(v) for k, v in tables.items()}
    snapshot(name, scrub({
        "outcomes": outcomes,
        "sync_history": dump_sync_history(db_session),
        "tables": tables,
        "external_calls": ext.calls,
    }))


# --------------------------------------------------------------------------- full / incremental

def test_full_sync(db_session, ext, source, snapshot):
    outcomes = [_outcome(full_sync_task.apply(task_id="celery-full"))]
    snapshot_world(snapshot, "sync__full", db_session, ext, outcomes)


def test_incremental_after_full_picks_up_changes(db_session, ext, source, snapshot):
    outcomes = [_outcome(full_sync_task.apply(task_id="celery-full"))]
    # New and modified source rows after the first sync.
    source.rows["EmployeeReports"].append(report_row(201, "Sana Malik", date(2025, 3, 8), date(2025, 3, 14),
                                                     "Second week.", datetime(2025, 3, 15, 10, 0)))
    source.rows["EmployeeReports"][0] = report_row(201, "Sana Malik", date(2025, 3, 1), date(2025, 3, 7),
                                                   "Closed twelve case files (edited).", datetime(2025, 3, 16, 8, 0))
    # Exactly at the stored cutoff (max + 1ms): get_records_since uses >=, so this row is included.
    source.rows["VisionEmployeeData"].append(vision_row(201, date(2025, 3, 8), date(2025, 3, 14), "Persons",
                                                        "Persons:1", "", datetime(2025, 3, 8, 12, 6, 0, 1000)))
    outcomes.append(_outcome(incremental_sync_task.apply(task_id="celery-incremental")))
    snapshot_world(snapshot, "sync__incremental_after_full", db_session, ext, outcomes)


def test_incremental_without_history_runs_full(db_session, ext, source, snapshot):
    outcomes = [_outcome(incremental_sync_task.apply(task_id="celery-incremental"))]
    snapshot_world(snapshot, "sync__incremental_first_run", db_session, ext, outcomes)


# --------------------------------------------------------------------------- single-type tasks

def test_employee_reports_task_with_api_created_sync_id(db_session, ext, source, snapshot):
    job = SyncHistory(sync_type=SyncType.EMPLOYEE_REPORTS.value, status=SyncStatus.PENDING.value,
                      sync_options={"is_full_sync": True, "triggered_by": "api"})
    db_session.add(job)
    db_session.commit()
    outcomes = [_outcome(sync_employee_reports_task.apply(kwargs={"is_full_sync": True, "sync_id": str(job.sync_id)},
                                                          task_id="celery-er"))]
    snapshot_world(snapshot, "sync__employee_reports_existing_sync_id", db_session, ext, outcomes)


def test_employee_reports_task_unknown_sync_id(db_session, ext, source, snapshot):
    outcomes = [_outcome(sync_employee_reports_task.apply(
        kwargs={"is_full_sync": True, "sync_id": "00000000-0000-4000-8000-00000000dead"}, task_id="celery-er"))]
    snapshot_world(snapshot, "sync__employee_reports_unknown_sync_id", db_session, ext, outcomes)


def test_vision_task_partial_and_all_failed(db_session, ext, source, snapshot):
    seed_import_employees(db_session)
    outcomes = [_outcome(sync_vision_data_task.apply(kwargs={"is_full_sync": True}, task_id="celery-v1"))]
    source.rows["VisionEmployeeData"] = [
        vision_row(999, date(2025, 3, 8), date(2025, 3, 14), "Tasks", "Tasks:1", "Tasks:[]", datetime(2025, 3, 20)),
    ]
    outcomes.append(_outcome(sync_vision_data_task.apply(kwargs={"is_full_sync": True}, task_id="celery-v2")))
    snapshot_world(snapshot, "sync__vision_partial_then_failed", db_session, ext, outcomes)


# --------------------------------------------------------------------------- failure modes

def test_error_threshold_aborts_sync(db_session, ext, source, snapshot, monkeypatch):
    monkeypatch.setenv("SYNC_ERROR_THRESHOLD_PERCENT", "5")
    seed_import_employees(db_session)
    rows = [vision_row(201, date(2025, 3, 1), date(2025, 3, 7), f"Entity {i:03d}", "Persons:1", "Persons:[]",
                       datetime(2025, 3, 8, 12, 0, i % 60)) for i in range(190)]
    rows += [vision_row(999, date(2025, 3, 1), date(2025, 3, 7), f"Ghost {i:02d}", "Persons:1", "Persons:[]",
                        datetime(2025, 3, 9, 12, 0, i)) for i in range(20)]
    source.rows["VisionEmployeeData"] = rows
    source.fetch_batch_size = 105  # two batches: the abort check runs after each one
    outcomes = [_outcome(sync_vision_data_task.apply(kwargs={"is_full_sync": True}, task_id="celery-threshold"))]
    snapshot_world(snapshot, "sync__error_threshold_abort", db_session, ext, outcomes, full_tables=False)


def test_connector_failures_inside_full_sync(db_session, ext, source, snapshot):
    """Fetch fails for employee reports and the schema lookup fails for JDs; the other types still sync."""
    source.fail_tables = {"EmployeeReports": "fetch", "EmployeeJobDescriptions": "schema"}
    seed_import_employees(db_session)
    outcomes = [_outcome(full_sync_task.apply(task_id="celery-full"))]
    snapshot_world(snapshot, "sync__connector_failures", db_session, ext, outcomes)
