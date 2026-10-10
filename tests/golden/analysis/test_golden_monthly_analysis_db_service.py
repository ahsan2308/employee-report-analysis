"""Golden-master tests for app/services/monthly_analysis_db_service.get_monthly_data_for_analysis.

Every db_service function is mocked where the module under test looks it up;
get_month_date_range (pure) and map_reports_to_jds (pure) run for real.
"""
from datetime import date

import pytest

from app.services import monthly_analysis_db_service as svc
from tests.golden.analysis.fixtures import EMPLOYEE, jd, report, weekly_analysis

MOD = "app.services.monthly_analysis_db_service"


def run(employee=EMPLOYEE, reports=(), analyses=(), jds=(), year=2025, month=1):
    """Call the service with mocked db_service functions; return result and recorded calls."""
    calls = []

    def record(name, value):
        def fake(*args, **kwargs):
            calls.append({"fn": name, "args": list(args), "kwargs": kwargs})
            return value() if callable(value) else value
        return fake

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(f"{MOD}.get_employee_info", record("get_employee_info", employee))
        mp.setattr(f"{MOD}.get_reports_for_month", record("get_reports_for_month", list(reports)))
        mp.setattr(f"{MOD}.get_analyses_for_month", record("get_analyses_for_month", list(analyses)))
        mp.setattr(f"{MOD}.get_employee_job_descriptions_for_period",
                   record("get_employee_job_descriptions_for_period", list(jds)))
        result = svc.get_monthly_data_for_analysis(42, year, month)
    finally:
        mp.undo()
    return {"result": result, "calls": calls}


JAN_REPORTS = [report(date(2025, 1, d)) for d in (5, 12, 19, 26)]
JAN_JD = jd("JD_1", "Analyst", date(2025, 1, 1), date(2025, 1, 31), assigned=date(2024, 6, 1))


def typical_analyses():
    return [
        weekly_analysis(date(2025, 1, 5), sentiment=0.4, risk="high", topics=["budget", "hiring"],
                        achievements=[{"title": "a1", "impact_score": 8}],
                        challenges=[{"title": "c1"}]),
        weekly_analysis(date(2025, 1, 12), sentiment=0.5, risk="medium", topics=["budget"],
                        achievements=[{"title": "a2", "impact": "6 (moderate)"}]),
        weekly_analysis(date(2025, 1, 19), sentiment=0.7, risk="low", topics=["hiring", "travel"],
                        achievements=[{"title": "a3", "impact_score": 7.5}, {"title": "a4", "impact": "9"}],
                        challenges=[{"title": "c2"}, {"title": "c3"}]),
        weekly_analysis(date(2025, 1, 26), sentiment=0.8, risk="medium", topics=["budget"]),
    ]


def test_typical_month(snapshot):
    snapshot("monthly_typical", run(reports=JAN_REPORTS, analyses=typical_analyses(), jds=[JAN_JD]))


def test_employee_not_found(snapshot):
    snapshot("monthly_employee_not_found", run(employee=None, reports=JAN_REPORTS,
                                               analyses=typical_analyses(), jds=[JAN_JD]))


def test_no_data_at_all(snapshot):
    snapshot("monthly_no_data", run(employee={"id": 42}))


def test_reports_without_analyses_and_jd_transition(snapshot):
    jds = [jd("JD_OLD", "Old", date(2025, 2, 1), date(2025, 2, 14)),
           jd("JD_NEW", "New", date(2025, 2, 15), date(2025, 2, 28))]
    reports = [report(date(2025, 2, d)) for d in (2, 9, 16, 23)]
    snapshot("monthly_reports_no_analyses_transition", run(reports=reports, jds=jds, month=2))


def test_analyses_without_reports_and_without_jds(snapshot):
    snapshot("monthly_analyses_no_reports_no_jds", run(analyses=typical_analyses()))


@pytest.mark.parametrize("name,scores", [
    ("declining", [0.9, 0.8, 0.4, 0.3]),
    ("improving_odd_count", [0.2, 0.5, 0.6]),
    ("stable_small_change", [0.5, 0.55, 0.6, 0.6]),
    ("boundary_plus_0_1", [0.5, 0.6]),
    ("boundary_minus_0_1", [0.6, 0.5]),
    ("single_score", [0.42]),
    ("with_none_scores", [None, 0.3, None, 0.9]),
    ("all_none", [None, None]),
    ("zero_scores", [0.0, 0.0, 1.0]),
])
def test_sentiment_average_and_trend(snapshot, name, scores):
    analyses = [weekly_analysis(date(2025, 3, 2 + 7 * i), sentiment=s) for i, s in enumerate(scores)]
    out = run(analyses=analyses, month=3)
    snapshot(f"monthly_sentiment_{name}", {
        key: out["result"]["metrics"][key] for key in ("avg_sentiment", "sentiment_trend", "report_count")
    })


def test_sentiment_trend_sorts_by_date(snapshot):
    analyses = [weekly_analysis(date(2025, 3, 23), sentiment=0.2),
                weekly_analysis(date(2025, 3, 2), sentiment=0.9),
                weekly_analysis(date(2025, 3, 16), sentiment=0.3),
                weekly_analysis(date(2025, 3, 9), sentiment=0.8)]
    snapshot("monthly_sentiment_unsorted_input", run(analyses=analyses, month=3)["result"]["metrics"])


def test_mixed_risk_levels_and_topics(snapshot):
    analyses = [
        weekly_analysis(date(2025, 4, 6), risk="high", topics=["a", "b", "a"]),
        weekly_analysis(date(2025, 4, 13), risk="HIGH", topics=None),
        weekly_analysis(date(2025, 4, 20), risk=None, topics=["b"]),
        {"date": date(2025, 4, 27), "sentiment_score": 0.5},  # no risk_level key -> "medium" default
        weekly_analysis(date(2025, 4, 27), risk="low", topics=["c"]),
    ]
    metrics = run(analyses=analyses, month=4)["result"]["metrics"]
    # risk_levels has a None key, which JSON cannot sort: keep insertion order with repr() keys.
    metrics["risk_levels"] = [[repr(k), v] for k, v in metrics["risk_levels"].items()]
    snapshot("monthly_mixed_risk_topics", metrics)


def test_achievement_impact_average_edge_cases(snapshot):
    achievements = [
        {"title": "score zero", "impact_score": 0},
        {"title": "score float", "impact_score": 9.25},
        {"title": "score none falls back to legacy", "impact_score": None, "impact": "4 (ok)"},
        {"title": "legacy plain", "impact": "10"},
        {"title": "legacy slash", "impact": "8/10"},
        {"title": "legacy leading space", "impact": " 7 (x)"},
        {"title": "legacy text", "impact": "high"},
        {"title": "legacy empty", "impact": ""},
        {"title": "legacy int not str", "impact": 7},
        {"title": "legacy float string", "impact": "7.5 (good)"},
        {"title": "nothing at all"},
    ]
    analyses = [weekly_analysis(date(2025, 5, 4), achievements=achievements)]
    snapshot("monthly_impact_edge_cases", run(analyses=analyses, month=5)["result"]["metrics"])


def test_achievement_impact_no_scorable(snapshot):
    analyses = [weekly_analysis(date(2025, 5, 4), achievements=[{"impact": "n/a"}, {"impact": ""}])]
    snapshot("monthly_impact_none_scorable", run(analyses=analyses, month=5)["result"]["metrics"])


def test_impact_score_as_string_aborts(snapshot):
    analyses = [weekly_analysis(date(2025, 5, 4), achievements=[{"impact_score": "8"}])]
    snapshot("monthly_impact_score_string", run(analyses=analyses, reports=[report(date(2025, 5, 4))],
                                                jds=[JAN_JD], month=5))


def test_achievements_none_aborts_partially(snapshot):
    analyses = [weekly_analysis(date(2025, 6, 1)), weekly_analysis(date(2025, 6, 8))]
    analyses[1]["achievements"] = None
    snapshot("monthly_achievements_none", run(analyses=analyses, reports=[report(date(2025, 6, 8))],
                                              jds=[JAN_JD], month=6))


def test_analyses_missing_dates_abort_partially(snapshot):
    analyses = [weekly_analysis(date(2025, 6, 1), sentiment=0.3), weekly_analysis(date(2025, 6, 8), sentiment=0.6)]
    for a in analyses:
        a["date"] = None
    snapshot("monthly_missing_analysis_dates", run(analyses=analyses, month=6))


def test_invalid_month(snapshot):
    snapshot("monthly_invalid_month_13", run(month=13))


def test_december_leap_february(snapshot):
    bounds = {}
    for year, month in ((2024, 2), (2023, 2), (2025, 12), (2026, 1)):
        out = run(year=year, month=month)
        jd_call = [c for c in out["calls"] if c["fn"] == "get_employee_job_descriptions_for_period"][0]
        bounds[f"{year}-{month:02d}"] = {
            "period": [out["result"]["period_start"], out["result"]["period_end"]],
            "jd_call_kwargs": jd_call["kwargs"],
        }
    snapshot("monthly_period_bounds", bounds)
