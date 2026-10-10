"""Characterization of the three analysis Celery tasks end to end.

Outcome = BackgroundTask row + stored analysis rows + every call that left the
process (LLM HTTP client, embeddings, vector search) + the exact prompt text.
The real OllamaProvider and LLMService run; only ``ollama.Client`` is faked.
"""
import json
from datetime import date
from pathlib import Path
from unittest import mock

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from app.models.db_models import QuarterlyAnalysis
from app.models.task_models import BackgroundTask, TaskType
from app.tasks.analysis_tasks import (
    analyze_monthly_reports_task,
    analyze_quarterly_reports_task,
    analyze_report_task,
)
from tests.integration.pipelines.seed import (
    AUDIT_TS,
    CURRENT_REPORT_DATE,
    EMP_ID,
    FIXED_UUIDS,
    REPORT_IDS,
    add_task,
    dump_analysis_tables,
    seed_analysis_world,
    seed_monthly_analyses,
)
from tests.support.scrub import scrub

WEEKLY_JSON = json.dumps({
    "sentiment": "positive",
    "risk_level": "medium",
    "risk_explanation": "Late field reports could delay the monthly summary.",
    "topics": ["backlog", "archives"],
    "achievements": [{"description": "Closed the backlog", "impact": "8 (cleared 20 percent)"}],
    "challenges": [{"description": "Late field reports", "severity": "medium"}],
    "action_items": ["Escalate late reports to the wing head"],
    "credibility_assessment": {"rating": "high", "explanation": "Matches vision activity",
                               "exaggeration_flags": ["'closed the backlog' is broad"], "consistency_score": "high"},
    "performance_assessment": {"rating": "high", "summary": "Strong week", "key_strengths": ["Diligent"],
                               "improvement_areas": ["Delegation"]},
})

MONTHLY_JSON = json.dumps({
    "progress_trends": {"performance_trend": "improving", "sentiment_trend": "positive",
                        "risk_level_pattern": "decreasing", "challenge_resolution_progress": "improved"},
    "monthly_achievements": [{"description": "Backlog cleared", "impact_score": 9},
                             {"description": "Archive audit", "impact_score": "7"},
                             {"description": "Unscored item", "impact_score": "n/a"}],
    "recurring_challenges": [{"description": "Late field reports", "severity": "medium", "status": "ongoing"}],
    "consistency_assessment": {"task_completion_reliability": "high", "work_quality_consistency": "medium",
                               "performance_stability": "high", "notable_strengths": ["Reliable"],
                               "notable_weaknesses": ["Delegation"]},
    "growth_indicators": {"complexity_of_tasks": "increased", "skill_development_evidence": "high",
                          "confidence_level_change": "increased", "approach_to_challenges": "more proactive"},
    "focus_areas": [{"project": "Archive audit", "time_investment": "high", "priority_level": "high"}],
    "monthly_risk_assessment": {"overall_risk_level": "low", "risk_explanation": "Contained",
                                "significant_risks": ["Late reports"], "escalating_risks": [],
                                "risk_mitigation_recommendations": ["Weekly sync"]},
    "strategic_recommendations": [{"action": "Mentor juniors", "priority": "medium"}],
    "monthly_summary": "A productive month.",
})

QUARTERLY_JSON = json.dumps({
    "strategic_alignment": {"organizational_impact": "team",
                            "key_initiatives": [{"initiative": "Backlog", "alignment": "high", "outcomes": "Cleared"}]},
    "achievement_themes": [{"theme": "Throughput", "related_achievements": ["Backlog"], "impact": "8 (big)",
                            "business_outcome": "Faster cases", "vision_verified": True}],
    "performance_trajectory": {"trend": "improving",
                               "consistency": {"task_completion_reliability": "high",
                                               "work_quality_consistency": "high", "performance_stability": "medium"},
                               "notable_shifts": [{"month": "February", "description": "Ramp up", "factors": "New JD"}]},
    "challenge_patterns": {"recurring_challenges": [{"description": "Late reports", "type": "external",
                                                     "frequency": "intermittent", "resolution_status": "ongoing",
                                                     "systemic": True}],
                           "adaptation_effectiveness": "high"},
    "cross_functional_impact": {"collaboration_effectiveness": "high",
                                "stakeholder_impacts": [{"stakeholder": "Ops", "impact": "Faster", "evidence": "x"},
                                                        {"stakeholder": "HR", "impact": "Less", "evidence": "y"}]},
    "risk_assessment": {"overall_risk_level": "low", "risk_trend": "decreasing", "key_risk_factors": ["Late reports"],
                        "mitigation_strategies": ["Weekly sync"]},
    "skill_development": {"key_capabilities": [{"skill": "Auditing", "proficiency": "advanced", "growth": "improved"}],
                          "learning_agility": "high", "autonomy_level": "high", "development_focus": "Delegation"},
    "behavioral_assessment": {"ownership": {"rating": "exceeds", "evidence": "Took over backlog"}},
    "credibility_assessment": {"rating": "high", "explanation": "Consistent", "vision_data_alignment": "high",
                               "impact_on_evaluation": "None"},
    "forward_planning": {"keep_doing": ["Audits"], "improve": ["Delegation"], "start": ["Mentoring"],
                         "stop": ["Overtime"], "support_needed": ["Scanner"]},
    "quarterly_summary": "Strong quarter.",
})

SIMILAR_REPORT_DATE = date(2025, 2, 14)


def _outcome(result):
    if isinstance(result.result, BaseException):
        return {"state": result.state, "exception": repr(result.result)}
    return {"state": result.state, "return": result.result}


def _snapshot_run(snapshot, name, result, db_session, ext):
    snapshot(name, scrub({
        "outcome": _outcome(result),
        "db": dump_analysis_tables(db_session),
        "external_calls": ext.calls,
    }, keep_uuids=FIXED_UUIDS))
    for index, prompt in enumerate(ext.llm.prompts):
        snapshot(f"{name}__prompt{index}", scrub(prompt, keep_uuids=FIXED_UUIDS))


def _similar_hits():
    report_id = str(REPORT_IDS[SIMILAR_REPORT_DATE])
    base = {"report_id": report_id, "employee_id": EMP_ID, "report_date": SIMILAR_REPORT_DATE.isoformat(),
            "report_date_ts": 1739491200.0}
    return [
        {**base, "chunk_index": 0, "text": "Tasks Completed: Reviewed 14 case files", "score": 0.91, "id": "pt-1"},
        {**base, "chunk_index": 1, "text": "Impact: below threshold", "score": 0.12, "id": "pt-2"},
    ]


# --------------------------------------------------------------------------- weekly

WEEKLY_SCENARIOS = {
    "happy": dict(responses=[WEEKLY_JSON], seed={}),
    "no_vision_no_jds": dict(responses=[WEEKLY_JSON], seed={"vision": False, "jds": False}),
    "llm_empty": dict(responses=["", ""], seed={}),
    "llm_connection_error": dict(responses=[ConnectionError("ollama down"), ConnectionError("ollama down")], seed={}),
    "llm_invalid_json": dict(responses=["{not json", "Sorry, I cannot produce JSON today."], seed={}),
    "llm_text_fallback_recovers": dict(responses=["{not json", "Here you go:\n```json\n" + WEEKLY_JSON + "\n```"],
                                       seed={}),
}


@pytest.mark.parametrize("scenario", list(WEEKLY_SCENARIOS))
def test_weekly_analysis(scenario, db_session, ext, snapshot):
    spec = WEEKLY_SCENARIOS[scenario]
    seed_analysis_world(db_session, **spec["seed"])
    task_id = add_task(db_session, "weekly", TaskType.REPORT_ANALYSIS,
                       report_id=REPORT_IDS[CURRENT_REPORT_DATE], employee_id=EMP_ID)
    ext.vector_store.search_hits = _similar_hits()
    ext.llm.queue(*spec["responses"])

    result = analyze_report_task.apply(args=[str(task_id)], task_id="celery-weekly")

    _snapshot_run(snapshot, f"weekly__{scenario}", result, db_session, ext)


def test_weekly_analysis_task_row_missing(db_session, ext, snapshot):
    seed_analysis_world(db_session)
    result = analyze_report_task.apply(args=["00000000-0000-4000-9000-0000000000ff"], task_id="celery-weekly")
    _snapshot_run(snapshot, "weekly__task_row_missing", result, db_session, ext)


def test_weekly_analysis_task_id_not_a_uuid(db_session, ext, snapshot):
    result = analyze_report_task.apply(args=["not-a-uuid"], task_id="celery-weekly")
    _snapshot_run(snapshot, "weekly__task_id_not_a_uuid", result, db_session, ext)


def test_weekly_analysis_task_without_report(db_session, ext, snapshot):
    seed_analysis_world(db_session)
    task_id = add_task(db_session, "weekly", TaskType.REPORT_ANALYSIS, report_id=None, employee_id=EMP_ID)
    result = analyze_report_task.apply(args=[str(task_id)], task_id="celery-weekly")
    _snapshot_run(snapshot, "weekly__task_without_report", result, db_session, ext)


# --------------------------------------------------------------------------- monthly

MONTHLY_SCENARIOS = {
    "happy": dict(responses=[MONTHLY_JSON], seed={}, task={"year": 2025, "month": 3}),
    "no_vision_no_jds": dict(responses=[MONTHLY_JSON], seed={"vision": False, "jds": False},
                             task={"year": 2025, "month": 3}),
    "no_weekly_analyses": dict(responses=[MONTHLY_JSON], seed={"weekly": False}, task={"year": 2025, "month": 3}),
    "llm_empty": dict(responses=["", ""], seed={}, task={"year": 2025, "month": 3}),
    "llm_invalid_json": dict(responses=["{not json", "nope"], seed={}, task={"year": 2025, "month": 3}),
    "no_reports_in_month": dict(responses=[MONTHLY_JSON], seed={}, task={"year": 2025, "month": 6}),
    "analysis_already_exists": dict(responses=[MONTHLY_JSON], seed={}, task={"year": 2025, "month": 2}),
    "missing_month_param": dict(responses=[MONTHLY_JSON], seed={}, task={"year": 2025, "month": None}),
}


@pytest.mark.parametrize("scenario", list(MONTHLY_SCENARIOS))
def test_monthly_analysis(scenario, db_session, ext, snapshot):
    spec = MONTHLY_SCENARIOS[scenario]
    seed_analysis_world(db_session, **spec["seed"])
    task_id = add_task(db_session, "monthly", TaskType.MONTHLY_ANALYSIS, employee_id=EMP_ID, **spec["task"])
    ext.llm.queue(*spec["responses"])

    result = analyze_monthly_reports_task.apply(args=[str(task_id)], task_id="celery-monthly")

    _snapshot_run(snapshot, f"monthly__{scenario}", result, db_session, ext)


def test_monthly_analysis_wrong_task_type(db_session, ext, snapshot):
    seed_analysis_world(db_session)
    task_id = add_task(db_session, "monthly", TaskType.REPORT_ANALYSIS, employee_id=EMP_ID, year=2025, month=3)
    result = analyze_monthly_reports_task.apply(args=[str(task_id)], task_id="celery-monthly")
    _snapshot_run(snapshot, "monthly__wrong_task_type", result, db_session, ext)


def test_monthly_analysis_task_row_missing(db_session, ext, snapshot):
    result = analyze_monthly_reports_task.apply(args=["00000000-0000-4000-9000-0000000000ff"],
                                                task_id="celery-monthly")
    _snapshot_run(snapshot, "monthly__task_row_missing", result, db_session, ext)


# --------------------------------------------------------------------------- quarterly

QUARTERLY_SCENARIOS = {
    "happy": dict(responses=[QUARTERLY_JSON], seed={}, task={"year": 2025, "quarter": 1}),
    "no_vision_no_jds": dict(responses=[QUARTERLY_JSON], seed={"vision": False, "jds": False},
                             task={"year": 2025, "quarter": 1}),
    "llm_empty": dict(responses=["", ""], seed={}, task={"year": 2025, "quarter": 1}),
    "llm_invalid_json": dict(responses=["{not json", "nope"], seed={}, task={"year": 2025, "quarter": 1}),
    "no_monthly_analyses": dict(responses=[QUARTERLY_JSON], seed={}, task={"year": 2025, "quarter": 2}),
    "missing_quarter_param": dict(responses=[QUARTERLY_JSON], seed={}, task={"year": 2025, "quarter": None}),
}


@pytest.mark.parametrize("scenario", list(QUARTERLY_SCENARIOS))
def test_quarterly_analysis(scenario, db_session, ext, snapshot):
    spec = QUARTERLY_SCENARIOS[scenario]
    seed_analysis_world(db_session, **spec["seed"])
    seed_monthly_analyses(db_session, months=(3,))
    task_id = add_task(db_session, "quarterly", TaskType.QUARTERLY_ANALYSIS, employee_id=EMP_ID, **spec["task"])
    ext.llm.queue(*spec["responses"])

    result = analyze_quarterly_reports_task.apply(args=[str(task_id)], task_id="celery-quarterly")

    _snapshot_run(snapshot, f"quarterly__{scenario}", result, db_session, ext)
    # The run leaves nothing in the working directory (B15 fixed: the prompt used to be dumped there).
    assert list(Path.cwd().iterdir()) == []


def test_quarterly_analysis_already_exists(db_session, ext, snapshot):
    seed_analysis_world(db_session)
    db_session.add(QuarterlyAnalysis(employee_id=EMP_ID, year=2025, quarter=1, period_start=date(2025, 1, 1),
                                     period_end=date(2025, 3, 31), quarterly_summary="Existing",
                                     full_analysis_json={"existing": True}, analysis_date=AUDIT_TS))
    db_session.commit()
    task_id = add_task(db_session, "quarterly", TaskType.QUARTERLY_ANALYSIS, employee_id=EMP_ID, year=2025, quarter=1)
    result = analyze_quarterly_reports_task.apply(args=[str(task_id)], task_id="celery-quarterly")
    _snapshot_run(snapshot, "quarterly__analysis_already_exists", result, db_session, ext)


def test_quarterly_analysis_wrong_task_type(db_session, ext, snapshot):
    seed_analysis_world(db_session)
    task_id = add_task(db_session, "quarterly", TaskType.MONTHLY_ANALYSIS, employee_id=EMP_ID, year=2025, quarter=1)
    result = analyze_quarterly_reports_task.apply(args=[str(task_id)], task_id="celery-quarterly")
    _snapshot_run(snapshot, "quarterly__wrong_task_type", result, db_session, ext)


# --------------------------------------------------------------------------- time limits

@pytest.mark.parametrize("kind, task, task_type, fields, first_lookup", [
    ("weekly", analyze_report_task, TaskType.REPORT_ANALYSIS,
     {"report_id": REPORT_IDS[CURRENT_REPORT_DATE], "employee_id": EMP_ID}, "get_recent_employee_reports"),
    ("monthly", analyze_monthly_reports_task, TaskType.MONTHLY_ANALYSIS,
     {"employee_id": EMP_ID, "year": 2025, "month": 3}, "get_monthly_analysis_by_params"),
    ("quarterly", analyze_quarterly_reports_task, TaskType.QUARTERLY_ANALYSIS,
     {"employee_id": EMP_ID, "year": 2025, "quarter": 1}, "get_quarterly_analysis_by_params"),
])
def test_soft_time_limit_marks_task_failed(db_session, ext, kind, task, task_type, fields, first_lookup):
    """B11: the soft limit fires inside the task, which records the failure instead of staying RUNNING."""
    seed_analysis_world(db_session)
    task_id = add_task(db_session, kind, task_type, **fields)
    with mock.patch(f"app.tasks.analysis_tasks.{first_lookup}", side_effect=SoftTimeLimitExceeded()):
        result = task.apply(args=[str(task_id)], task_id=f"celery-{kind}")
    assert result.state == "FAILURE"
    db_session.expire_all()
    row = db_session.get(BackgroundTask, task_id)
    assert (row.status, row.error_message) == ("failed", "Analysis exceeded the time limit")
    assert row.completed_at is not None
