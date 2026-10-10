"""Golden master for StructuredPrompts.employee_analysis_prompt (weekly analysis)."""
from datetime import date, datetime

import pytest

from app.prompts.structured_prompts import StructuredPrompts
from tests.golden.prompts.fixtures import (
    EMPLOYEE_INFO,
    IsoOnly,
    JD_TEXT,
    REPORT_TEXT,
    VISION_CURRENT,
    VISION_HISTORICAL,
    prompt_diff,
    weekly_full_kwargs,
    weekly_minimal_kwargs,
)

build = StructuredPrompts.employee_analysis_prompt


def minimal_prompt():
    return build(**weekly_minimal_kwargs())


def test_weekly_full(snapshot):
    snapshot("weekly_full", build(**weekly_full_kwargs()))


def test_weekly_minimal(snapshot):
    """Only report_text: no JD/vision/recent/similar sections, 'Unknown ...' employee fields."""
    snapshot("weekly_minimal", minimal_prompt())


def test_weekly_positional_call_matches_keyword_call():
    """LLMService.analyze_report passes everything positionally; order must stay the same."""
    kw = weekly_full_kwargs()
    positional = build(
        kw["report_text"], kw["formatted_vision_data"], kw["recent_reports"],
        kw["similar_reports"], kw["formatted_jd_data"], kw["employee_info"],
    )
    assert positional == build(**kw)


def test_weekly_empty_collections_equal_none():
    """[] / {} / "" behave exactly like None for every optional argument."""
    empty = build(REPORT_TEXT, "", [], [], "", {})
    assert empty == minimal_prompt()


def test_weekly_vision_current_only(snapshot):
    """No 'Historical Activity Data:' marker -> whole string is current data, historical part empty."""
    variant = build(REPORT_TEXT, formatted_vision_data=VISION_CURRENT)
    snapshot("weekly_vision_current_only.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_vision_historical_only(snapshot):
    """Marker at the very start -> current part is empty, but the vision section is still emitted."""
    variant = build(REPORT_TEXT, formatted_vision_data=VISION_HISTORICAL)
    snapshot("weekly_vision_historical_only.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_jd_only(snapshot):
    variant = build(REPORT_TEXT, formatted_jd_data=JD_TEXT)
    snapshot("weekly_jd_only.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_recent_report_date_kinds(snapshot):
    """date -> 'start to end' (6 days back); datetime -> same with times; non-date with isoformat -> bare value."""
    variant = build(
        REPORT_TEXT,
        recent_reports=[
            {"date": date(2026, 3, 7), "text": "Plain date week."},
            {"date": datetime(2026, 2, 28, 18, 30), "text": "Datetime week."},
            {"date": IsoOnly("2026-W08"), "text": "Iso-only week."},
        ],
    )
    snapshot("weekly_recent_date_kinds.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_similar_only(snapshot):
    variant = build(
        REPORT_TEXT,
        similar_reports=[
            {"date": date(2025, 11, 22), "text": "Similar A."},
            {"date": datetime(2025, 10, 4, 12, 0), "text": "Similar B."},
        ],
    )
    snapshot("weekly_similar_only.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_partial_employee_info(snapshot):
    """Missing keys fall back individually; explicit None values are rendered as 'None'."""
    variant = build(REPORT_TEXT, employee_info={"name": "Sana Qureshi", "wing": None})
    snapshot("weekly_partial_employee_info.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_weekly_string_dates_raise():
    """String dates are not accepted for recent/similar reports (they have no .isoformat)."""
    with pytest.raises(AttributeError):
        build(REPORT_TEXT, recent_reports=[{"date": "2026-03-07", "text": "x"}])
    with pytest.raises(AttributeError):
        build(REPORT_TEXT, similar_reports=[{"date": "2026-03-07", "text": "x"}])


def test_weekly_missing_report_keys_raise():
    with pytest.raises(KeyError):
        build(REPORT_TEXT, recent_reports=[{"text": "no date"}])
    with pytest.raises(KeyError):
        build(REPORT_TEXT, recent_reports=[{"date": date(2026, 3, 7)}])


def test_weekly_employee_info_is_not_mutated():
    info = dict(EMPLOYEE_INFO)
    build(REPORT_TEXT, employee_info=info)
    assert info == EMPLOYEE_INFO
