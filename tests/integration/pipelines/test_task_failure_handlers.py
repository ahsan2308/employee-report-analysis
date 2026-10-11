"""The Celery on_failure handlers of the import and sync tasks: a task that dies records why."""
from app.db.database import get_database
from app.models.import_models import ImportError, ImportStatus
from app.models.sync_models import SyncStatus, SyncType
from app.services.csv_import_service import CSVImportService
from app.services.sync.sync_tracker import SyncTracker
from app.tasks.import_tasks import process_csv_import
from app.tasks.sync_tasks import sync_vision_data_task
from tests.integration.pipelines.seed import dump_import_job, dump_sync_history


def test_import_task_failure_marks_job_failed_with_reason(db_session, ext):
    job = CSVImportService().create_import_job(filename="reports.csv")
    process_csv_import.on_failure(RuntimeError("worker lost"), "celery-1", (), {"job_id": job.job_id}, None)
    db_session.expire_all()
    world = dump_import_job(db_session)
    assert world["csv_import_jobs"][0]["status"] == ImportStatus.FAILED.value
    assert world["csv_import_jobs"][0]["error_count"] == 1
    assert [(e["row_number"], e["error_message"]) for e in world["import_errors"]] == [
        (0, "Import task failed: worker lost")]

    # A job the import already failed is left as it is
    process_csv_import.on_failure(RuntimeError("again"), "celery-2", (), {"job_id": job.job_id}, None)
    db_session.expire_all()
    assert db_session.query(ImportError).count() == 1


def test_sync_task_failure_marks_sync_failed(db_session, ext):
    with get_database().create_session() as session:
        sync_id = SyncTracker(None).create_sync_job(SyncType.VISION_DATA, session=session).sync_id
        session.commit()
    sync_vision_data_task.on_failure(RuntimeError("source down"), "celery-1", (), {"sync_id": str(sync_id)}, None)
    db_session.expire_all()
    [row] = dump_sync_history(db_session)
    assert (row["status"], row["error_message"]) == (SyncStatus.FAILED.value, "source down")
    assert row["completed_at"] is not None

    # A sync already FAILED keeps its first message
    sync_vision_data_task.on_failure(RuntimeError("later"), "celery-2", (), {"sync_id": str(sync_id)}, None)
    db_session.expire_all()
    assert dump_sync_history(db_session)[0]["error_message"] == "source down"
