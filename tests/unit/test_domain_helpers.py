"""The pure period and scoring helpers in app.domain."""
from datetime import date

import pytest

from app.domain import periods, scoring


def test_month_helpers():
    assert periods.month_name(3) == "March"
    assert periods.month_name(13) == "Month 13"
    assert periods.month_name("May") == "Month May"
    assert [periods.months_in_quarter(q) for q in (1, 2, 3, 4)] == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]
    assert [periods.quarter_of_month(m) for m in range(1, 13)] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]


def test_report_week_start_is_seven_days_ending_on_the_report_date():
    assert periods.report_week_start(date(2025, 3, 7)) == date(2025, 3, 1)


@pytest.mark.parametrize("value, expected", [
    ("2024-03-01", date(2024, 3, 1)),
    ("03/01/2024", date(2024, 3, 1)),
    ("13/01/2024", date(2024, 1, 13)),
    ("13-01-2024", date(2024, 1, 13)),
    ("2024-03-01 00:00:00", date(2024, 3, 1)),
    ("2024-03-01T10:30", date(2024, 3, 1)),
])
def test_parse_period_date(value, expected):
    assert periods.parse_period_date(value) == expected


@pytest.mark.parametrize("value", ["2024/03/01", "31/31/2024", "yesterday", ""])
def test_parse_period_date_rejects(value):
    with pytest.raises(ValueError):
        periods.parse_period_date(value)


def test_rating_scales():
    assert [scoring.rating_score(v) for v in ("high", "Medium", " low ", "excellent", None)] == [3, 2, 1, None, None]
    assert [scoring.score_level(v) for v in (2.6, 2.5, 1.6, 1.5)] == ["high", "medium", "medium", "low"]
    assert [scoring.risk_score(v) for v in ("high", "medium", "low", None)] == [2, 1, 0, 0]
    assert [scoring.level_fraction(v) for v in ("HIGH", "medium", "low", "very high", 3)] == [0.8, 0.5, 0.2, None, None]


def test_sentiment_scales():
    assert [scoring.sentiment_score(v) for v in ("positive", "neutral", "negative", "mixed")] == [0.8, 0.5, 0.2, 0.0]
    assert [scoring.sentiment_label(v) for v in (0.2, 0.5, 0.8, None, "x")] == [
        "negative", "neutral", "positive", "neutral", "neutral"]


@pytest.mark.parametrize("value, expected", [
    (7, 7.0), (7.5, 7.5), (True, None), ("8 (good)", 8.0), ("9/10", 9.0), ("9", 9.0),
    ("a high impact (8) here", 8.0), ("Impact rating: 6", 6.0), ("high", None), ("", None), (None, None),
])
def test_parse_impact(value, expected):
    assert scoring.parse_impact(value) == expected


def test_average_impact_skips_achievements_without_a_readable_impact():
    achievements = [{"impact_score": 9}, {"impact_score": None, "impact": "6 (ok)"}, {"impact": "n/a"}, {}]
    assert scoring.average_impact(achievements) == 7.5
    assert scoring.average_impact([{}]) is None
