"""CSV import jobs and their row errors (CSVImportJob, ImportError), in the caller's session."""
from typing import Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.import_models import CSVImportJob, ImportError


def get_job(session: Session, job_id) -> Optional[CSVImportJob]:
    return session.query(CSVImportJob).filter(CSVImportJob.job_id == job_id).first()


def add_job(session: Session, job: CSVImportJob) -> CSVImportJob:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def list_jobs(session: Session, status: Optional[str] = None, csv_type: Optional[str] = None,
              limit: int = 50, offset: int = 0) -> List[CSVImportJob]:
    """Import jobs, newest first."""
    query = session.query(CSVImportJob)
    if status:
        query = query.filter(CSVImportJob.status == status)
    if csv_type:
        query = query.filter(CSVImportJob.csv_type == csv_type)
    return query.order_by(CSVImportJob.submitted_at.desc()).offset(offset).limit(limit).all()


def count_errors(session: Session, job_id) -> int:
    return session.query(ImportError).filter(ImportError.job_id == job_id).count()


def error_counts(session: Session, job_ids: Iterable) -> Dict:
    """Stored error rows per job id (jobs without errors are absent)."""
    job_ids = list(job_ids)
    if not job_ids:
        return {}
    return dict(
        session.query(ImportError.job_id, func.count(ImportError.error_id))
        .filter(ImportError.job_id.in_(job_ids))
        .group_by(ImportError.job_id)
        .all()
    )


def add_errors(session: Session, errors: Iterable[ImportError]) -> None:
    for error in errors:
        session.add(error)
    session.commit()


def page_errors(session: Session, job_id, offset: int, limit: int) -> List[ImportError]:
    """A job's errors in row order."""
    return session.query(ImportError).filter(
        ImportError.job_id == job_id
    ).order_by(ImportError.row_number).offset(offset).limit(limit).all()
