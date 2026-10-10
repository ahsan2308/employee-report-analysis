"""Characterization of app/services/db_service.py against the real test Postgres.

Each db_service function opens its own engine/session via get_database(); seeds
are committed through ``db_session`` first so those sessions can see them.
"""
from datetime import date

import pytest

from app.models.db_models import MonthlyAnalysis, QuarterlyAnalysis
from app.services import db_service
from tests.integration.services.seed import (
    dump_rows,
    make_analysis,
    make_employee,
    make_jd,
    make_monthly,
    make_quarterly,
    make_report,
    make_vision,
    normalize,
    uid,
)


# ------------------------------------------------------------ pure helpers

def test_month_and_quarter_date_ranges(snapshot):
    months = {f"{y}-{m}": db_service.get_month_date_range(y, m)
              for y, m in [(2024, 2), (2025, 2), (2025, 1), (2025, 4), (2025, 12)]}
    quarters = {f"{y}-Q{q}": db_service.get_quarter_date_range(y, q)
                for y in (2024, 2025) for q in (1, 2, 3, 4)}
    errors = {}
    for bad in (0, 5, -1):
        with pytest.raises(ValueError) as exc:
            db_service.get_quarter_date_range(2025, bad)
        errors[str(bad)] = str(exc.value)
    with pytest.raises(ValueError) as exc:
        db_service.get_month_date_range(2025, 13)
    errors["month 13"] = str(exc.value)
    snapshot("date_ranges", normalize({"months": months, "quarters": quarters, "errors": errors}))


# ------------------------------------------------------------ reports

@pytest.fixture
def reports_seed(db_session):
    make_employee(db_session, 1, "Alice")
    make_employee(db_session, 2, "Bob")
    make_report(db_session, 1, 1, date(2025, 1, 6))
    make_report(db_session, 2, 1, date(2025, 1, 13))
    make_report(db_session, 3, 1, date(2025, 1, 31))
    make_report(db_session, 4, 1, date(2025, 2, 1))
    make_report(db_session, 5, 1, date(2025, 2, 3), text="")  # empty text
    make_report(db_session, 6, 2, date(2025, 1, 20))
    make_report(db_session, 7, 1, date(2024, 1, 15))   # exactly 52 weeks before 2025-01-13
    make_report(db_session, 8, 1, date(2024, 1, 14))   # 52 weeks + 1 day before 2025-01-13
    make_report(db_session, 9, 1, date(2024, 12, 30))
    db_session.commit()
    return db_session


def _sorted_by_id(reports):
    return sorted(reports, key=lambda r: r["report_id"])


def test_get_complete_reports_by_ids(reports_seed, snapshot):
    cases = {
        "empty_list": db_service.get_complete_reports_by_ids([]),
        "duplicates_and_mixed_types": _sorted_by_id(db_service.get_complete_reports_by_ids(
            [str(uid(1)), str(uid(1)), uid(2), str(uid(6))])),
        "invalid_uuid_string_skipped": _sorted_by_id(db_service.get_complete_reports_by_ids(
            ["not-a-uuid", str(uid(3))])),
        "missing_id": db_service.get_complete_reports_by_ids([str(uid(999))]),
        "empty_text_excluded": db_service.get_complete_reports_by_ids([str(uid(5))]),
        "uppercase_string": db_service.get_complete_reports_by_ids([str(uid(4)).upper()]),
    }
    snapshot("get_complete_reports_by_ids", normalize(cases))


def test_get_complete_reports_by_ids_order_follows_set_iteration(reports_seed):
    """Output order is set-iteration order (hash dependent), not input/date order.

    Only the membership is stable; the snapshot above sorts it.
    """
    ids = [str(uid(n)) for n in (1, 2, 3, 4, 6)]
    result = db_service.get_complete_reports_by_ids(ids)
    assert [r["report_id"] for r in result] == list(set(ids))


def test_get_reports_for_vector_results(reports_seed, snapshot):
    results = [
        {"report_id": str(uid(2)), "chunk": 0},
        {"chunk": 1},  # no report_id -> ignored
        {"report_id": str(uid(2)), "chunk": 2},
        {"metadata": {"report_id": str(uid(3))}},  # nested report_id is NOT read
        {"report_id": str(uid(6))},
    ]
    snapshot("get_reports_for_vector_results", normalize({
        "results": _sorted_by_id(db_service.get_reports_for_vector_results(results)),
        "empty": db_service.get_reports_for_vector_results([]),
    }))


def test_get_recent_employee_reports(reports_seed, snapshot):
    cur = date(2025, 1, 13)
    cases = {
        "default": db_service.get_recent_employee_reports(1, cur),
        "limit_1": db_service.get_recent_employee_reports(1, cur, limit=1),
        "limit_0_means_unlimited": db_service.get_recent_employee_reports(1, cur, limit=0),
        "limit_negative_ignored": db_service.get_recent_employee_reports(1, cur, limit=-3),
        "exclude_existing": db_service.get_recent_employee_reports(1, cur, exclude_report_id=str(uid(1))),
        "exclude_invalid_uuid_ignored": db_service.get_recent_employee_reports(1, cur, exclude_report_id="bad"),
        "max_weeks_1": db_service.get_recent_employee_reports(1, cur, max_weeks=1),
        "max_weeks_0": db_service.get_recent_employee_reports(1, cur, max_weeks=0),
        "after_month_end": db_service.get_recent_employee_reports(1, date(2025, 2, 10)),
        "other_employee": db_service.get_recent_employee_reports(2, date(2025, 12, 31)),
        "unknown_employee": db_service.get_recent_employee_reports(99, cur),
    }
    snapshot("get_recent_employee_reports", normalize(cases))


def test_get_reports_for_month(reports_seed, snapshot):
    cases = {
        "2025-01_emp1": db_service.get_reports_for_month(1, 2025, 1),
        "2025-02_emp1_empty_text_dropped": db_service.get_reports_for_month(1, 2025, 2),
        "2024-12_emp1": db_service.get_reports_for_month(1, 2024, 12),
        "2025-01_emp2": db_service.get_reports_for_month(2, 2025, 1),
        "2025-03_none": db_service.get_reports_for_month(1, 2025, 3),
    }
    snapshot("get_reports_for_month", normalize(cases))


def test_get_reports_for_month_invalid_month_raises(reports_seed):
    # get_month_date_range is evaluated before the try block, so it propagates.
    with pytest.raises(ValueError):
        db_service.get_reports_for_month(1, 2025, 13)


# ------------------------------------------------------------ weekly analyses

@pytest.fixture
def analyses_seed(db_session):
    make_employee(db_session, 1, "Alice")
    make_employee(db_session, 2, "Bob")
    r1 = make_report(db_session, 1, 1, date(2025, 1, 31))
    r2 = make_report(db_session, 2, 1, date(2025, 2, 1))
    r3 = make_report(db_session, 3, 1, date(2025, 2, 28))
    make_report(db_session, 4, 1, date(2025, 2, 14))  # no analysis
    r5 = make_report(db_session, 5, 1, date(2025, 3, 31))
    r6 = make_report(db_session, 6, 1, date(2025, 4, 1))
    r7 = make_report(db_session, 7, 2, date(2025, 2, 10))
    make_analysis(db_session, r1, sentiment_score=0.1, risk_level="high",
                  achievements_json=[{"description": "x", "impact": "8"}],
                  challenges_json=[{"description": "c", "severity": "high"}],
                  topics=["t1"], action_items=["a1"],
                  credibility_rating="high", credibility_explanation="ok",
                  exaggeration_flags=["f"], consistency_score="medium",
                  performance_rating="high", performance_summary="good",
                  performance_strengths=["s"], performance_improvement_areas=["i"])
    make_analysis(db_session, r2, sentiment_score=0.2)
    make_analysis(db_session, r3, sentiment_score=0.3)
    make_analysis(db_session, r3, sentiment_score=0.35, risk_level="medium")  # 2nd analysis same report
    make_analysis(db_session, r5, sentiment_score=0.5)
    make_analysis(db_session, r6, sentiment_score=0.6)
    make_analysis(db_session, r7, sentiment_score=0.7)
    db_session.commit()
    return db_session


def _sort_analyses(rows):
    return sorted(rows, key=lambda r: (str(r["date"]), r["analysis_id"]))


def test_get_analyses_for_month(analyses_seed, snapshot):
    feb = db_service.get_analyses_for_month(1, 2025, 2)
    # Rows are ordered by report_date only; ties (two analyses of one report) are unordered.
    assert [str(r["date"]) for r in feb] == sorted(str(r["date"]) for r in feb)
    cases = {
        "jan": db_service.get_analyses_for_month(1, 2025, 1),
        "feb": _sort_analyses(feb),
        "mar": db_service.get_analyses_for_month(1, 2025, 3),
        "no_reports": db_service.get_analyses_for_month(1, 2025, 6),
        "unknown_employee": db_service.get_analyses_for_month(42, 2025, 2),
        "emp2_feb": db_service.get_analyses_for_month(2, 2025, 2),
    }
    snapshot("get_analyses_for_month", normalize(cases))


def test_get_weekly_analyses_for_quarter(analyses_seed, snapshot):
    q1 = db_service.get_weekly_analyses_for_quarter(1, 2025, 1)
    cases = {
        "q1": _sort_analyses(q1),
        "q2": db_service.get_weekly_analyses_for_quarter(1, 2025, 2),
        "q3_empty": db_service.get_weekly_analyses_for_quarter(1, 2025, 3),
        "emp2_q1": db_service.get_weekly_analyses_for_quarter(2, 2025, 1),
    }
    with pytest.raises(ValueError):
        db_service.get_weekly_analyses_for_quarter(1, 2025, 5)
    snapshot("get_weekly_analyses_for_quarter", normalize(cases))


# ------------------------------------------------------------ employee info

def test_get_employee_info(db_session, snapshot):
    make_employee(db_session, 7, "Grace", "Research", "Lead")
    db_session.commit()
    snapshot("get_employee_info", normalize({
        "found": db_service.get_employee_info(7),
        "missing": db_service.get_employee_info(8),
    }))


# ------------------------------------------------------------ vision data

@pytest.fixture
def vision_seed(db_session):
    make_employee(db_session, 1, "Alice")
    make_employee(db_session, 2, "Bob")
    # Weekly records around report date 2025-03-07 (Friday).
    make_vision(db_session, 1, 1, date(2025, 3, 3), date(2025, 3, 7), "Meetings", {"count": 3}, {"notes": "n1"})
    make_vision(db_session, 2, 1, date(2025, 3, 3), date(2025, 3, 7), "Tasks", {"done": 5})
    make_vision(db_session, 3, 1, date(2025, 2, 24), date(2025, 2, 28), "Meetings", {"count": 2})
    make_vision(db_session, 4, 1, date(2025, 2, 3), date(2025, 2, 7), "Meetings", {"count": 1})   # exactly 4 weeks
    make_vision(db_session, 5, 1, date(2025, 2, 2), date(2025, 2, 6), "Tasks", {"done": 1})       # 4 weeks + 1 day
    make_vision(db_session, 6, 1, date(2025, 3, 10), date(2025, 3, 14), "Meetings", {"count": 9})  # after
    make_vision(db_session, 7, 2, date(2025, 3, 3), date(2025, 3, 7), "Meetings", {"count": 4})
    # Month grouping: to_date spanning Jan/Feb boundary and a long record.
    make_vision(db_session, 8, 1, date(2025, 1, 27), date(2025, 1, 31), "Meetings", {"count": 7})
    make_vision(db_session, 9, 1, date(2025, 1, 1), date(2025, 1, 31), "Monthly", {"total": 30})
    make_vision(db_session, 10, 1, date(2025, 1, 6), date(2025, 1, 10), "Meetings", {"count": 6})
    # December 2025: 2025-12-31 is ISO week 1 (of 2026) -> sorts before week 49.
    make_vision(db_session, 11, 1, date(2025, 12, 1), date(2025, 12, 5), "Meetings", {"count": 11})
    make_vision(db_session, 12, 1, date(2025, 12, 29), date(2025, 12, 31), "Meetings", {"count": 12})
    # January 2027: 2027-01-01 is ISO week 53 (of 2026) -> sorts after week 1.
    make_vision(db_session, 13, 1, date(2026, 12, 28), date(2027, 1, 1), "Meetings", {"count": 13})
    make_vision(db_session, 14, 1, date(2027, 1, 4), date(2027, 1, 8), "Meetings", {"count": 14})
    # Same ISO week number in two different years would merge only within one month (n/a).
    db_session.commit()
    return db_session


def _sort_vision(result):
    for key in ("current_data", "previous_data"):
        if key in result:
            result[key] = sorted(result[key], key=lambda r: (r["to_date"], r["main_entity"]))
    return result


def test_get_employee_vision_data(vision_seed, snapshot):
    report_date = date(2025, 3, 7)
    raw = db_service.get_employee_vision_data(1, report_date)
    # previous_data is ordered by to_date desc.
    assert [r["to_date"] for r in raw["previous_data"]] == sorted(
        (r["to_date"] for r in raw["previous_data"]), reverse=True)
    cases = {
        "default_4_weeks": _sort_vision(raw),
        "1_week": _sort_vision(db_service.get_employee_vision_data(1, report_date, num_previous_weeks=1)),
        "0_weeks": _sort_vision(db_service.get_employee_vision_data(1, report_date, num_previous_weeks=0)),
        "no_exact_match_date": _sort_vision(db_service.get_employee_vision_data(1, date(2025, 3, 8))),
        "other_employee": _sort_vision(db_service.get_employee_vision_data(2, report_date)),
        "unknown_employee": db_service.get_employee_vision_data(99, report_date),
    }
    snapshot("get_employee_vision_data", normalize(cases))


def _sort_month(result):
    for week in result.get("weeks_data", []):
        week["activities"] = sorted(week["activities"], key=lambda a: (a["to_date"], a["main_entity"]))
    return result


def test_get_employee_vision_data_for_month(vision_seed, snapshot):
    cases = {
        "2025-01": _sort_month(db_service.get_employee_vision_data_for_month(1, 2025, 1)),
        "2025-02": _sort_month(db_service.get_employee_vision_data_for_month(1, 2025, 2)),
        "2025-03": _sort_month(db_service.get_employee_vision_data_for_month(1, 2025, 3)),
        "2025-04_empty": db_service.get_employee_vision_data_for_month(1, 2025, 4),
        "2025-12_iso_week_1_first": _sort_month(db_service.get_employee_vision_data_for_month(1, 2025, 12)),
        "2027-01_iso_week_53_last": _sort_month(db_service.get_employee_vision_data_for_month(1, 2027, 1)),
        "emp2_2025-03": _sort_month(db_service.get_employee_vision_data_for_month(2, 2025, 3)),
    }
    snapshot("get_employee_vision_data_for_month", normalize(cases))


def test_get_employee_vision_data_for_quarter(vision_seed, snapshot):
    def q(emp, year, quarter):
        result = db_service.get_employee_vision_data_for_quarter(emp, year, quarter)
        for month in result["months_data"]:
            _sort_month(month)
        return result

    cases = {
        "2025-Q1": q(1, 2025, 1),
        "2025-Q2_empty": q(1, 2025, 2),
        "2025-Q4": q(1, 2025, 4),
        "emp2_2025-Q1": q(2, 2025, 1),
    }
    with pytest.raises(ValueError):
        db_service.get_employee_vision_data_for_quarter(1, 2025, 0)
    snapshot("get_employee_vision_data_for_quarter", normalize(cases))


# ------------------------------------------------------------ monthly analyses

FULL_MONTHLY = {
    "employee_id": 1,
    "year": 2025,
    "month": 2,
    "period_start": date(2025, 2, 1),
    "period_end": date(2025, 2, 28),
    "weekly_report_ids": [str(uid(1)), str(uid(2))],
    "avg_sentiment_score": 0.42,
    "sentiment_trend": "improving",
    "performance_trend": "stable",
    "risk_level_pattern": "decreasing",
    "challenge_resolution_progress": "improved",
    "risk_level": "low",
    "risk_explanation": "fine",
    "significant_risks": ["r1"],
    "escalating_risks": [],
    "risk_mitigation_recommendations": ["m1"],
    "monthly_achievements": [{"achievement": "a", "impact": "high"}],
    "recurring_challenges": [{"challenge": "c", "severity": "low", "status": "open"}],
    "achievement_impact_avg": 7.5,
    "task_completion_reliability": "high",
    "work_quality_consistency": "medium",
    "performance_stability": "high",
    "consistency_notable_strengths": ["s"],
    "consistency_notable_weaknesses": ["w"],
    "complexity_of_tasks": "increased",
    "skill_development_evidence": "high",
    "confidence_level_change": "increased",
    "approach_to_challenges": "more proactive",
    "focus_areas": [{"project": "p", "priority": "high"}],
    "strategic_recommendations": [{"action": "x", "priority": "high"}],
    "monthly_summary": "Feb summary",
    "full_analysis_json": {"raw": True},
    "key_achievements": ["ignored on create"],
    "progress_assessment": "ignored on create",
    "unknown_field": "ignored",
}


@pytest.fixture
def employees(db_session):
    make_employee(db_session, 1, "Alice")
    make_employee(db_session, 2, "Bob")
    db_session.commit()
    return db_session


def _monthly_rows(database):
    return dump_rows(database, MonthlyAnalysis)


def test_store_monthly_analysis_create(employees, database, snapshot):
    returned = db_service.store_monthly_analysis(dict(FULL_MONTHLY))
    minimal = db_service.store_monthly_analysis(
        {"employee_id": 2, "year": 2025, "month": 3,
         "period_start": date(2025, 3, 1), "period_end": date(2025, 3, 31)})
    snapshot("store_monthly_analysis_create", normalize({
        "returned_ids": [returned, minimal],
        "rows": _monthly_rows(database),
    }))


def test_store_monthly_analysis_update_and_aliases(employees, database, snapshot):
    first = db_service.store_monthly_analysis(dict(FULL_MONTHLY))
    second = db_service.store_monthly_analysis({
        "employee_id": 1, "year": 2025, "month": 2,
        "avg_sentiment_score": 0.9,
        "key_achievements": [{"achievement": "via alias"}],   # -> monthly_achievements
        "progress_assessment": "declining",                    # -> performance_trend
        "monthly_summary": None,                               # explicit None overwrites
        "not_a_column": 1,
    })
    snapshot("store_monthly_analysis_update", normalize({
        "returned_ids": [first, second],
        "rows": _monthly_rows(database),
    }))


def test_store_monthly_analysis_update_overwrites_primary_key(employees, database, snapshot):
    """On update every key with a matching attribute is set, including analysis_id."""
    first = db_service.store_monthly_analysis(dict(FULL_MONTHLY))
    second = db_service.store_monthly_analysis(
        {"employee_id": 1, "year": 2025, "month": 2, "analysis_id": 77})
    snapshot("store_monthly_analysis_pk_overwrite", normalize({
        "returned_ids": [first, second],
        "row_ids": [row["analysis_id"] for row in _monthly_rows(database)],
    }))


def test_store_monthly_analysis_invalid_inputs(employees, database, snapshot):
    cases = {
        "missing_employee": db_service.store_monthly_analysis({"year": 2025, "month": 1}),
        "month_zero": db_service.store_monthly_analysis({"employee_id": 1, "year": 2025, "month": 0}),
        "missing_period_not_null": db_service.store_monthly_analysis(
            {"employee_id": 1, "year": 2025, "month": 1}),
        "unknown_employee_fk": db_service.store_monthly_analysis(
            {"employee_id": 99, "year": 2025, "month": 1,
             "period_start": date(2025, 1, 1), "period_end": date(2025, 1, 31)}),
    }
    snapshot("store_monthly_analysis_invalid", normalize({
        "returned": cases, "rows": _monthly_rows(database)}))


def test_get_monthly_analysis_by_params(employees, snapshot):
    make_monthly(employees, 1, 2025, 1,
                 weekly_report_ids=[str(uid(5))], significant_risks=["x"],
                 monthly_achievements=[{"a": 1}])
    employees.commit()
    snapshot("get_monthly_analysis_by_params", normalize({
        "found": db_service.get_monthly_analysis_by_params(1, 2025, 1),
        "other_month": db_service.get_monthly_analysis_by_params(1, 2025, 2),
        "other_employee": db_service.get_monthly_analysis_by_params(2, 2025, 1),
    }))


def test_get_monthly_analyses_for_quarter(employees, snapshot):
    make_monthly(employees, 1, 2025, 3, avg_sentiment_score=0.3)
    make_monthly(employees, 1, 2025, 1, avg_sentiment_score=0.1,
                 consistency_notable_strengths=["s"], escalating_risks=["e"])
    make_monthly(employees, 1, 2025, 2, avg_sentiment_score=0.2)
    make_monthly(employees, 1, 2025, 4, avg_sentiment_score=0.4)   # Q2
    make_monthly(employees, 1, 2024, 1, avg_sentiment_score=0.0)   # other year
    make_monthly(employees, 2, 2025, 2, avg_sentiment_score=0.9)   # other employee
    employees.commit()
    cases = {
        "q1": db_service.get_monthly_analyses_for_quarter(1, 2025, 1),
        "q2": db_service.get_monthly_analyses_for_quarter(1, 2025, 2),
        "q3_empty": db_service.get_monthly_analyses_for_quarter(1, 2025, 3),
        "emp2_q1": db_service.get_monthly_analyses_for_quarter(2, 2025, 1),
    }
    with pytest.raises(ValueError):
        db_service.get_monthly_analyses_for_quarter(1, 2025, 9)
    snapshot("get_monthly_analyses_for_quarter", normalize(cases))


# ------------------------------------------------------------ quarterly analyses

FULL_QUARTERLY = {
    "employee_id": 1,
    "year": 2025,
    "quarter": 1,
    "period_start": date(2025, 1, 1),
    "period_end": date(2025, 3, 31),
    "monthly_analysis_ids": [1, 2, 3],
    "organizational_impact": "team",
    "strategic_alignment_json": {"aligned": True},
    "performance_trend": "improving",
    "task_completion_reliability": "high",
    "work_quality_consistency": "high",
    "performance_stability": "medium",
    "performance_trajectory_json": {"shifts": []},
    "collaboration_effectiveness": "high",
    "stakeholder_count": 4,
    "cross_functional_impact_json": {"teams": ["a"]},
    "risk_level": "low",
    "risk_trend": "decreasing",
    "risk_assessment_json": {"factors": []},
    "learning_agility": "high",
    "autonomy_level": "medium",
    "development_focus": "leadership",
    "skill_development_json": {"skills": ["x"]},
    "credibility_rating": "high",
    "vision_data_alignment": "medium",
    "credibility_assessment_json": {"ok": 1},
    "adaptation_effectiveness": "high",
    "challenge_patterns_json": {"recurring": []},
    "achievement_themes_json": {"themes": ["t"]},
    "behavioral_assessment_json": {"b": 1},
    "forward_planning_json": {"continue": ["c"]},
    "quarterly_summary": "Q1 summary",
    "full_analysis_json": {"raw": "q"},
    "analysis_id": 555,  # ignored on create
}


def test_store_quarterly_analysis_create_update_invalid(employees, database, snapshot):
    created = db_service.store_quarterly_analysis(dict(FULL_QUARTERLY))
    rows_after_create = dump_rows(database, QuarterlyAnalysis)
    updated = db_service.store_quarterly_analysis({
        "employee_id": 1, "year": 2025, "quarter": 1,
        "analysis_id": 999,           # skipped on update
        "risk_level": "high",
        "quarterly_summary": None,
        "monthly_analysis_ids": [9],
        "bogus": "x",
    })
    invalid = {
        "missing_quarter": db_service.store_quarterly_analysis({"employee_id": 1, "year": 2025}),
        "quarter_zero": db_service.store_quarterly_analysis({"employee_id": 1, "year": 2025, "quarter": 0}),
        "missing_period": db_service.store_quarterly_analysis({"employee_id": 2, "year": 2025, "quarter": 2}),
        "unknown_employee": db_service.store_quarterly_analysis({
            "employee_id": 99, "year": 2025, "quarter": 2,
            "period_start": date(2025, 4, 1), "period_end": date(2025, 6, 30)}),
        # Out-of-range quarter is not validated on store.
        "quarter_7": db_service.store_quarterly_analysis({
            "employee_id": 2, "year": 2025, "quarter": 7,
            "period_start": date(2025, 1, 1), "period_end": date(2025, 1, 2)}),
    }
    snapshot("store_quarterly_analysis", normalize({
        "created": created,
        "rows_after_create": rows_after_create,
        "updated": updated,
        "invalid": invalid,
        "rows_final": dump_rows(database, QuarterlyAnalysis),
    }))


def test_get_quarterly_analysis_by_params(employees, snapshot):
    make_quarterly(employees, 1, 2025, 2, monthly_analysis_ids=[4, 5, 6],
                   stakeholder_count=3, forward_planning_json={"start": ["s"]})
    employees.commit()
    snapshot("get_quarterly_analysis_by_params", normalize({
        "found": db_service.get_quarterly_analysis_by_params(1, 2025, 2),
        "other_quarter": db_service.get_quarterly_analysis_by_params(1, 2025, 1),
        "other_employee": db_service.get_quarterly_analysis_by_params(2, 2025, 2),
    }))


# ------------------------------------------------------------ job descriptions

def test_get_employee_job_descriptions_for_period(employees, snapshot):
    s = employees
    make_jd(s, 1, "JD-ENDED-BEFORE", date(2024, 1, 1), date(2024, 12, 31), False)
    make_jd(s, 1, "JD-ENDS-ON-START", date(2024, 6, 1), date(2025, 1, 1), False)
    make_jd(s, 1, "JD-MID-PERIOD", date(2025, 1, 15), date(2025, 2, 15), False)
    make_jd(s, 1, "JD-CURRENT", date(2025, 2, 16), None, True)
    make_jd(s, 1, "JD-STARTS-ON-END", date(2025, 3, 31), None, True)
    make_jd(s, 1, "JD-AFTER", date(2025, 4, 1), None, True)
    make_jd(s, 1, "JD-SPANS", date(2023, 1, 1), date(2026, 1, 1), False)
    # Inconsistent rows the sync can produce:
    make_jd(s, 1, "JD-CURRENT-BUT-ENDED-EARLY", date(2023, 1, 1), date(2023, 6, 30), True)
    make_jd(s, 1, "JD-NOT-CURRENT-NO-END", date(2024, 1, 1), None, False)
    make_jd(s, 2, "JD-OTHER-EMP", date(2025, 1, 1), None, True)
    s.commit()

    q1 = (date(2025, 1, 1), date(2025, 3, 31))
    result = db_service.get_employee_job_descriptions_for_period(1, *q1)
    assert [jd["assigned_date"] for jd in result] == sorted(jd["assigned_date"] for jd in result)
    snapshot("get_employee_job_descriptions_for_period", normalize({
        "q1_2025": sorted(result, key=lambda jd: (str(jd["assigned_date"]), jd["jd_id"])),
        "single_day": sorted(
            db_service.get_employee_job_descriptions_for_period(1, date(2025, 2, 15), date(2025, 2, 15)),
            key=lambda jd: (str(jd["assigned_date"]), jd["jd_id"])),
        "inverted_period": sorted(
            db_service.get_employee_job_descriptions_for_period(1, date(2025, 3, 31), date(2025, 1, 1)),
            key=lambda jd: (str(jd["assigned_date"]), jd["jd_id"])),
        "unknown_employee": db_service.get_employee_job_descriptions_for_period(99, *q1),
    }))
