"""Characterization of the DB-facing parts of CSVImportService and ImportErrorHandler."""
from datetime import date, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.models.import_models import CSVImportJob, ImportError, ImportStatus
from app.schemas.csv_import_schema import CSVImportOptions
from app.services.csv.error_handler import ErrorCategory, ImportErrorHandler
from app.services.csv_import_service import CSVImportService, get_csv_import_service
from tests.integration.services.seed import (
    dump_rows,
    fmt_dt,
    make_import_error,
    make_import_job,
    normalize,
    uid,
)


def _jobs(database):
    rows = dump_rows(database, CSVImportJob, order_by=[CSVImportJob.submitted_at, CSVImportJob.job_id])
    for row in rows:
        if row["submitted_at"] is not None and row["submitted_at"].year == 2025:
            row["submitted_at"] = fmt_dt(row["submitted_at"])
    return rows


def _errors(database):
    return dump_rows(database, ImportError, order_by=[ImportError.error_id])


@pytest.fixture
def service(clean_db):
    return get_csv_import_service()


def test_create_import_job(service, database, snapshot):
    plain = service.create_import_job("reports.csv")
    typed = service.create_import_job("vision.txt", options=CSVImportOptions(chunk_size=5, stop_on_error=True),
                                      csv_type="vision_data")
    # csv_type is free text: no validation against CSVImportType.
    odd = service.create_import_job("x.csv", csv_type="not-a-type")
    snapshot("csv_create_import_job", normalize({
        "returned": [type(plain).__name__, plain.model_dump(), typed.model_dump(), odd.model_dump()],
        "rows": _jobs(database),
    }))


def test_get_import_job(service, db_session, database, snapshot):
    s = db_session
    make_import_job(s, 1, total_rows=3, processed_rows=1, successful_rows=1, error_count=5,
                    metrics_json={"reports_created": 1}, csv_type="employee_report", status="running")
    make_import_job(s, 2, total_rows=0, processed_rows=4, error_count=0)
    make_import_job(s, 3, total_rows=None, processed_rows=None, successful_rows=None, error_count=None)
    make_import_error(s, uid(1), 2)
    make_import_error(s, uid(1), 3)
    make_import_error(s, uid(2), 1)
    s.commit()
    out = {
        "job_1_error_count_fixed": service.get_import_job(str(uid(1))),
        "job_2_error_count_fixed": service.get_import_job(str(uid(2))),
        "job_3_nulls": service.get_import_job(uid(3)),
        "missing": service.get_import_job(str(uid(99))),
    }
    snapshot("csv_get_import_job", normalize({"returned": out, "rows": _jobs(database)}))


def test_get_import_job_invalid_uuid(service, snapshot):
    with pytest.raises(Exception) as exc:
        service.get_import_job("not-a-uuid")
    snapshot("csv_get_import_job_invalid_uuid", type(exc.value).__module__ + "." + type(exc.value).__name__)


def test_get_job_errors(service, db_session, snapshot):
    s = db_session
    make_import_job(s, 1)
    make_import_job(s, 2)
    make_import_error(s, uid(1), 5, "late row", "Name", {"Name": "x"})
    make_import_error(s, uid(1), 1, "first row", None, None)
    make_import_error(s, uid(1), 3, "middle row", "Date", {"Date": "bad"})
    make_import_error(s, uid(2), 1, "other job")
    s.commit()
    out = {
        "page1_size2": service.get_job_errors(str(uid(1)), page=1, page_size=2),
        "page2_size2": service.get_job_errors(str(uid(1)), page=2, page_size=2),
        "page3_size2": service.get_job_errors(str(uid(1)), page=3, page_size=2),
        "default": service.get_job_errors(uid(1)),
        "unknown_job": service.get_job_errors(str(uid(99))),
    }
    with pytest.raises(Exception) as exc:
        service.get_job_errors(str(uid(1)), page=0)
    out["page0_error"] = type(exc.value).__name__
    snapshot("csv_get_job_errors", normalize(out))


def test_update_job_status(service, db_session, database, snapshot):
    s = db_session
    jobs = {n: make_import_job(s, n, error_count=0) for n in range(1, 6)}
    jobs[5].started_at = datetime(2025, 1, 2, 8, 30)
    make_import_error(s, uid(3), 1)
    make_import_error(s, uid(3), 2)
    s.commit()

    service._update_job_status(s, jobs[1], ImportStatus.RUNNING)
    service._update_job_status(s, jobs[5], ImportStatus.RUNNING)   # started_at kept
    service._update_job_status(s, jobs[2], ImportStatus.COMPLETED, metrics={
        "processed_rows": 10, "successful_rows": 9, "csv_type": "vision_data",
        "metrics": {"records": 9}, "unrelated": 1})
    service._update_job_status(s, jobs[3], ImportStatus.FAILED)                 # count from DB = 2
    service._update_job_status(s, jobs[4], ImportStatus.FAILED)                 # no DB errors -> 1
    service._update_job_status(s, jobs[1], ImportStatus.COMPLETED, metrics={"csv_type": ""}, error_count=7)
    rows = _jobs(database)
    for row in rows:
        if row["started_at"] is not None and row["started_at"].year == 2025:
            row["started_at"] = fmt_dt(row["started_at"])
    snapshot("csv_update_job_status", normalize(rows))


class _Row(BaseModel):
    Name: str
    Age: int


def test_error_handler_to_db_models_and_save_errors(service, db_session, database, snapshot):
    s = db_session
    make_import_job(s, 1, error_count=99)
    s.commit()

    handler = ImportErrorHandler()
    handler.add_validation_error(3, "bad name", "Name", {"Name": ""})
    handler.add_processing_error(4, "weird date", "Date", {"Date": date(2025, 1, 1), "n": None, "ok": 1},
                                 exception=RuntimeError("x"))
    handler.add_database_error(4, "dup", {"set": {1}}, exception=RuntimeError("y"))
    handler.add_error(9, "other")
    try:
        _Row(Name=5, Age="x")
    except ValidationError as err:
        handler.normalize_pydantic_errors(err, 10, {"Name": 5, "Age": "x"})

    models = handler.to_db_models(str(uid(1)))
    summary = {
        "count": handler.get_error_count(),
        "by_category": {k.value: v for k, v in handler.get_error_count_by_category().items()},
        "pct_of_8": handler.get_error_percentage(8),
        "pct_of_0": handler.get_error_percentage(0),
        "by_field": handler.get_error_summary_by_field(),
        "patterns": handler.get_error_patterns(),
        "models": [{"job_id": m.job_id, "row_number": m.row_number, "field_name": m.field_name,
                    "error_message": m.error_message, "row_data": m.row_data} for m in models],
        "should_abort": {
            "stop_on_error": handler.should_abort(1, stop_on_error=True),
            "under_min_rows": handler.should_abort(150),
            "at_200_rows": handler.should_abort(200),
            "at_200_threshold_1pct": handler.should_abort(200, error_threshold_percent=1.0),
            "custom_min": handler.should_abort(10, minimum_rows_before_threshold=5),
        },
    }

    service._save_errors(s, str(uid(1)), handler)
    service._save_errors(s, str(uid(1)), handler)   # saving twice duplicates rows
    snapshot("csv_save_errors", normalize({
        "summary": summary, "errors": _errors(database), "jobs": _jobs(database)}))

    handler.clear()
    assert handler.get_errors() == [] and handler.get_error_count_by_category()[ErrorCategory.OTHER] == 0
