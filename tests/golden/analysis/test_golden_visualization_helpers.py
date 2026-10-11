"""Golden-master tests for the DB-free helpers in app/services/visualization_service.py."""
from datetime import date, datetime

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories import visualizations as viz_repo
from app.services import visualization_service as vis


def outcome(fn, *args, **kwargs):
    try:
        return {"returned": fn(*args, **kwargs)}
    except Exception as exc:  # noqa: BLE001
        return {"raised": type(exc).__name__, "message": str(exc)}


def typed(value):
    """Keep the Python type visible in JSON snapshots (date vs datetime vs str)."""
    return {"type": type(value).__name__, "value": value}


def test_convert_rating_to_score(snapshot):
    inputs = [None, "low", "LOW", " Medium ", "high", "High\n", "", "very high", "0.8"]
    table = {repr(v): outcome(vis._convert_rating_to_score, v) for v in inputs}
    table["int_3"] = outcome(vis._convert_rating_to_score, 3)
    snapshot("convert_rating_to_score", table)


def test_parse_date(snapshot):
    inputs = [
        None, "", 0, date(2024, 2, 29), datetime(2025, 1, 5, 13, 45, 7),
        "2025-01-05", "2025-01-05T10:00:00", "2025-01-05 10:00:00", "2025-01-05T10:00:00+05:00",
        "05/01/2025", "2025-13-01", "2023-02-29", "not a date", 20250105, [2025, 1, 5],
    ]
    table = {}
    for value in inputs:
        res = outcome(vis._parse_date, value)
        if "returned" in res:
            res["returned"] = typed(res["returned"])
        table[f"{type(value).__name__}:{value!r}"] = res
    snapshot("parse_date", table)


DATES = [date(2024, 1, 1), date(2024, 2, 29), date(2024, 12, 30), date(2024, 12, 31), date(2025, 1, 1),
         date(2020, 12, 31), date(2021, 1, 3), date(2025, 3, 31), date(2025, 4, 1), date(2025, 9, 30),
         date(2025, 10, 1)]


def test_format_time_period(snapshot):
    table = {
        d.isoformat(): {iv: vis._format_time_period(d, iv) for iv in ("day", "week", "month", "quarter", "year", "bogus")}
        for d in DATES
    }
    table["datetime_input"] = {iv: vis._format_time_period(datetime(2025, 5, 17, 23, 59), iv)
                               for iv in ("day", "week", "month", "quarter", "year")}
    snapshot("format_time_period", table)


def test_sort_time_periods(snapshot):
    snapshot("sort_time_periods", {
        "empty": vis._sort_time_periods([], "day"),
        "none": vis._sort_time_periods(None, "day"),
        "day": vis._sort_time_periods(["2025-01-10", "2024-12-31", "2025-01-02", "2025-1-3"], "day"),
        "week": vis._sort_time_periods(["2025-W10", "2025-W2", "2024-W52", "2024-W1", "2025-W1"], "week"),
        "month": vis._sort_time_periods(["2025-10", "2025-02", "2024-12", "2025-1"], "month"),
        "quarter": vis._sort_time_periods(["2025-Q3", "2024-Q4", "2025-Q1"], "quarter"),
        "year": vis._sort_time_periods(["2025", "2019", "2024"], "year"),
        "unknown_interval_uses_year": vis._sort_time_periods(["2025", "2019"], "decade"),
        "malformed_week": outcome(vis._sort_time_periods, ["2025-10", "2025-W1"], "week"),
        "malformed_day": outcome(vis._sort_time_periods, ["2025-01", "2025-01-01"], "day"),
        "duplicates": vis._sort_time_periods(["2025-Q1", "2025-Q1", "2024-Q2"], "quarter"),
        "roundtrip_from_format": vis._sort_time_periods(
            [vis._format_time_period(d, "week") for d in DATES], "week"),
    })


def test_build_trend_response(snapshot):
    snapshot("build_trend_response", {
        "empty": vis._build_trend_response([], [], "Sentiment"),
        "single": vis._build_trend_response(["2025-01"], [0.5], "Sentiment"),
        "many": vis._build_trend_response(["a", "b", "c"], [0.2, 0.8, 0.333], "Risk"),
        "rounding": vis._build_trend_response(["a", "b"], [0.125, 0.0], "R"),
        "negative": vis._build_trend_response(["a", "b"], [-1, 2], "Neg"),
        "mismatched_lengths": vis._build_trend_response(["a"], [1, 2, 3], "M"),
    })


def test_extract_impact_score(snapshot):
    inputs = [
        None, "", 8, 8.5, ["8"],
        "8 (Good impact)", "8(Good)", "8.5 (ok)", "10/10", "9.5/10", "9", "9.0", "07",
        "It has a high impact (8) on the team", "Impact (7.25) noted", "Impact rating: 6",
        "impact RATING:  4.5 because", "Impact rating:7", "High", "-3", "-3 (bad)", " 8 (lead space)",
        "8 ", "8/", "score 8/10", "(8) first", "8 (a) and (9)", "1e3", "Impact rating: x (5)",
    ]
    snapshot("extract_impact_score", {repr(v): vis.extract_impact_score(v) for v in inputs})


class FrozenDatetime(datetime):
    now_value = datetime(2025, 6, 1, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.now_value


@pytest.fixture
def frozen_cache(monkeypatch):
    monkeypatch.setattr(vis, "datetime", FrozenDatetime)
    monkeypatch.setattr(vis, "_cache", {})
    monkeypatch.setattr(vis, "_cache_expiry", {})
    FrozenDatetime.now_value = datetime(2025, 6, 1, 12, 0, 0)
    yield FrozenDatetime


def test_cache_store_get_expire_clear(snapshot, frozen_cache):
    steps = {}
    vis._store_in_cache("sentiment:1", {"v": 1})
    vis._store_in_cache("sentiment:2", {"v": 2}, ttl=10)
    vis._store_in_cache("risk:1", {"v": 3}, ttl=0)
    steps["default_ttl"] = vis.DEFAULT_CACHE_SECONDS
    steps["expiry_offsets"] = {k: v - frozen_cache.now_value.timestamp() for k, v in sorted(vis._cache_expiry.items())}
    steps["get_fresh"] = [vis._get_from_cache(k) for k in ("sentiment:1", "sentiment:2", "risk:1", "missing")]
    frozen_cache.now_value = datetime(2025, 6, 1, 12, 0, 10)
    steps["get_at_plus_10s"] = [vis._get_from_cache(k) for k in ("sentiment:1", "sentiment:2")]
    frozen_cache.now_value = datetime(2025, 6, 1, 12, 5, 0)
    steps["get_at_plus_300s"] = vis._get_from_cache("sentiment:1")
    frozen_cache.now_value = datetime(2025, 6, 1, 12, 0, 0)
    vis.clear_cache("sentiment")
    steps["after_prefix_clear_keys"] = sorted(vis._cache)
    steps["after_prefix_clear_expiry_keys"] = sorted(vis._cache_expiry)
    vis.clear_cache("nomatch")
    steps["after_nomatch_clear_keys"] = sorted(vis._cache)
    vis.clear_cache()
    steps["after_full_clear"] = [vis._cache, vis._cache_expiry]
    vis.clear_cache("")  # empty prefix is falsy -> full clear
    steps["after_empty_prefix_clear"] = [vis._cache, vis._cache_expiry]
    snapshot("cache_lifecycle", steps)


class RecordingQuery:
    """Stand-in for a SQLAlchemy Query that records clauses as compiled SQL text."""

    def __init__(self):
        self.ops = []

    @staticmethod
    def _sql(clause):
        return str(clause.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

    def filter(self, *clauses):
        self.ops.append(["filter"] + [self._sql(c) for c in clauses])
        return self

    def group_by(self, *clauses):
        self.ops.append(["group_by"] + [self._sql(c) for c in clauses])
        return self

    def order_by(self, *clauses):
        self.ops.append(["order_by"] + [self._sql(c) for c in clauses])
        return self

    def with_entities(self, *clauses):
        self.ops.append(["with_entities"] + [self._sql(c) for c in clauses])
        return self

    def all(self):
        self.ops.append(["all"])
        return self


@pytest.mark.parametrize("name,args", [
    ("nothing", (None, None, None, None)),
    ("all", (7, "Ops", date(2025, 1, 1), date(2025, 3, 31))),
    ("employee_str_int", ("12", None, None, None)),
    ("employee_bad_str", ("abc", None, None, None)),
    ("employee_zero_ignored", (0, "", None, None)),
    ("dates_only", (None, None, "2025-01-01", date(2025, 12, 31))),
])
def test_apply_common_filters(snapshot, name, args):
    query = RecordingQuery()
    returned = viz_repo.apply_report_filters(query, *args)
    snapshot(f"apply_common_filters_{name}", {"same_query": returned is query, "ops": query.ops})


def test_group_by_time_interval(snapshot):
    table = {}
    for interval in ("day", "week", "month", "quarter", "year", "bogus"):
        query = RecordingQuery()
        viz_repo.average_sentiment_by_period(query, interval, "report_date")
        table[interval] = query.ops
    table["bad_column"] = outcome(viz_repo.average_sentiment_by_period, RecordingQuery(), "day", "no_such_column")
    snapshot("group_by_time_interval", table)
