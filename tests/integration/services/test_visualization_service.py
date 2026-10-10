"""Characterization of app/services/visualization_service.py over a seeded weekly-analysis set.

Dataset: tests.integration.services.seed.seed_visualization_dataset (3 employees,
2 departments, Dec 2024 - Jun 2025, ISO week/month/quarter/year boundaries).
"""
from datetime import date, datetime

import pytest

from app.services import visualization_service as vs
from tests.integration.services.seed import (
    make_analysis,
    make_employee,
    make_report,
    normalize,
    seed_visualization_dataset,
)

INTERVALS = ("day", "week", "month", "quarter", "year")

RATING_TRENDS = {
    "risk": vs.get_risk_level_trends,
    "credibility": vs.get_credibility_trends,
    "consistency": vs.get_consistency_trends,
    "performance": vs.get_performance_trends,
    "impact": vs.get_impact_score_trends,
}


@pytest.fixture(autouse=True)
def empty_cache():
    vs._cache.clear()
    vs._cache_expiry.clear()
    yield
    vs._cache.clear()
    vs._cache_expiry.clear()


@pytest.fixture
def viz(db_session):
    seed_visualization_dataset(db_session)
    db_session.commit()
    return db_session


FILTERS = {
    "none": {},
    "employee_1": {"employee_id": 1},
    "employee_str_2": {"employee_id": "2"},
    "employee_invalid_ignored": {"employee_id": "abc"},
    "employee_0_falsy_ignored": {"employee_id": 0},
    "department_engineering": {"department": "Engineering"},
    "department_unknown": {"department": "Nope"},
    "date_range_q1": {"start_date": date(2025, 1, 1), "end_date": date(2025, 3, 31)},
    "date_strings": {"start_date": "2025-02-01T00:00:00", "end_date": "2025-03-03 23:59"},
    "date_unparseable_ignored": {"start_date": "01/02/2025"},
    "datetime_start": {"start_date": datetime(2025, 3, 3, 12, 0)},
    "combined": {"department": "Engineering", "employee_id": 1, "start_date": "2025-01-01"},
}


def _sentiment_view(result):
    """get_sentiment_trends has no ORDER BY: compare label/value pairs, not order."""
    dataset = result["datasets"][0]
    return {
        "pairs": sorted(zip(result["labels"], dataset["data"])),
        "label": dataset["label"],
        "metadata": dataset["metadata"],
        "n_labels": len(result["labels"]),
    }


def _heatmap_view(result):
    """Cell order follows unordered query rows; sort cells by (x, y)."""
    out = dict(result)
    out["cells"] = sorted(result["cells"], key=lambda c: (c["x"], c["y"]))
    return out


# ------------------------------------------------------------ sentiment

def test_get_sentiment_trends_intervals(viz, snapshot):
    out = {interval: _sentiment_view(vs.get_sentiment_trends(viz, interval=interval))
           for interval in INTERVALS}
    snapshot("sentiment_trends_intervals", normalize(out))


def test_get_sentiment_trends_filters(viz, snapshot):
    out = {name: _sentiment_view(vs.get_sentiment_trends(viz, interval="month", **kwargs))
           for name, kwargs in FILTERS.items()}
    snapshot("sentiment_trends_filters", normalize(out))


def test_get_sentiment_trends_empty(db_session, snapshot):
    snapshot("sentiment_trends_empty", normalize(vs.get_sentiment_trends(db_session)))


def test_get_sentiment_trends_period_with_only_null_scores_raises(db_session):
    """AVG over only-NULL sentiment yields None and round(None, 2) raises."""
    make_employee(db_session, 1, "Solo", "Ops", "x")
    make_analysis(db_session, make_report(db_session, 1, 1, date(2025, 5, 5)), sentiment_score=None)
    db_session.commit()
    with pytest.raises(TypeError):
        vs.get_sentiment_trends(db_session)


# ------------------------------------------------------------ rating / impact trends

@pytest.mark.parametrize("name", sorted(RATING_TRENDS))
def test_rating_trends_intervals(viz, snapshot, name):
    func = RATING_TRENDS[name]
    out = {interval: func(viz, interval=interval) for interval in INTERVALS}
    snapshot(f"{name}_trends_intervals", normalize(out))


@pytest.mark.parametrize("name", sorted(RATING_TRENDS))
def test_rating_trends_filters(viz, snapshot, name):
    func = RATING_TRENDS[name]
    out = {fname: func(viz, interval="month", **kwargs) for fname, kwargs in FILTERS.items()}
    snapshot(f"{name}_trends_filters", normalize(out))


@pytest.mark.parametrize("name", sorted(RATING_TRENDS))
def test_rating_trends_empty(db_session, snapshot, name):
    snapshot(f"{name}_trends_empty", normalize(RATING_TRENDS[name](db_session, interval="week")))


def test_impact_trends_week_labels_sorted_chronologically(viz):
    """'2025-W9' comes before '2025-W10' (they used to be sorted as text)."""
    labels = vs.get_impact_score_trends(viz, interval="week")["labels"]
    assert labels.index("2025-W9") < labels.index("2025-W10")


def test_week_label_uses_iso_year(viz):
    """2024-12-30 is in ISO week 2025-W1 (it used to be labelled '2024-W1')."""
    labels = vs.get_risk_level_trends(viz, interval="week")["labels"]
    assert labels[0] == "2025-W1"
    assert not any(label.startswith("2024-") for label in labels)


def test_extract_impact_score(snapshot):
    samples = ["8 (Good impact)", "9/10", "7", "6.5", "It has a high impact (6) on the team",
               "Impact rating: 5", "impact RATING:4.5", "huge", "", None, 9, " 7", "7 ", "10/10 (great)",
               "(3) first", "rated 8/10"]
    snapshot("extract_impact_score", [[repr(s), vs.extract_impact_score(s)] for s in samples])


# ------------------------------------------------------------ heatmaps

@pytest.mark.parametrize("heatmap", ["sentiment", "impact"])
def test_heatmaps(viz, snapshot, heatmap):
    func = vs.get_sentiment_heatmap if heatmap == "sentiment" else vs.get_impact_score_heatmap
    out = {}
    for dimension in ("department", "employee", "anything_else_means_employee"):
        for interval in INTERVALS:
            out[f"{dimension}/{interval}"] = _heatmap_view(func(viz, dimension=dimension, interval=interval))
    out["department/month/q1_dates"] = _heatmap_view(
        func(viz, dimension="department", interval="month",
             start_date="2025-01-01", end_date=date(2025, 3, 31)))
    snapshot(f"{heatmap}_heatmap", normalize(out))


@pytest.mark.parametrize("heatmap", ["sentiment", "impact"])
def test_heatmaps_empty(db_session, snapshot, heatmap):
    func = vs.get_sentiment_heatmap if heatmap == "sentiment" else vs.get_impact_score_heatmap
    snapshot(f"{heatmap}_heatmap_empty", normalize(func(db_session)))


def test_sentiment_heatmap_null_sentiment_raises(db_session):
    make_employee(db_session, 1, "Solo", "Ops", "x")
    make_analysis(db_session, make_report(db_session, 1, 1, date(2025, 5, 5)), sentiment_score=None)
    db_session.commit()
    with pytest.raises(TypeError):
        vs.get_sentiment_heatmap(db_session)


# ------------------------------------------------------------ multi-criteria

def test_get_multi_criteria_trends(viz, snapshot):
    out = {
        "all_month": vs.get_multi_criteria_trends(
            viz, ["sentiment", "risk", "credibility", "consistency", "performance", "impact"]),
        "risk_impact_unknown_week": vs.get_multi_criteria_trends(viz, ["impact", "bogus", "risk"], interval="week"),
        "duplicate_criteria_quarter": vs.get_multi_criteria_trends(viz, ["risk", "risk"], interval="quarter"),
        "employee_3_day": vs.get_multi_criteria_trends(viz, ["performance", "sentiment"], employee_id=3,
                                                      interval="day"),
        "department_finance_year": vs.get_multi_criteria_trends(viz, ["consistency"], department="Finance",
                                                                interval="year"),
        "empty_criteria": vs.get_multi_criteria_trends(viz, []),
        "only_unknown": vs.get_multi_criteria_trends(viz, ["nope"]),
    }
    snapshot("multi_criteria_trends", normalize(out))


def test_get_multi_criteria_trends_empty_db(db_session, snapshot):
    snapshot("multi_criteria_trends_empty", normalize(
        vs.get_multi_criteria_trends(db_session, ["risk", "sentiment", "impact"])))


# ------------------------------------------------------------ cache

def test_cache_behaviour(viz, snapshot):
    first = vs.get_risk_level_trends(viz, interval="month")
    # New data in a new month is invisible while the entry is fresh.
    make_employee(viz, 9, "Late", "Engineering", "x")
    make_analysis(viz, make_report(viz, 900, 9, date(2025, 9, 1)), risk_level="high")
    viz.commit()
    second = vs.get_risk_level_trends(viz, interval="month")
    hit_is_same_object = second is first

    # Callers get a copy: mutating it leaves the cached entry alone.
    second["labels"].append("MUTATED")
    third = vs.get_risk_level_trends(viz, interval="month")

    # Key is built from str() of the raw arguments: '2025-01-01' and date(2025, 1, 1) share one key.
    vs.get_risk_level_trends(viz, start_date="2025-01-01")
    vs.get_risk_level_trends(viz, start_date=date(2025, 1, 1))

    # Expire the entry -> recomputed and sees the new month.
    vs._cache_expiry["risk_level_trends_None_None_None_None_month"] = 0
    fourth = vs.get_risk_level_trends(viz, interval="month")

    # multi-criteria caches its own key AND each sub-call's key.
    vs.get_multi_criteria_trends(viz, ["risk", "sentiment"], interval="quarter")
    keys_after_multi = sorted(vs._cache)

    vs.clear_cache(prefix="risk_level")
    keys_after_prefix_clear = sorted(vs._cache)

    before_identity = vs._cache
    vs.clear_cache()
    rebinds_module_dict = vs._cache is not before_identity

    snapshot("cache_behaviour", normalize({
        "hit_is_same_object": hit_is_same_object,
        "first_labels_after_mutation": first["labels"],
        "third_labels": third["labels"],
        "fourth_after_expiry": fourth,
        "keys_after_multi": keys_after_multi,
        "keys_after_prefix_clear": keys_after_prefix_clear,
        "clear_all_rebinds_module_dict": rebinds_module_dict,
        "cache_after_clear": sorted(vs._cache),
    }))


def test_cache_ttl_zero_still_stores_but_is_immediately_stale(viz):
    first = vs.get_credibility_trends(viz, cache_ttl=0)
    assert "credibility_trends_None_None_None_None_month" in vs._cache
    second = vs.get_credibility_trends(viz, cache_ttl=0)
    assert second is not first and second == first
