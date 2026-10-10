"""Deterministic ORM seed builders and DB dump helpers for the API tests.

All values are fixed (dates, UUIDs, texts). Integer primary keys are
deterministic because ``clean_db`` truncates with RESTART IDENTITY.
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import inspect

from app.models.db_models import Employee, EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis, Report
from app.models.import_models import CSVImportJob, ImportError
from app.models.sync_models import SyncHistory
from app.models.task_models import BackgroundTask


def fixed_uuid(n: int) -> uuid.UUID:
    """A valid version-4 UUID with a recognisable, fixed value."""
    return uuid.UUID(f"00000000-0000-4000-8000-{n:012d}")


FIXED_NOW = datetime(2025, 3, 14, 9, 30, 0)


# --------------------------------------------------------------------------- employees / reports

def add_employee(db, name="Alice Analyst", wing="Engineering", position="Engineer"):
    employee = Employee(name=name, wing=wing, position=position)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def seed_employees(db):
    """Three employees: ids 1, 2, 3 (two wings)."""
    return [
        add_employee(db, "Alice Analyst", "Engineering", "Engineer"),
        add_employee(db, "Bob Builder", "Finance", "Analyst"),
        add_employee(db, "Carol Coder", "Engineering", "Lead"),
    ]


def add_report(db, employee_id, report_date, text="Weekly report text", report_id=None):
    report = Report(
        report_id=report_id or uuid.uuid4(),
        employee_id=employee_id,
        report_date=report_date,
        report_text=text,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def add_analysis(db, report, **overrides):
    values = dict(
        report_id=report.report_id,
        employee_id=report.employee_id,
        analysis_date=FIXED_NOW,
        sentiment_score=0.75,
        risk_level="low",
        risk_explanation="No notable risks.",
        credibility_rating="high",
        credibility_explanation="Claims are specific and consistent.",
        exaggeration_flags=["claimed 100% uptime"],
        consistency_score="high",
        performance_rating="high",
        performance_summary="Strong week.",
        performance_strengths=["delivery"],
        performance_improvement_areas=["documentation"],
        full_analysis_json={"summary": "Strong week", "score": 8},
        achievements_json=[{"description": "Shipped feature", "impact": "8 (Good impact)"}],
        challenges_json=[{"description": "Flaky CI", "severity": "medium"}],
        topics=["release", "ci"],
        action_items=["write docs"],
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )
    values.update(overrides)
    analysis = EmployeeAnalysis(**values)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


# --------------------------------------------------------------------------- monthly / quarterly

def monthly_full_fields():
    return dict(
        avg_sentiment_score=0.71,
        sentiment_trend="improving",
        performance_trend="stable",
        risk_level_pattern="decreasing",
        challenge_resolution_progress="improved",
        risk_level="low",
        risk_explanation="Risks under control.",
        significant_risks=["vendor delay"],
        escalating_risks=[],
        risk_mitigation_recommendations=["add buffer"],
        monthly_achievements=[
            {"description": "Release 1.2", "impact_score": 8, "impact_reason": "team", "vision_verification": "supported"},
            {"description": "Mentoring", "impact_score": 6, "impact_reason": "individual", "vision_verification": "none"},
        ],
        recurring_challenges=[
            {"description": "Flaky CI", "severity": "medium", "status": "ongoing"},
        ],
        achievement_impact_avg=7.0,
        task_completion_reliability="high",
        work_quality_consistency="medium",
        performance_stability="high",
        consistency_notable_strengths=["on time"],
        consistency_notable_weaknesses=["docs"],
        complexity_of_tasks="increased",
        skill_development_evidence="medium",
        confidence_level_change="increased",
        approach_to_challenges="more proactive",
        focus_areas=[{"project": "Billing", "time_investment": "high", "priority_level": "high"}],
        strategic_recommendations=[{"action": "Lead design review", "priority": "medium"}],
        monthly_summary="Solid month.",
        full_analysis_json={"month": "summary"},
    )


def add_monthly(db, employee_id, year, month, full=True, **overrides):
    values = dict(
        employee_id=employee_id,
        year=year,
        month=month,
        period_start=date(year, month, 1),
        period_end=date(year, month, 28),
        analysis_date=FIXED_NOW,
    )
    if full:
        values.update(monthly_full_fields())
    values.update(overrides)
    analysis = MonthlyAnalysis(**values)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def quarterly_full_fields():
    rec = {"action": "Keep shipping", "priority": "high", "ownership": "employee"}
    behavior = {"rating": "meets", "evidence": "Observed in reviews"}
    return dict(
        monthly_analysis_ids=[1, 2, 3],
        organizational_impact="team",
        performance_trend="improving",
        task_completion_reliability="high",
        work_quality_consistency="high",
        performance_stability="medium",
        collaboration_effectiveness="high",
        stakeholder_count=4,
        risk_level="low",
        risk_trend="stable",
        learning_agility="high",
        autonomy_level="medium",
        development_focus="System design",
        credibility_rating="high",
        vision_data_alignment="high",
        adaptation_effectiveness="medium",
        strategic_alignment_json={
            "organizational_impact": "team",
            "key_initiatives": [{"initiative": "Billing v2", "alignment": "high", "outcomes": "Launched"}],
            "role_alignment": "strong",
            "role_fit_assessment": "Good fit",
        },
        achievement_themes_json=[{
            "theme": "Delivery",
            "related_achievements": ["Release 1.2"],
            "impact_score": 8,
            "impact_reason": "team",
            "vision_verification": "supported",
        }],
        performance_trajectory_json={
            "trend": "improving",
            "consistency": {
                "task_completion_reliability": "high",
                "work_quality_consistency": "high",
                "performance_stability": "medium",
            },
            "notable_shifts": [{"month": "February", "description": "Took ownership", "factors": "New project"}],
        },
        challenge_patterns_json={"recurring": ["Flaky CI"]},
        cross_functional_impact_json={
            "collaboration_effectiveness": "high",
            "stakeholder_impacts": [{
                "stakeholder": "Finance",
                "collaboration_type": "contributing_expertise",
                "impact": "Faster close",
                "evidence": "Automated report",
            }],
        },
        skill_development_json={
            "key_capabilities": [{"skill": "Python", "proficiency": "advanced", "growth": "improved"}],
            "learning_agility": "high",
            "autonomy_level": "medium",
            "development_focus": "System design",
        },
        behavioral_assessment_json={
            "ownership": behavior,
            "collaboration": behavior,
            "communication": behavior,
            "problem_solving": behavior,
            "quality_standards": behavior,
        },
        risk_assessment_json={
            "overall_risk_level": "low",
            "risk_trend": "stable",
            "key_risk_factors": ["single point of failure"],
            "mitigation_strategies": ["pairing"],
        },
        credibility_assessment_json={
            "rating": "high",
            "explanation": "Consistent",
            "vision_data_alignment": "high",
            "impact_on_evaluation": "None",
        },
        forward_planning_json={
            "keep_doing": [rec],
            "improve": [rec],
            "start": [rec],
            "stop": [rec],
            "support_needed": [rec],
        },
        quarterly_summary="Strong quarter.",
        full_analysis_json={"quarter": "summary"},
    )


def add_quarterly(db, employee_id, year, quarter, full=True, **overrides):
    start_month = (quarter - 1) * 3 + 1
    values = dict(
        employee_id=employee_id,
        year=year,
        quarter=quarter,
        period_start=date(year, start_month, 1),
        period_end=date(year, start_month + 2, 28),
        analysis_date=FIXED_NOW,
    )
    if full:
        values.update(quarterly_full_fields())
    values.update(overrides)
    analysis = QuarterlyAnalysis(**values)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


# --------------------------------------------------------------------------- background tasks

def add_task(db, **fields):
    values = dict(
        task_id=uuid.uuid4(),
        celery_task_id="celery-seeded",
        task_type="REPORT_ANALYSIS",
        status="pending",
        created_at=FIXED_NOW,
    )
    values.update(fields)
    task = BackgroundTask(**values)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# --------------------------------------------------------------------------- sync history

def add_sync(db, sync_type="employee_reports", status="completed", **fields):
    values = dict(
        sync_id=uuid.uuid4(),
        sync_type=sync_type,
        status=status,
        started_at=FIXED_NOW,
    )
    values.update(fields)
    sync = SyncHistory(**values)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync


def seed_sync_history(db):
    """Six history rows with distinct fixed start times (no 'partial' rows)."""
    base = datetime(2025, 1, 1, 8, 0, 0)
    specs = [
        ("employee_reports", "completed", False, 0, 10, 10),
        ("employee_reports", "failed", True, 1, 5, 0),
        ("vision_data", "completed", True, 2, 200, 190),
        ("job_descriptions", "completed", False, 3, 7, 7),
        ("supervisor_feedback", "failed", False, 4, 3, 1),
        ("vision_data", "completed", False, 5, 50, 50),
    ]
    rows = []
    for i, (sync_type, status, is_full, day, queried, synced) in enumerate(specs, start=1):
        started = base + timedelta(days=day)
        rows.append(add_sync(
            db,
            sync_type=sync_type,
            status=status,
            sync_id=fixed_uuid(100 + i),
            started_at=started,
            completed_at=started + timedelta(seconds=30 + i),
            last_sync_timestamp=started - timedelta(hours=1) if status == "completed" else None,
            records_queried=queried,
            records_synced=synced,
            error_count=queried - synced,
            sync_options={"is_full_sync": is_full},
        ))
    return rows


# --------------------------------------------------------------------------- CSV imports

def add_import_job(db, **fields):
    values = dict(
        job_id=uuid.uuid4(),
        filename="reports.csv",
        status="completed",
        csv_type="employee_report",
        submitted_at=FIXED_NOW,
        total_rows=0,
        processed_rows=0,
        successful_rows=0,
        error_count=0,
    )
    values.update(fields)
    job = CSVImportJob(**values)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def add_import_error(db, job_id, row_number, field_name="Name", message="bad value", row_data=None):
    error = ImportError(
        job_id=job_id,
        row_number=row_number,
        field_name=field_name,
        error_message=message,
        row_data=row_data if row_data is not None else {"row": row_number},
    )
    db.add(error)
    db.commit()
    db.refresh(error)
    return error


# --------------------------------------------------------------------------- visualization data

def seed_visualization_data(db):
    """Reports + analyses spread across days, ISO weeks, months, quarters and years.

    Dates are chosen to exercise period formatting edge cases:
    2024-12-30 is ISO week 1 of 2025 but labelled with its calendar year;
    2025-02-24 / 2025-03-03 are weeks 9 and 10 (string vs numeric sort).
    """
    alice, bob, carol = seed_employees(db)
    specs = [
        # employee, date, sentiment, risk, credibility, consistency, performance, impacts
        (alice, date(2024, 12, 30), 0.40, "high", "low", "low", "low", ["3 (Low)"]),
        (alice, date(2025, 1, 6), 0.60, "medium", "medium", "medium", "medium", ["6/10", "garbled"]),
        (alice, date(2025, 2, 24), 0.80, "low", "high", "high", "high", ["9"]),
        (alice, date(2025, 3, 3), 0.90, "low", "high", "high", "high", ["Impact rating: 7"]),
        (bob, date(2025, 1, 6), 0.20, "high", "low", "medium", "low", ["It had (5) impact"]),
        (bob, date(2025, 3, 3), 0.50, "Medium ", "weird", None, "medium", []),
        (carol, date(2025, 2, 24), 0.70, None, "high", "high", "high", ["10 (Huge)"]),
        (carol, date(2025, 4, 15), 0.65, "low", "medium", "medium", "high", ["4/5"]),
    ]
    for i, (emp, rdate, sentiment, risk, cred, cons, perf, impacts) in enumerate(specs, start=1):
        report = add_report(db, emp.id, rdate, text=f"report {i}", report_id=fixed_uuid(i))
        add_analysis(
            db,
            report,
            sentiment_score=sentiment,
            risk_level=risk,
            credibility_rating=cred,
            consistency_score=cons,
            performance_rating=perf,
            achievements_json=[{"description": f"a{i}-{j}", "impact": impact} for j, impact in enumerate(impacts)],
        )
    # A report without any analysis must never show up in the charts.
    add_report(db, alice.id, date(2025, 5, 5), text="unanalysed", report_id=fixed_uuid(99))
    return alice, bob, carol


# --------------------------------------------------------------------------- dumping DB state

def _plain(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def dump_rows(db, model, order_by=None):
    """All rows of ``model`` as plain dicts, freshly read from the database."""
    db.expire_all()
    mapper = inspect(model)
    query = db.query(model)
    if order_by is None:
        order_by = list(mapper.primary_key)
    elif not isinstance(order_by, (list, tuple)):
        order_by = [order_by]
    rows = query.order_by(*order_by).all()
    return [{attr.key: _plain(getattr(row, attr.key)) for attr in mapper.column_attrs} for row in rows]
