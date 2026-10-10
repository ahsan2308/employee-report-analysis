"""Seed builders and snapshot helpers for the service-layer characterization tests.

Every builder takes an open ORM session, adds rows with fixed values and flushes
(callers commit). Report/record ids use ``uid(n)`` so snapshots can keep them
verbatim (see ``KEEP_UUIDS``) and show which seeded row came back.
"""
import json
import uuid
from datetime import date, datetime
from typing import Any, Iterable, Optional

from sqlalchemy import inspect as sa_inspect

from tests.support.scrub import scrub

from app.models.db_models import (
    Employee,
    EmployeeAnalysis,
    EmployeeJobDescription,
    MonthlyAnalysis,
    QuarterlyAnalysis,
    Report,
)
from app.models.import_models import CSVImportJob, ImportError
from app.models.sync_models import SyncHistory
from app.models.task_models import BackgroundTask
from app.models.vision_data_models import EmployeeVisionData


def uid(n: int) -> uuid.UUID:
    """Deterministic UUID for seeded rows: 00000000-0000-0000-0000-<n>."""
    return uuid.UUID(f"00000000-0000-0000-0000-{n:012d}")


KEEP_UUIDS = tuple(str(uid(n)) for n in range(1, 1000))


def normalize(value: Any) -> Any:
    """JSON-round-trip (dates -> str) then scrub timestamps and random UUIDs."""
    return scrub(json.loads(json.dumps(value, default=str)), keep_uuids=KEEP_UUIDS)


def fmt_dt(value: Optional[datetime]) -> Optional[str]:
    """Render a seeded (fixed) datetime in a form ``scrub`` leaves alone."""
    return None if value is None else value.strftime("%Y-%m-%d@%H:%M:%S.%f")


def row_dict(obj) -> dict:
    mapper = sa_inspect(obj).mapper
    return {col.key: getattr(obj, col.key) for col in mapper.column_attrs}


def dump_rows(database, model, order_by: Iterable = ()) -> list:
    """Read every row of ``model`` through a fresh session (what is committed)."""
    session = database.create_session()
    try:
        query = session.query(model)
        if order_by:
            query = query.order_by(*order_by)
        else:
            query = query.order_by(*sa_inspect(model).primary_key)
        return [row_dict(row) for row in query.all()]
    finally:
        session.close()


# ---------------------------------------------------------------- builders

def make_employee(session, id: int, name: str = None, wing: str = "Engineering",
                  position: str = "Engineer") -> Employee:
    employee = Employee(id=id, name=name or f"Employee {id}", wing=wing, position=position)
    session.add(employee)
    session.flush()
    return employee


def make_report(session, n: int, employee_id: int, report_date: date,
                text: Optional[str] = None) -> Report:
    report = Report(
        report_id=uid(n),
        employee_id=employee_id,
        report_date=report_date,
        report_text=f"report {n} text" if text is None else text,
    )
    session.add(report)
    session.flush()
    return report


def make_analysis(session, report: Report, **fields) -> EmployeeAnalysis:
    values = dict(
        report_id=report.report_id,
        employee_id=report.employee_id,
        sentiment_score=0.5,
        risk_level="low",
        full_analysis_json={"summary": f"analysis of {report.report_id}"},
    )
    values.update(fields)
    analysis = EmployeeAnalysis(**values)
    session.add(analysis)
    session.flush()
    return analysis


def make_vision(session, n: int, employee_id: int, from_date: date, to_date: date,
                main_entity: str = "Meetings", sub_entities=None, content=None) -> EmployeeVisionData:
    record = EmployeeVisionData(
        record_id=uid(n),
        employee_id=employee_id,
        from_date=from_date,
        to_date=to_date,
        main_entity=main_entity,
        sub_entities=sub_entities if sub_entities is not None else {"count": n},
        sub_entities_content=content,
    )
    session.add(record)
    session.flush()
    return record


def make_monthly(session, employee_id: int, year: int, month: int, **fields) -> MonthlyAnalysis:
    from app.domain.periods import get_month_date_range

    start, end = get_month_date_range(year, month)
    values = dict(
        employee_id=employee_id,
        year=year,
        month=month,
        period_start=start,
        period_end=end,
        avg_sentiment_score=0.6,
        performance_trend="improving",
        risk_level="low",
        monthly_summary=f"summary {year}-{month}",
        full_analysis_json={"month": month},
    )
    values.update(fields)
    analysis = MonthlyAnalysis(**values)
    session.add(analysis)
    session.flush()
    return analysis


def make_quarterly(session, employee_id: int, year: int, quarter: int, **fields) -> QuarterlyAnalysis:
    from app.domain.periods import get_quarter_date_range

    start, end = get_quarter_date_range(year, quarter)
    values = dict(
        employee_id=employee_id,
        year=year,
        quarter=quarter,
        period_start=start,
        period_end=end,
        performance_trend="stable",
        risk_level="medium",
        quarterly_summary=f"Q{quarter} {year}",
        full_analysis_json={"quarter": quarter},
    )
    values.update(fields)
    analysis = QuarterlyAnalysis(**values)
    session.add(analysis)
    session.flush()
    return analysis


def make_jd(session, employee_id: int, jd_id: str, assigned: date, end: Optional[date],
            is_current: bool) -> EmployeeJobDescription:
    jd = EmployeeJobDescription(
        employee_id=employee_id,
        jd_id=jd_id,
        job_description=f"JD text for {jd_id}",
        assigned_date=assigned,
        end_date=end,
        is_current=is_current,
    )
    session.add(jd)
    session.flush()
    return jd


def make_task(session, n: int, **fields) -> BackgroundTask:
    values = dict(task_id=uid(n), celery_task_id=f"celery-{n}",
                  created_at=datetime(2025, 1, 1, 9, 0, 0))
    values.update(fields)
    task = BackgroundTask(**values)
    session.add(task)
    session.flush()
    return task


def make_sync(session, n: int, sync_type: str, status: str, started_at: datetime,
              last_sync_timestamp: Optional[datetime] = None, **fields) -> SyncHistory:
    sync = SyncHistory(sync_id=uid(n), sync_type=sync_type, status=status,
                       started_at=started_at, last_sync_timestamp=last_sync_timestamp, **fields)
    session.add(sync)
    session.flush()
    return sync


def make_import_job(session, n: int, **fields) -> CSVImportJob:
    values = dict(job_id=uid(n), filename=f"file{n}.csv", status="pending",
                  submitted_at=datetime(2025, 1, 2, 8, 0, 0))
    values.update(fields)
    job = CSVImportJob(**values)
    session.add(job)
    session.flush()
    return job


def make_import_error(session, job_id, row_number: int, message: str = None,
                      field_name: Optional[str] = None, row_data=None) -> ImportError:
    error = ImportError(job_id=job_id, row_number=row_number, field_name=field_name,
                        error_message=message or f"error on row {row_number}", row_data=row_data)
    session.add(error)
    session.flush()
    return error


# ------------------------------------------------- visualization dataset

def seed_visualization_dataset(session) -> None:
    """Weekly analyses for 3 employees in 2 departments, Dec 2024 - Jun 2025.

    Dates deliberately straddle ISO-week/year (2024-12-30 is ISO 2025-W1),
    week 9/10, month, and quarter boundaries.
    """
    make_employee(session, 1, "Alice", "Engineering", "Developer")
    make_employee(session, 2, "Bob", "Engineering", "Tester")
    make_employee(session, 3, "Carol", "Finance", "Analyst")

    rows = [
        # n, emp, date, sentiment, risk, credibility, consistency, performance, achievements
        (101, 1, date(2024, 12, 30), 0.40, "high", "low", "medium", "low",
         [{"description": "a", "impact": "8 (Good impact)"}]),
        (102, 1, date(2025, 1, 6), 0.55, "medium", "medium", "high", "medium",
         [{"description": "b", "impact": "9/10"}, {"description": "c", "impact": "7"}]),
        (103, 2, date(2025, 1, 6), 0.65, "low", "high", "high", "high",
         [{"description": "d", "impact": "It has a high impact (6) on the team"}]),
        (104, 3, date(2025, 1, 31), 0.30, "High ", "unknown", None, "MEDIUM",
         [{"description": "e", "impact": "Impact rating: 5"}, {"description": "f", "impact": "huge"}]),
        (105, 1, date(2025, 2, 3), 0.70, "low", "high", "medium", "high",
         ["not a dict", {"description": "no impact key"}]),
        (106, 2, date(2025, 2, 24), 0.20, "high", "low", "low", "low",
         [{"description": "g", "impact": "4"}]),
        (107, 3, date(2025, 3, 3), 0.80, "low", "high", "high", "high",
         [{"description": "h", "impact": "10/10"}]),
        (108, 1, date(2025, 3, 3), 0.60, None, None, "medium", None, None),
        (109, 1, date(2025, 3, 31), 0.90, "low", "high", "high", "high", []),
        (110, 2, date(2025, 4, 1), 0.10, "high", "low", "low", "low",
         [{"description": "i", "impact": "3 (low)"}]),
        (111, 3, date(2025, 6, 30), 0.50, "medium", "medium", "medium", "medium",
         [{"description": "j", "impact": "6.5"}]),
    ]
    for n, emp, day, sentiment, risk, cred, cons, perf, achievements in rows:
        report = make_report(session, n, emp, day)
        make_analysis(
            session, report,
            sentiment_score=sentiment,
            risk_level=risk,
            credibility_rating=cred,
            consistency_score=cons,
            performance_rating=perf,
            achievements_json=achievements,
        )
