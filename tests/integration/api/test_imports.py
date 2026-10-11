"""Characterization of the /imports router (process_csv_import.delay patched in conftest)."""
from datetime import datetime, timedelta

import pytest

from app.models.import_models import CSVImportJob
from tests.integration.api.seed import add_import_error, add_import_job, dump_rows, fixed_uuid

CSV_BODY = b"Name,Wing,Position\nAlice,Engineering,Engineer\n"
TSV_BODY = b"Name\tWing\tPosition\nAlice\tEngineering\tEngineer\n"


def _jobs(db):
    return dump_rows(db, CSVImportJob, order_by=[CSVImportJob.submitted_at, CSVImportJob.filename])


def _upload(api, filename, content=CSV_BODY, **form):
    data = {key: str(value) for key, value in form.items()}
    return api.post("/imports/upload", files={"file": (filename, content, "application/octet-stream")}, data=data)


# =========================================================================== POST /imports/upload

@pytest.mark.parametrize("filename,content", [
    ("reports.csv", CSV_BODY),
    ("vision.tsv", TSV_BODY),
    ("vision.txt", TSV_BODY),
    ("UPPER.CSV", CSV_BODY),
], ids=["csv", "tsv", "txt", "uppercase_csv"])
def test_upload_auto_detects_format(api, db_session, snap, dispatch, filename, content, request):
    resp = _upload(api, filename, content)
    snap(f"imports_upload_{request.node.callspec.id}", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_with_explicit_options(api, db_session, snap, dispatch):
    resp = _upload(
        api, "data.txt", CSV_BODY,
        dry_run="true", stop_on_error="true", error_threshold_percent="2.5", chunk_size="50",
        processing_mode="row_by_row", file_format="csv", delimiter=",", encoding="utf-8",
        csv_type="vision_data",
    )
    snap("imports_upload_explicit_options", resp, db=_jobs(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("csv_type", ["employee_report", "vision_data", "job_descriptions", "supervisor_feedback"])
def test_upload_each_csv_type(api, db_session, snap, dispatch, csv_type):
    resp = _upload(api, "file.csv", CSV_BODY, csv_type=csv_type)
    snap(f"imports_upload_type_{csv_type}", resp, db=_jobs(db_session), dispatch=dispatch.calls)


@pytest.mark.parametrize("filename", ["report.xlsx", "report.csv.bak", "noextension"])
def test_upload_unsupported_extension_400(api, db_session, snap, dispatch, filename):
    resp = _upload(api, filename)
    snap(f"imports_upload_bad_extension_{filename.replace('.', '_')}", resp, db=_jobs(db_session),
         dispatch=dispatch.calls)


def test_upload_invalid_csv_type_400(api, db_session, snap, dispatch):
    resp = _upload(api, "file.csv", csv_type="payroll")
    snap("imports_upload_invalid_csv_type", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_extension_checked_before_csv_type(api, db_session, snap, dispatch):
    resp = _upload(api, "file.xls", csv_type="payroll")
    snap("imports_upload_extension_before_type", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_invalid_processing_mode_500(api, db_session, snap, dispatch):
    resp = _upload(api, "file.csv", processing_mode="turbo")
    snap("imports_upload_invalid_processing_mode", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_invalid_file_format_500(api, db_session, snap, dispatch):
    resp = _upload(api, "file.csv", file_format="xml")
    snap("imports_upload_invalid_file_format", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_empty_file_is_accepted(api, db_session, snap, dispatch):
    resp = _upload(api, "empty.csv", b"")
    snap("imports_upload_empty_file", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_non_numeric_chunk_size_422(api, db_session, snap, dispatch):
    resp = _upload(api, "file.csv", chunk_size="lots")
    snap("imports_upload_bad_chunk_size", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_missing_file_422(api, db_session, snap, dispatch):
    resp = api.post("/imports/upload", data={"dry_run": "true"})
    snap("imports_upload_missing_file", resp, db=_jobs(db_session), dispatch=dispatch.calls)


def test_upload_dispatch_failure_marks_job_failed(api, db_session, snap, dispatch):
    from unittest import mock

    with mock.patch("app.tasks.dispatch.process_csv_import") as broken:
        broken.delay.side_effect = RuntimeError("broker unreachable")
        resp = _upload(api, "file.csv")
    snap("imports_upload_dispatch_failure", resp, db=_jobs(db_session))


# =========================================================================== GET /imports/{job_id}

def test_get_job(api, db_session, snap):
    add_import_job(db_session, job_id=fixed_uuid(1), status="running", total_rows=8, processed_rows=3,
                   successful_rows=2, started_at=datetime(2025, 3, 14, 9, 31), metrics_json={"reports_created": 2})
    snap("imports_get_job", api.get(f"/imports/{fixed_uuid(1)}"), db=_jobs(db_session))


def test_get_job_reports_stored_errors_without_writing(api, db_session, snap):
    add_import_job(db_session, job_id=fixed_uuid(1), error_count=5)
    add_import_error(db_session, fixed_uuid(1), 2)
    add_import_error(db_session, fixed_uuid(1), 7)
    snap("imports_get_job_error_count_read_only", api.get(f"/imports/{fixed_uuid(1)}"), db=_jobs(db_session))


def test_get_job_not_found_404(api, snap):
    snap("imports_get_job_missing", api.get(f"/imports/{fixed_uuid(404)}"))


def test_get_job_invalid_uuid_500(api, snap):
    snap("imports_get_job_invalid_uuid", api.get("/imports/not-a-uuid"))


# =========================================================================== GET /imports/{job_id}/errors

def _seed_errors(db):
    add_import_job(db, job_id=fixed_uuid(1), error_count=5)
    for row in [9, 3, 5, 1, 7]:
        add_import_error(db, fixed_uuid(1), row, field_name=f"F{row}", message=f"bad row {row}")
    add_import_job(db, job_id=fixed_uuid(2), filename="other.csv")
    add_import_error(db, fixed_uuid(2), 1, message="other job")


def test_get_errors_default_page(api, db_session, snap):
    _seed_errors(db_session)
    snap("imports_errors_default", api.get(f"/imports/{fixed_uuid(1)}/errors"))


@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_get_errors_pagination(api, db_session, snap, page):
    _seed_errors(db_session)
    snap(f"imports_errors_page_{page}", api.get(f"/imports/{fixed_uuid(1)}/errors",
                                                params={"page": page, "page_size": 2}))


def test_get_errors_job_without_errors(api, db_session, snap):
    add_import_job(db_session, job_id=fixed_uuid(1))
    snap("imports_errors_none", api.get(f"/imports/{fixed_uuid(1)}/errors"))


def test_get_errors_job_not_found_404(api, snap):
    snap("imports_errors_missing_job", api.get(f"/imports/{fixed_uuid(404)}/errors"))


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 1001}, {"page": "x"}],
                         ids=["page0", "page_size0", "page_size1001", "page_str"])
def test_get_errors_invalid_pagination_422(api, db_session, snap, params, request):
    add_import_job(db_session, job_id=fixed_uuid(1))
    snap(f"imports_errors_invalid_{request.node.callspec.id}",
         api.get(f"/imports/{fixed_uuid(1)}/errors", params=params))


# =========================================================================== GET /imports/

def _seed_jobs(db):
    base = datetime(2025, 3, 1, 12, 0, 0)
    add_import_job(db, job_id=fixed_uuid(1), filename="a.csv", status="completed", csv_type="employee_report",
                   submitted_at=base, total_rows=10, processed_rows=10, successful_rows=9, error_count=1,
                   metrics_json={"reports_created": 9})
    add_import_job(db, job_id=fixed_uuid(2), filename="b.txt", status="running", csv_type="vision_data",
                   submitted_at=base + timedelta(hours=1), total_rows=3, processed_rows=1)
    add_import_job(db, job_id=fixed_uuid(3), filename="c.csv", status="failed", csv_type=None,
                   submitted_at=base + timedelta(hours=2), total_rows=None, processed_rows=None,
                   successful_rows=None, error_count=None)
    add_import_job(db, job_id=fixed_uuid(4), filename="d.csv", status="pending", csv_type="employee_report",
                   submitted_at=base + timedelta(hours=3))


def test_list_jobs_empty(api, snap):
    snap("imports_list_empty", api.get("/imports/"))


def test_list_jobs_newest_first(api, db_session, snap):
    _seed_jobs(db_session)
    snap("imports_list_all", api.get("/imports/"))


@pytest.mark.parametrize("params", [
    {"status": "completed"},
    {"status": "running"},
    {"csv_type": "employee_report"},
    {"status": "pending", "csv_type": "employee_report"},
    {"csv_type": "supervisor_feedback"},
    {"limit": 2},
    {"limit": 2, "offset": 2},
    {"offset": 10},
], ids=["status_completed", "status_running", "type_employee_report", "status_and_type", "type_no_match",
        "limit2", "limit2_offset2", "offset_past_end"])
def test_list_jobs_filters(api, db_session, snap, params, request):
    _seed_jobs(db_session)
    snap(f"imports_list_{request.node.callspec.id}", api.get("/imports/", params=params))


@pytest.mark.parametrize("params", [
    {"status": "done"},
    {"csv_type": "payroll"},
    {"limit": 0},
    {"limit": 1001},
    {"offset": -1},
], ids=["bad_status_400", "bad_type_400", "limit0_422", "limit1001_422", "offset_neg_422"])
def test_list_jobs_invalid(api, snap, params, request):
    snap(f"imports_list_invalid_{request.node.callspec.id}", api.get("/imports/", params=params))
