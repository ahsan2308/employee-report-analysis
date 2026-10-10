"""Characterization of the CSV import pipeline end to end.

create_import_job -> Celery task ``csv_import.process`` (run in-process via
``.apply``) -> CSVImportService -> PandasCSVReader -> processor. Outcome = the
task's return value, CSVImportJob / ImportError rows, every affected data table,
and the embedding / vector-store calls (employee reports only).
"""
from pathlib import Path

import pytest

from app.schemas.csv_import_schema import CSVImportOptions
from app.services.csv_import_service import CSVImportService
from app.tasks.import_tasks import process_csv_import
from tests.integration.pipelines.seed import (
    _plain,
    dump_data_tables,
    dump_import_job,
    seed_import_employees,
)
from tests.support.scrub import scrub

DATA = Path(__file__).parent / "data"


def run_import(file_name, options=None, csv_type=None, as_content=False, task_id="celery-import"):
    job = CSVImportService().create_import_job(
        filename=file_name, options=CSVImportOptions(**options) if options else None, csv_type=csv_type)
    kwargs = {"job_id": job.job_id, "csv_type": csv_type, "options": options}
    path = DATA / file_name
    if as_content:
        kwargs.update(file_content=path.read_bytes(), filename=file_name)
    else:
        kwargs.update(file_path=str(path))
    result = process_csv_import.apply(kwargs=kwargs, task_id=task_id)
    if isinstance(result.result, BaseException):
        return {"state": result.state, "exception": repr(result.result)}
    return {"state": result.state, "return": _plain(result.result)}


def snapshot_world(snapshot, name, db_session, ext, outcomes):
    snapshot(name, scrub({
        "outcomes": outcomes,
        "import": dump_import_job(db_session),
        "tables": dump_data_tables(db_session, ext.vector_store.document_order),
        "external_calls": ext.calls,
    }))


# --------------------------------------------------------------------------- employee reports

def test_employee_reports_import(db_session, ext, snapshot):
    outcomes = [run_import("employee_reports.csv")]
    snapshot_world(snapshot, "import__employee_reports", db_session, ext, outcomes)


def test_employee_reports_reimport_upserts(db_session, ext, snapshot):
    outcomes = [run_import("employee_reports.csv", task_id="celery-import-1"),
                run_import("employee_reports.csv", task_id="celery-import-2")]
    snapshot_world(snapshot, "import__employee_reports_reimport", db_session, ext, outcomes)


def test_employee_reports_bad_rows(db_session, ext, snapshot):
    outcomes = [run_import("employee_reports_bad.csv", csv_type="employee_report")]
    snapshot_world(snapshot, "import__employee_reports_bad_rows", db_session, ext, outcomes)


def test_employee_reports_bad_rows_small_chunks(db_session, ext, snapshot):
    """chunk_size=2 -> four DataFrame chunks; shows how row numbers are reported across chunks."""
    outcomes = [run_import("employee_reports_bad.csv", options={"chunk_size": 2})]
    snapshot_world(snapshot, "import__employee_reports_bad_rows_chunk2", db_session, ext, outcomes)


def test_employee_reports_stop_on_error(db_session, ext, snapshot):
    outcomes = [run_import("employee_reports_bad.csv", options={"stop_on_error": True})]
    snapshot_world(snapshot, "import__employee_reports_stop_on_error", db_session, ext, outcomes)


def test_employee_reports_row_by_row_mode(db_session, ext, snapshot):
    options = {"processing_mode": "row_by_row", "auto_mode_selection": False}
    outcomes = [run_import("employee_reports.csv", options=options, as_content=True)]
    snapshot_world(snapshot, "import__employee_reports_row_by_row", db_session, ext, outcomes)


def test_employee_reports_dry_run(db_session, ext, snapshot):
    outcomes = [run_import("employee_reports_bad.csv", options={"dry_run": True})]
    snapshot_world(snapshot, "import__employee_reports_dry_run", db_session, ext, outcomes)


def test_employee_reports_vector_store_failure(db_session, ext, snapshot):
    """Vector upserts fail on every retry: the import still reports success (errors are only logged)."""
    ext.vector_store.batch_failures = 99
    outcomes = [run_import("employee_reports.csv")]
    snapshot_world(snapshot, "import__employee_reports_vector_store_down", db_session, ext, outcomes)


# --------------------------------------------------------------------------- other CSV types

@pytest.mark.parametrize("kind", ["vision_data", "job_descriptions", "supervisor_feedback"])
def test_import_good_bad_and_reimport(kind, db_session, ext, snapshot):
    seed_import_employees(db_session)
    outcomes = [
        run_import(f"{kind}.csv", task_id="celery-import-1"),
        run_import(f"{kind}_bad.csv", task_id="celery-import-2"),
        run_import(f"{kind}.csv", task_id="celery-import-3"),
    ]
    snapshot_world(snapshot, f"import__{kind}", db_session, ext, outcomes)


def test_import_unknown_format(db_session, ext, snapshot):
    """Comma file read with delimiter=";" -> one merged header column that no processor recognises."""
    outcomes = [run_import("employee_reports.csv", options={"delimiter": ";"})]
    snapshot_world(snapshot, "import__unrecognised_headers", db_session, ext, outcomes)
