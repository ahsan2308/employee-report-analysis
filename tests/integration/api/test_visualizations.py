"""Characterization of the /visualizations router.

The service keeps a 5-minute in-process cache keyed by the query parameters;
conftest clears it around every test (see test_results_are_cached_*).
"""
from datetime import date

import pytest

from tests.integration.api.conftest import body_of
from tests.integration.api.seed import add_analysis, add_report, fixed_uuid, seed_visualization_data
from tests.support.scrub import scrub

INTERVALS = ["day", "week", "month", "quarter", "year"]
TREND_ENDPOINTS = [
    "sentiment-trends",
    "impact-trends",
    "risk-trends",
    "credibility-trends",
    "consistency-trends",
    "performance-trends",
]
HEATMAP_ENDPOINTS = ["sentiment-heatmap", "impact-heatmap"]
ALL_CRITERIA = ["sentiment", "risk", "credibility", "consistency", "performance", "impact"]


def _resp(resp):
    return {"status": resp.status_code, "body": body_of(resp)}


def _slug(endpoint):
    return endpoint.replace("-", "_")


# --------------------------------------------------------------------------- empty database

@pytest.mark.parametrize("endpoint", TREND_ENDPOINTS + HEATMAP_ENDPOINTS)
def test_empty_db(api, snap, endpoint):
    snap(f"viz_{_slug(endpoint)}_empty", api.get(f"/visualizations/{endpoint}"))


def test_multi_criteria_empty_db(api, snap):
    resp = api.get("/visualizations/multi-criteria-trends", params={"criteria": ALL_CRITERIA})
    snap("viz_multi_criteria_trends_empty", resp)


# --------------------------------------------------------------------------- every interval, seeded

@pytest.mark.parametrize("interval", INTERVALS)
@pytest.mark.parametrize("endpoint", TREND_ENDPOINTS)
def test_trend_intervals(api, db_session, snap, endpoint, interval):
    seed_visualization_data(db_session)
    resp = api.get(f"/visualizations/{endpoint}", params={"interval": interval})
    snap(f"viz_{_slug(endpoint)}_{interval}", resp)


def test_trend_default_interval_is_month(api, db_session, snapshot):
    seed_visualization_data(db_session)
    results = {}
    for endpoint in TREND_ENDPOINTS:
        default = api.get(f"/visualizations/{endpoint}")
        monthly = api.get(f"/visualizations/{endpoint}", params={"interval": "month"})
        results[endpoint] = {"default": _resp(default), "same_as_month": default.json() == monthly.json()}
    snapshot("viz_trends_default_interval", scrub(results))


@pytest.mark.parametrize("interval", INTERVALS)
@pytest.mark.parametrize("dimension", ["department", "employee"])
@pytest.mark.parametrize("endpoint", HEATMAP_ENDPOINTS)
def test_heatmap_intervals(api, db_session, snap, endpoint, dimension, interval):
    seed_visualization_data(db_session)
    resp = api.get(f"/visualizations/{endpoint}", params={"interval": interval, "dimension": dimension})
    snap(f"viz_{_slug(endpoint)}_{dimension}_{interval}", resp)


@pytest.mark.parametrize("interval", INTERVALS)
def test_multi_criteria_intervals(api, db_session, snap, interval):
    seed_visualization_data(db_session)
    resp = api.get("/visualizations/multi-criteria-trends", params={"criteria": ALL_CRITERIA, "interval": interval})
    snap(f"viz_multi_criteria_trends_{interval}", resp)


# --------------------------------------------------------------------------- filters

FILTER_CASES = {
    "employee_1": {"employee_id": 1},
    "employee_2_quarter": {"employee_id": 2, "interval": "quarter"},
    "employee_unknown": {"employee_id": 999},
    "employee_zero_ignored": {"employee_id": 0},
    "department_engineering": {"department": "Engineering"},
    "department_finance_day": {"department": "Finance", "interval": "day"},
    "department_unknown": {"department": "Nope"},
    "start_date": {"start_date": "2025-02-01"},
    "end_date": {"end_date": "2025-01-31"},
    "date_range_week": {"start_date": "2025-01-01", "end_date": "2025-03-03", "interval": "week"},
    "inverted_range": {"start_date": "2025-04-01", "end_date": "2025-01-01"},
    "all_filters": {"employee_id": 1, "department": "Engineering", "start_date": "2025-01-01",
                    "end_date": "2025-12-31", "interval": "month"},
    "employee_department_mismatch": {"employee_id": 2, "department": "Engineering"},
}


@pytest.mark.parametrize("endpoint", TREND_ENDPOINTS)
def test_trend_filters(api, db_session, snapshot, endpoint):
    seed_visualization_data(db_session)
    results = {name: _resp(api.get(f"/visualizations/{endpoint}", params=params))
               for name, params in FILTER_CASES.items()}
    snapshot(f"viz_{_slug(endpoint)}_filters", scrub(results))


def test_multi_criteria_filters(api, db_session, snapshot):
    seed_visualization_data(db_session)
    results = {
        name: _resp(api.get("/visualizations/multi-criteria-trends", params={"criteria": ["risk", "impact"], **params}))
        for name, params in FILTER_CASES.items()
    }
    snapshot("viz_multi_criteria_trends_filters", scrub(results))


HEATMAP_FILTER_CASES = {
    "start_date": {"start_date": "2025-02-01"},
    "end_date": {"end_date": "2025-01-31", "dimension": "employee"},
    "range_quarter": {"start_date": "2025-01-01", "end_date": "2025-06-30", "interval": "quarter"},
    "empty_range": {"start_date": "2030-01-01"},
    # Heatmaps do not declare employee_id/department: they are silently ignored.
    "ignored_employee_and_department": {"employee_id": 1, "department": "Finance"},
}


@pytest.mark.parametrize("endpoint", HEATMAP_ENDPOINTS)
def test_heatmap_filters(api, db_session, snapshot, endpoint):
    seed_visualization_data(db_session)
    results = {name: _resp(api.get(f"/visualizations/{endpoint}", params=params))
               for name, params in HEATMAP_FILTER_CASES.items()}
    snapshot(f"viz_{_slug(endpoint)}_filters", scrub(results))


# --------------------------------------------------------------------------- invalid input

INVALID_CASES = {
    "interval_hour_400": {"interval": "hour"},
    "interval_uppercase_400": {"interval": "MONTH"},
    "start_date_bad_format_422": {"start_date": "01/02/2025"},
    "end_date_bad_value_422": {"end_date": "2025-02-30"},
    "employee_id_not_int_422": {"employee_id": "abc"},
}


@pytest.mark.parametrize("endpoint", TREND_ENDPOINTS)
def test_trend_invalid_input(api, snapshot, endpoint):
    results = {name: _resp(api.get(f"/visualizations/{endpoint}", params=params))
               for name, params in INVALID_CASES.items()}
    snapshot(f"viz_{_slug(endpoint)}_invalid", scrub(results))


@pytest.mark.parametrize("endpoint", HEATMAP_ENDPOINTS)
def test_heatmap_invalid_input(api, snapshot, endpoint):
    cases = {
        "interval_hour_400": {"interval": "hour"},
        "dimension_team_400": {"dimension": "team"},
        "interval_checked_before_dimension": {"interval": "hour", "dimension": "team"},
        "start_date_bad_format_422": {"start_date": "yesterday"},
    }
    results = {name: _resp(api.get(f"/visualizations/{endpoint}", params=params)) for name, params in cases.items()}
    snapshot(f"viz_{_slug(endpoint)}_invalid", scrub(results))


def test_multi_criteria_invalid_input(api, snapshot):
    url = "/visualizations/multi-criteria-trends"
    results = {
        "missing_criteria_422": _resp(api.get(url)),
        "unknown_criterion_400": _resp(api.get(url, params={"criteria": ["risk", "mood"]})),
        "interval_checked_first_400": _resp(api.get(url, params={"criteria": ["mood"], "interval": "hour"})),
        "empty_string_criterion_400": _resp(api.get(url, params={"criteria": [""]})),
        "bad_date_422": _resp(api.get(url, params={"criteria": ["risk"], "start_date": "x"})),
    }
    snapshot("viz_multi_criteria_trends_invalid", scrub(results))


def test_multi_criteria_order_and_duplicates(api, db_session, snapshot):
    seed_visualization_data(db_session)
    url = "/visualizations/multi-criteria-trends"
    results = {
        "impact_then_risk": _resp(api.get(url, params={"criteria": ["impact", "risk"]})),
        "risk_then_impact": _resp(api.get(url, params={"criteria": ["risk", "impact"]})),
        "duplicate_risk": _resp(api.get(url, params={"criteria": ["risk", "risk"]})),
        "single_performance": _resp(api.get(url, params={"criteria": ["performance"]})),
    }
    snapshot("viz_multi_criteria_trends_order", scrub(results))


# --------------------------------------------------------------------------- caching

@pytest.mark.parametrize("endpoint", ["risk-trends", "sentiment-heatmap"])
def test_results_are_cached_across_data_changes(api, db_session, snapshot, endpoint):
    alice, _, _ = seed_visualization_data(db_session)
    first = api.get(f"/visualizations/{endpoint}")
    report = add_report(db_session, alice.id, date(2026, 1, 5), report_id=fixed_uuid(500))
    add_analysis(db_session, report, risk_level="high", sentiment_score=0.1)
    second = api.get(f"/visualizations/{endpoint}")
    from app.services import visualization_service

    visualization_service.clear_cache()
    third = api.get(f"/visualizations/{endpoint}")
    snapshot(f"viz_{_slug(endpoint)}_cache", scrub({
        "first": _resp(first),
        "second_after_insert": _resp(second),
        "second_equals_first": second.json() == first.json(),
        "after_cache_clear": _resp(third),
    }))
