"""Golden-master tests for app/services/analysis/quarterly_context.get_quarterly_data_for_analysis.

Every db_service function is mocked where the module under test looks it up;
get_quarter_date_range (pure) and map_reports_to_jds (pure) run for real.
Anything printed to stdout is captured and snapshotted too (nothing, since B5 was fixed).
"""
from datetime import date

import pytest

from app.services.analysis import quarterly_context as svc
from tests.golden.analysis.fixtures import EMPLOYEE, jd, monthly_analysis, weekly_analysis

MOD = "app.services.analysis.quarterly_context"


def run(capsys, employee=EMPLOYEE, monthly=(), weekly=(), jds=(), year=2025, quarter=1):
    calls = []

    def record(name, value):
        def fake(*args, **kwargs):
            calls.append({"fn": name, "args": list(args), "kwargs": kwargs})
            return value
        return fake

    capsys.readouterr()
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(f"{MOD}.get_employee_info", record("get_employee_info", employee))
        mp.setattr(f"{MOD}.get_monthly_analyses_for_quarter",
                   record("get_monthly_analyses_for_quarter", list(monthly)))
        mp.setattr(f"{MOD}.get_weekly_analyses_for_quarter",
                   record("get_weekly_analyses_for_quarter", list(weekly)))
        mp.setattr(f"{MOD}.get_employee_job_descriptions_for_period",
                   record("get_employee_job_descriptions_for_period", list(jds)))
        result = svc.get_quarterly_data_for_analysis(42, year, quarter)
    finally:
        mp.undo()
    return {"result": result, "calls": calls, "stdout": capsys.readouterr().out}


def typical_monthly():
    return [
        monthly_analysis(1, "January", sentiment=0.4, report_ids=["r1", "r2", "r3", "r4"],
                         achievements=[{"a": 1}, {"a": 2}], challenges=[{"c": 1}], impact_avg=6.0,
                         risk="high",
                         progress={"performance_trend": "stable", "sentiment_trend": "declining",
                                   "risk_level_pattern": "increasing",
                                   "challenge_resolution_progress": "unchanged"},
                         consistency={"task_completion_reliability": "low",
                                      "work_quality_consistency": "medium",
                                      "performance_stability": "low"},
                         summary="January went slowly."),
        monthly_analysis(2, "February", sentiment=0.6, report_ids=["r5", "r6", "r7", "r8"],
                         achievements=[{"a": 3}], challenges=[], impact_avg=8.0, risk="medium",
                         progress={"performance_trend": "improving"},
                         consistency={"task_completion_reliability": "medium",
                                      "work_quality_consistency": "medium",
                                      "performance_stability": "medium"},
                         summary="February improved."),
        monthly_analysis(3, "March", sentiment=0.8, report_ids=["r9", "r10"],
                         achievements=[{"a": 4}, {"a": 5}, {"a": 6}], challenges=[{"c": 2}, {"c": 3}],
                         impact_avg=9.0, risk="low",
                         progress={"performance_trend": "improving", "challenge_resolution_progress": "improved"},
                         consistency={"task_completion_reliability": "high",
                                      "work_quality_consistency": "high",
                                      "performance_stability": "high"},
                         summary=""),
    ]


def typical_weekly():
    return [
        weekly_analysis(date(2025, 1, 12), topics=["budget", "hiring"], credibility_rating="low",
                        exaggeration_flags=["x"], performance_rating="low"),
        weekly_analysis(date(2025, 1, 26), topics=["budget"], credibility_rating="medium",
                        performance_rating="medium"),
        weekly_analysis(date(2025, 2, 9), topics=["hiring"], credibility_rating="high",
                        exaggeration_flags=["y", "z"], performance_rating="medium"),
        weekly_analysis(date(2025, 2, 23), topics=["travel"], credibility_rating="weird",
                        performance_rating="excellent"),
        weekly_analysis(date(2025, 3, 9), topics=["budget", "travel"], credibility_rating="high",
                        performance_rating="high"),
        weekly_analysis(date(2025, 3, 23), topics=None, credibility_rating=None, exaggeration_flags=None,
                        performance_rating="high"),
    ]


Q1_JDS = [jd("JD_A", "Analyst", date(2025, 1, 1), date(2025, 2, 14)),
          jd("JD_B", "Lead", date(2025, 2, 15), date(2025, 3, 31))]


def test_typical_quarter(snapshot, capsys):
    snapshot("quarterly_typical", run(capsys, monthly=typical_monthly(), weekly=typical_weekly(), jds=Q1_JDS))


def test_employee_not_found(snapshot, capsys):
    snapshot("quarterly_employee_not_found",
             run(capsys, employee=None, monthly=typical_monthly(), weekly=typical_weekly(), jds=Q1_JDS))


def test_no_data_at_all(snapshot, capsys):
    snapshot("quarterly_no_data", run(capsys, employee={"id": 42}))


def test_monthly_only(snapshot, capsys):
    snapshot("quarterly_monthly_only", run(capsys, monthly=typical_monthly(), quarter=1))


def test_weekly_only_with_jds(snapshot, capsys):
    snapshot("quarterly_weekly_only", run(capsys, weekly=typical_weekly(), jds=Q1_JDS))


def test_single_month_keeps_defaults(snapshot, capsys):
    snapshot("quarterly_single_month", run(capsys, monthly=typical_monthly()[:1]))


@pytest.mark.parametrize("name,levels", [
    ("all_high", ["high", "high", "high"]),
    ("all_low", ["low", "low", "low"]),
    ("declining_high_to_low", ["high", "medium", "low"]),
    ("improving_low_to_high", ["low", "medium", "high"]),
    ("unknown_values", ["excellent", None, "MEDIUM"]),
    ("two_months_medium", ["medium", "medium"]),
])
def test_consistency_and_risk_levels(snapshot, capsys, name, levels):
    monthly = []
    for i, level in enumerate(levels, start=1):
        consistency = {"task_completion_reliability": level, "work_quality_consistency": level,
                       "performance_stability": level}
        monthly.append(monthly_analysis(i, sentiment=None, risk=level, consistency=consistency))
    metrics = run(capsys, monthly=monthly)["result"]["metrics"]
    snapshot(f"quarterly_levels_{name}", {k: metrics[k] for k in (
        "task_reliability_trend", "quality_consistency_trend", "performance_stability",
        "risk_trend", "risk_levels", "sentiment_trend")})


@pytest.mark.parametrize("name,values", [
    ("sentiment_rising", [0.2, 0.5, 0.9]),
    ("sentiment_falling", [0.9, 0.5, 0.2]),
    ("sentiment_with_zero", [0.0, 0.5, 0.3]),
    ("sentiment_with_none", [None, 0.5, 0.4]),
    ("sentiment_negative", [-0.2, -0.5, -0.1]),
])
def test_sentiment_trend(snapshot, capsys, name, values):
    # Values are in chronological order (months 1, 2, 3).
    monthly = [monthly_analysis(1 + i, sentiment=v, report_ids=["x"] * (i + 1)) for i, v in enumerate(values)]
    metrics = run(capsys, monthly=monthly)["result"]["metrics"]
    snapshot(f"quarterly_{name}", {k: metrics[k] for k in ("avg_sentiment", "sentiment_trend")})


def test_progress_trend_aggregation(snapshot, capsys):
    cases = {
        "mixed": [{"performance_trend": "improving", "challenge_resolution_progress": "declined"},
                  {"performance_trend": "declining", "challenge_resolution_progress": "improved"}],
        "all_improving": [{"performance_trend": "improved"}, {"performance_trend": "increased"}],
        "all_declining": [{"performance_trend": "declining", "challenge_resolution_progress": "decreased"},
                          {"performance_trend": "declined", "challenge_resolution_progress": "declined"}],
        "mixed_and_unknown": [{"performance_trend": "mixed"}, {"performance_trend": "whatever"},
                              {"performance_trend": "improving"}],
        "one_empty_progress": [{"performance_trend": "improving"}, {}],
    }
    out = {}
    for name, progress_list in cases.items():
        monthly = [monthly_analysis(i + 1, progress=p) for i, p in enumerate(progress_list)]
        m = run(capsys, monthly=monthly)["result"]["metrics"]
        out[name] = {k: m.get(k, "<absent>") for k in (
            "performance_trend", "challenge_resolution_trend", "monthly_progress_trends")}
    snapshot("quarterly_progress_trends", out)


def test_impact_and_weighting_edge_cases(snapshot, capsys):
    cases = {
        "impact_avg_none_counts_in_denominator": [
            monthly_analysis(1, achievements=[{}, {}], impact_avg=None, report_ids=["a"]),
            monthly_analysis(2, achievements=[{}, {}], impact_avg=8.0, report_ids=["b"])],
        "no_achievements_impact_ignored": [
            monthly_analysis(1, achievements=[], impact_avg=10.0),
            monthly_analysis(2, achievements=[{}], impact_avg=3.333)],
        "impact_zero": [monthly_analysis(1, achievements=[{}], impact_avg=0.0)],
        "rounding": [monthly_analysis(1, achievements=[{}] * 3, impact_avg=7.0, report_ids=["a"] * 3),
                     monthly_analysis(2, achievements=[{}] * 1, impact_avg=8.0, report_ids=["b"] * 3)],
        "zero_reports_means_no_weighted_sentiment": [
            monthly_analysis(1, sentiment=0.9), monthly_analysis(2, sentiment=0.1)],
        "duplicate_month_numbers": [
            monthly_analysis(1, sentiment=0.9, report_ids=["a"]),
            monthly_analysis(1, sentiment=0.1, report_ids=["b", "c", "d"])],
        "missing_month_key": [
            {"avg_sentiment_score": 0.7, "weekly_report_ids": ["a", "b"], "monthly_achievements": [{}],
             "achievement_impact_avg": 5.0}],
    }
    out = {}
    for name, monthly in cases.items():
        m = run(capsys, monthly=monthly)["result"]["metrics"]
        out[name] = {k: m[k] for k in ("avg_sentiment", "achievement_impact_avg", "achievement_count",
                                        "challenge_count", "sentiment_trend", "monthly_summaries")}
    snapshot("quarterly_impact_weighting", out)


def test_weekly_metrics_edge_cases(snapshot, capsys):
    cases = {
        "rating_tie_first_wins": [
            weekly_analysis(date(2025, 1, 5), performance_rating="medium"),
            weekly_analysis(date(2025, 1, 12), performance_rating="high")],
        "two_ratings_no_trend": [
            weekly_analysis(date(2025, 1, 5), performance_rating="high"),
            weekly_analysis(date(2025, 2, 5), performance_rating="low")],
        "declining_ratings": [
            weekly_analysis(date(2025, 3, 5), performance_rating="low"),
            weekly_analysis(date(2025, 1, 5), performance_rating="high"),
            weekly_analysis(date(2025, 2, 5), performance_rating="medium")],
        "credibility_declining": [
            weekly_analysis(date(2025, 1, 5), credibility_rating="high"),
            weekly_analysis(date(2025, 2, 5), credibility_rating="medium"),
            weekly_analysis(date(2025, 3, 5), credibility_rating="low")],
        "credibility_one_month": [
            weekly_analysis(date(2025, 1, 5), credibility_rating="high"),
            weekly_analysis(date(2025, 1, 12), credibility_rating="low")],
        "credibility_unknown_only": [
            weekly_analysis(date(2025, 1, 5), credibility_rating="great"),
            weekly_analysis(date(2025, 2, 5), credibility_rating="ok")],
        "string_dates_and_missing_dates": [
            weekly_analysis(date(2025, 1, 5), performance_rating="high", topics=["t"]),
            dict(weekly_analysis(date(2025, 1, 5), performance_rating="low", topics=["t"]), date="2025-02-02"),
            dict(weekly_analysis(date(2025, 1, 5), performance_rating="low", topics=["t"]), date=None)],
        "many_topics": [weekly_analysis(date(2025, 1, 5), topics=[f"t{i % 13}" for i in range(30)])],
    }
    out = {}
    for name, weekly in cases.items():
        result = run(capsys, weekly=weekly, jds=[jd("J", "J", date(2025, 1, 1), date(2025, 3, 31))])["result"]
        m = result["metrics"]
        out[name] = {
            "weekly_report_count": m["weekly_report_count"],
            "weekly_credibility_data": m["weekly_credibility_data"],
            "weekly_performance_ratings": m["weekly_performance_ratings"],
            "performance_rating_aggregation": m["performance_rating_aggregation"],
            "recurring_topics": m["recurring_topics"],
            "detailed_topics": m["detailed_topics"],
            "jd_analysis_mapping": result.get("jd_analysis_mapping", "<absent>"),
        }
    snapshot("quarterly_weekly_metrics", out)


def test_weekly_report_id_none_aborts_jd_mapping(snapshot, capsys):
    weekly = [weekly_analysis(date(2025, 1, 12))]
    weekly[0]["report_id"] = None
    out = run(capsys, weekly=weekly, jds=Q1_JDS)
    snapshot("quarterly_report_id_none", {k: v for k, v in out.items() if k != "stdout"})


def test_none_collections_abort_partially(snapshot, capsys):
    cases = {
        "monthly_achievements_none": [dict(monthly_analysis(1, summary="s"), monthly_achievements=None)],
        "weekly_report_ids_none": [dict(monthly_analysis(1, summary="s"), weekly_report_ids=None)],
        "progress_trends_none": [dict(monthly_analysis(1), progress_trends=None)],
    }
    snapshot("quarterly_none_collections", {
        name: run(capsys, monthly=monthly, jds=Q1_JDS)["result"] for name, monthly in cases.items()})


@pytest.mark.parametrize("quarter", [0, 5])
def test_invalid_quarter(snapshot, capsys, quarter):
    snapshot(f"quarterly_invalid_quarter_{quarter}", run(capsys, quarter=quarter))


def test_period_bounds_and_jd_call(snapshot, capsys):
    out = {}
    for year, quarter in ((2024, 1), (2025, 2), (2025, 3), (2025, 4)):
        res = run(capsys, year=year, quarter=quarter)
        out[f"{year}-Q{quarter}"] = {
            "period": [res["result"]["period_start"], res["result"]["period_end"]],
            "calls": res["calls"],
        }
    snapshot("quarterly_period_bounds", out)
