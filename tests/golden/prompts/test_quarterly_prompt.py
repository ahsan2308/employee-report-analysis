"""Golden master for StructuredPrompts.quarterly_analysis_prompt.

Every test runs inside an empty temporary directory, so a builder that writes
files into the working directory is caught.
"""
from datetime import date

import pytest

from app.prompts.structured_prompts import StructuredPrompts
from tests.golden.prompts.fixtures import (
    JD_TEXT,
    VISION_CURRENT,
    prompt_diff,
    quarterly_full_data,
    quarterly_minimal_data,
)

build = StructuredPrompts.quarterly_analysis_prompt


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def minimal_prompt():
    return build(quarterly_minimal_data())


def test_quarterly_full(snapshot):
    """Covers: 3 months (one with every sub-dict empty), weekly analyses matched by .month
    (date, datetime, object with isoformat but no subtraction, object with month only),
    weekly analyses dropped (string date, month with no monthly analysis, no date),
    sentiment float/str-number/non-number/None, all metric blocks populated, vision + JD."""
    snapshot("quarterly_full", build(quarterly_full_data()))


def test_quarterly_minimal(snapshot):
    """Empty dict: 'Quarter' label, every metric default, no monthly section, no vision/JD."""
    snapshot("quarterly_minimal", minimal_prompt())


def test_quarterly_label_variants(snapshot):
    labels = {}
    for name, extra in {
        "quarter_and_year": {"quarter": 2, "year": 2026},
        "quarter_only": {"quarter": 2},
        "year_only": {"year": 2026},
        "quarter_zero": {"quarter": 0, "year": 2026},
        "quarter_string": {"quarter": "3", "year": "2026"},
    }.items():
        prompt = build(extra)
        line = next(l for l in prompt.splitlines() if "Analysis Period:" in l)
        labels[name] = line
    snapshot("quarterly_label_variants", labels)


def test_quarterly_monthly_analysis_without_month_keys(snapshot):
    """Missing month_name/month -> 'Month N' label and month number i+1 used to match weeks."""
    data = {
        "monthly_analyses": [{}, {}],
        "weekly_analyses": [{"date": date(2026, 2, 7)}, {"date": date(2026, 1, 3), "sentiment_score": 0.9}],
    }
    snapshot("quarterly_month_defaults.diff_vs_minimal", prompt_diff(minimal_prompt(), build(data)))


def test_quarterly_weekly_matched_by_month_and_year():
    """Weeks are attached to the month with the same number and year; a week is the 7 days ending on its date."""
    data = {
        "monthly_analyses": [{"month": 1, "month_name": "January", "year": 2025}],
        "weekly_analyses": [{"date": date(2025, 1, 11)}, {"date": date(2026, 1, 10)}],
    }
    prompt = build(data)
    assert "WEEKLY ANALYSES FOR JANUARY:" in prompt
    assert "WEEK 1 (2025-01-05 to 2025-01-11)" in prompt
    assert "2026-01-10" not in prompt


def test_quarterly_weekly_matched_by_quarter_year_when_month_has_none():
    data = {
        "year": 2026,
        "monthly_analyses": [{"month": 1, "month_name": "January"}],
        "weekly_analyses": [{"date": date(2025, 1, 11)}, {"date": date(2026, 1, 10)}],
    }
    prompt = build(data)
    assert "WEEK 1 (2026-01-04 to 2026-01-10)" in prompt
    assert "2025-01-11" not in prompt


def test_quarterly_vision_only(snapshot):
    snapshot(
        "quarterly_vision_only.diff_vs_minimal",
        prompt_diff(minimal_prompt(), build({"formatted_vision_data": VISION_CURRENT})),
    )


def test_quarterly_jd_only(snapshot):
    snapshot(
        "quarterly_jd_only.diff_vs_minimal",
        prompt_diff(minimal_prompt(), build({"formatted_jd_data": JD_TEXT})),
    )


def test_quarterly_rating_distribution_requires_numbers():
    with pytest.raises(ValueError):
        build({"metrics": {"performance_rating_aggregation": {"rating_distribution": {"high": "60%"}}}})


def test_quarterly_progress_trend_month_not_a_number_is_labelled_as_given():
    prompt = build({"metrics": {"monthly_progress_trends": [{"month": "January"}]}})
    assert "Month January:" in prompt


def test_quarterly_has_no_side_effects(_isolated_cwd, capsys, snapshot):
    """Building a prompt writes no file and prints nothing (B15 fixed: it used to dump the prompt to the CWD)."""
    prompt = build(quarterly_minimal_data())
    assert list(_isolated_cwd.iterdir()) == []
    assert capsys.readouterr().out == ""
    snapshot("quarterly_minimal_length", {"chars": len(prompt)})
