"""Fixed seed data and DB dump helpers for the pipeline characterization tests.

Every value is literal; nothing depends on the clock. Wall-clock audit columns
(created_at, started_at, ...) are dumped as ISO strings and blanked by ``scrub``.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import inspect as sa_inspect, text

from app.models.db_models import (
    Employee,
    EmployeeAnalysis,
    EmployeeJobDescription,
    MonthlyAnalysis,
    QdrantMapping,
    QuarterlyAnalysis,
    Report,
    SupervisorFeedbackForm,
    SupervisorFeedbackMetricDefinition,
    SupervisorFeedbackResponse,
)
from app.models.import_models import CSVImportJob, ImportError
from app.models.sync_models import SyncHistory
from app.models.task_models import BackgroundTask, TaskStatus, TaskType
from app.models.vision_data_models import EmployeeVisionData

EMP_ID = 101
OTHER_EMP_ID = 102

REPORT_IDS = {
    date(2025, 3, 7): uuid.UUID("00000000-0000-4000-8000-0000000000a1"),
    date(2025, 3, 14): uuid.UUID("00000000-0000-4000-8000-0000000000a2"),
    date(2025, 3, 21): uuid.UUID("00000000-0000-4000-8000-0000000000a3"),
    date(2025, 3, 28): uuid.UUID("00000000-0000-4000-8000-0000000000a4"),
    date(2025, 2, 14): uuid.UUID("00000000-0000-4000-8000-0000000000b1"),
    date(2025, 1, 17): uuid.UUID("00000000-0000-4000-8000-0000000000c1"),
}
CURRENT_REPORT_DATE = date(2025, 3, 28)

TASK_IDS = {
    "weekly": uuid.UUID("00000000-0000-4000-9000-000000000001"),
    "monthly": uuid.UUID("00000000-0000-4000-9000-000000000002"),
    "quarterly": uuid.UUID("00000000-0000-4000-9000-000000000003"),
}

AUDIT_TS = datetime(2025, 3, 29, 9, 0, 0)

# Seeded ids are literal, so snapshots keep them verbatim (scrub(..., keep_uuids=FIXED_UUIDS)).
FIXED_UUIDS = tuple(str(u) for u in (*REPORT_IDS.values(), *TASK_IDS.values()))


def report_text(day: date) -> str:
    return "\n\n".join([
        f"Tasks Completed: Reviewed {day.day} case files and closed the backlog for week ending {day.isoformat()}.",
        "Impact: Backlog reduced by 20 percent.",
        "Challenges: Two field reports arrived late.",
        "Support Required: Access to the archive scanner.",
        "Tasks Planned: Draft the monthly summary.",
        "Confidence Level: 4",
        f"Report Period: {day.replace(day=max(1, day.day - 6)).isoformat()} to {day.isoformat()}",
    ])


# --------------------------------------------------------------------------- seeding

def seed_employees(session) -> None:
    session.add_all([
        Employee(id=EMP_ID, name="Ayesha Khan", wing="Technical", position="Analyst (BS-17)"),
        Employee(id=OTHER_EMP_ID, name="Bilal Ahmed", wing="Operations", position="Officer (BS-16)"),
    ])
    session.commit()


def seed_reports(session, dates: Iterable[date] = tuple(REPORT_IDS)) -> None:
    for day in sorted(dates):
        session.add(Report(report_id=REPORT_IDS[day], employee_id=EMP_ID, report_date=day,
                           report_text=report_text(day)))
    session.commit()


def seed_vision(session) -> None:
    session.add_all([
        EmployeeVisionData(employee_id=EMP_ID, from_date=date(2025, 3, 22), to_date=date(2025, 3, 28),
                           main_entity="Persons", sub_entities={"Persons": 3, "Pictures": 1, "Numbers": 0},
                           sub_entities_content={"Persons": [{"name": "Person A"}, {"name": "Person B"}],
                                                 "Pictures": [{"file": "img-1.jpg"}]},
                           created_at=AUDIT_TS, updated_at=AUDIT_TS),
        EmployeeVisionData(employee_id=EMP_ID, from_date=date(2025, 3, 15), to_date=date(2025, 3, 21),
                           main_entity="Tasks", sub_entities={"Tasks": 2, "Task Updates": 4},
                           sub_entities_content={"Tasks": [{"title": "Archive audit"}, {"title": "Ledger check"}]},
                           created_at=AUDIT_TS, updated_at=AUDIT_TS),
        EmployeeVisionData(employee_id=EMP_ID, from_date=date(2025, 2, 8), to_date=date(2025, 2, 14),
                           main_entity="Activities and Cases", sub_entities={"Cases": 1, "Activities": 2},
                           sub_entities_content={"Cases": [{"title": "Case 77"}]},
                           created_at=AUDIT_TS, updated_at=AUDIT_TS),
    ])
    session.commit()


def seed_jds(session) -> None:
    session.add_all([
        EmployeeJobDescription(employee_id=EMP_ID, jd_id="900",
                               job_description="Junior analyst: maintains case registers and prepares weekly digests for the wing head.",
                               assigned_date=date(2023, 1, 1), end_date=date(2025, 3, 10), is_current=False,
                               created_at=AUDIT_TS, updated_at=AUDIT_TS),
        EmployeeJobDescription(employee_id=EMP_ID, jd_id="1001",
                               job_description="Analyst: leads backlog reduction, audits archives and drafts monthly performance summaries.",
                               assigned_date=date(2025, 3, 11), end_date=None, is_current=True,
                               created_at=AUDIT_TS, updated_at=AUDIT_TS),
    ])
    session.commit()


def seed_weekly_analyses(session, dates: Sequence[date] = (date(2025, 3, 7), date(2025, 3, 14), date(2025, 3, 21))) -> None:
    sentiments = [0.5, 0.8, 0.8, 0.2]
    for i, day in enumerate(dates):
        session.add(EmployeeAnalysis(
            report_id=REPORT_IDS[day], employee_id=EMP_ID, sentiment_score=sentiments[i % 4],
            risk_level=["low", "medium", "low"][i % 3], risk_explanation=f"Risk note {i}",
            full_analysis_json={"sentiment": "positive", "week": day.isoformat()},
            achievements_json=[{"description": f"Closed backlog batch {i}", "impact": f"{6 + i} (backlog)"}],
            challenges_json=[{"description": "Late field reports", "severity": "medium"}],
            topics=["backlog", "archives"] if i % 2 == 0 else ["backlog"],
            action_items=["Escalate late reports"],
            credibility_rating="high", credibility_explanation="Consistent with vision data",
            exaggeration_flags=[], consistency_score="high",
            performance_rating="high", performance_summary=f"Solid week {i}",
            performance_strengths=["Diligent"], performance_improvement_areas=["Delegation"],
            analysis_date=AUDIT_TS, created_at=AUDIT_TS, updated_at=AUDIT_TS,
        ))
    session.commit()


def seed_monthly_analyses(session, months: Sequence[int] = (1, 2, 3)) -> None:
    import calendar
    for m in months:
        last = calendar.monthrange(2025, m)[1]
        session.add(MonthlyAnalysis(
            employee_id=EMP_ID, year=2025, month=m, period_start=date(2025, m, 1), period_end=date(2025, m, last),
            weekly_report_ids=[str(REPORT_IDS[d]) for d in sorted(REPORT_IDS) if d.month == m],
            avg_sentiment_score=0.6 + m / 10, sentiment_trend="stable", performance_trend="improving",
            risk_level_pattern="stable", challenge_resolution_progress="improved",
            risk_level="low", risk_explanation=f"Month {m} risk", significant_risks=["Late reports"],
            escalating_risks=[], risk_mitigation_recommendations=["Weekly sync"],
            monthly_achievements=[{"description": f"Month {m} backlog cleared", "impact": "8 (major)", "impact_score": 8}],
            recurring_challenges=[{"description": "Late field reports", "severity": "medium", "status": "ongoing"}],
            achievement_impact_avg=8.0, task_completion_reliability="high", work_quality_consistency="high",
            performance_stability="medium", consistency_notable_strengths=["Reliable"],
            consistency_notable_weaknesses=["Delegation"], complexity_of_tasks="increased",
            skill_development_evidence="medium", confidence_level_change="increased",
            approach_to_challenges="more proactive",
            focus_areas=[{"project": "Archive audit", "time_investment": "high", "priority_level": "high"}],
            strategic_recommendations=[{"action": "Mentor juniors", "priority": "medium"}],
            monthly_summary=f"Summary for month {m}.", full_analysis_json={"month": m},
            analysis_date=AUDIT_TS,
        ))
    session.commit()


def add_task(session, kind: str, task_type: TaskType, **fields) -> uuid.UUID:
    task = BackgroundTask(task_id=TASK_IDS[kind], task_type=task_type.value, status=TaskStatus.PENDING.value,
                          created_at=AUDIT_TS, **fields)
    session.add(task)
    session.commit()
    return task.task_id


def seed_analysis_world(session, vision: bool = True, jds: bool = True, weekly: bool = True,
                        monthly: bool = True) -> None:
    seed_employees(session)
    seed_reports(session)
    if vision:
        seed_vision(session)
    if jds:
        seed_jds(session)
    if weekly:
        seed_weekly_analyses(session)
    if monthly:
        seed_monthly_analyses(session, months=(1, 2))


# --------------------------------------------------------------------------- dumping

def _plain(value: Any, keep_datetime: bool = False) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return repr(value) if keep_datetime else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_plain(v, keep_datetime) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v, keep_datetime) for k, v in value.items()}
    return value


def row_to_dict(obj, keep_datetimes: Sequence[str] = (), drop: Sequence[str] = ()) -> Dict[str, Any]:
    """All mapped columns of an ORM object. Datetime columns named in keep_datetimes are kept via repr."""
    out = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        if attr.key in drop:
            continue
        out[attr.key] = _plain(getattr(obj, attr.key), keep_datetime=attr.key in keep_datetimes)
    return out


def dump(session, model, order_by, **kwargs) -> List[Dict[str, Any]]:
    session.expire_all()
    return [row_to_dict(r, **kwargs) for r in session.query(model).order_by(*order_by).all()]


def dump_mappings(session, document_order: List[str]) -> List[Dict[str, Any]]:
    """qdrant_mappings joined to their report; qdrant_id replaced by its position in the upsert stream."""
    rows = session.execute(text(
        "SELECT m.qdrant_id, m.chunk_index, r.employee_id, r.report_date "
        "FROM qdrant_mappings m JOIN reports r ON r.report_id = m.report_id"
    )).fetchall()
    out = []
    for qdrant_id, chunk_index, employee_id, report_date in rows:
        qid = str(qdrant_id)
        out.append({
            "employee_id": employee_id,
            "report_date": report_date.isoformat(),
            "chunk_index": chunk_index,
            "upserted_point_index": document_order.index(qid) if qid in document_order else None,
        })
    return sorted(out, key=lambda r: (r["employee_id"], r["report_date"], r["chunk_index"],
                                      -1 if r["upserted_point_index"] is None else r["upserted_point_index"]))


def dump_analysis_tables(session) -> Dict[str, Any]:
    return {
        "background_tasks": dump(session, BackgroundTask, [BackgroundTask.task_id]),
        "employee_analyses": dump(session, EmployeeAnalysis, [EmployeeAnalysis.analysis_id]),
        "monthly_analyses": dump(session, MonthlyAnalysis, [MonthlyAnalysis.analysis_id]),
        "quarterly_analyses": dump(session, QuarterlyAnalysis, [QuarterlyAnalysis.analysis_id]),
    }


def dump_data_tables(session, document_order: Optional[List[str]] = None) -> Dict[str, Any]:
    tables = {
        "employees": dump(session, Employee, [Employee.id]),
        "reports": dump(session, Report, [Report.employee_id, Report.report_date]),
        "employee_vision_data": dump(session, EmployeeVisionData, [
            EmployeeVisionData.employee_id, EmployeeVisionData.from_date, EmployeeVisionData.to_date,
            EmployeeVisionData.main_entity], drop=("record_id",)),
        "employee_job_descriptions": dump(session, EmployeeJobDescription, [
            EmployeeJobDescription.employee_id, EmployeeJobDescription.jd_id]),
        "supervisor_feedback_metric_definitions": dump(session, SupervisorFeedbackMetricDefinition, [
            SupervisorFeedbackMetricDefinition.metric_id]),
        "supervisor_feedback_forms": dump(session, SupervisorFeedbackForm, [SupervisorFeedbackForm.ro_form_id]),
        "supervisor_feedback_responses": dump(session, SupervisorFeedbackResponse, [
            SupervisorFeedbackResponse.l_ro_form_metric_id]),
    }
    tables["qdrant_mappings"] = dump_mappings(session, document_order or [])
    return tables


def dump_import_job(session) -> Dict[str, Any]:
    return {
        "csv_import_jobs": dump(session, CSVImportJob, [CSVImportJob.submitted_at, CSVImportJob.filename]),
        "import_errors": dump(session, ImportError, [ImportError.error_id]),
    }


def dump_sync_history(session) -> List[Dict[str, Any]]:
    return dump(session, SyncHistory, [SyncHistory.sync_type, SyncHistory.started_at],
                keep_datetimes=("last_sync_timestamp",))


def seed_import_employees(session) -> None:
    """Employees referenced by the vision / JD / supervisor-feedback sample files."""
    session.add_all([
        Employee(id=201, name="Sana Malik", wing="Technical>Tech-I>SOC", position="Analyst (BS-17)"),
        Employee(id=202, name="Omar Farooq", wing="Operations>Ops-II", position="Officer (BS-16)"),
    ])
    session.commit()
