"""Golden master for StructuredPrompts.monthly_analysis_prompt."""
import pytest

from app.prompts.structured_prompts import StructuredPrompts
from tests.golden.prompts.fixtures import (
    JD_TEXT,
    VISION_CURRENT,
    monthly_full_data,
    monthly_minimal_data,
    prompt_diff,
)

build = StructuredPrompts.monthly_analysis_prompt


def minimal_prompt():
    return build(monthly_minimal_data())


def test_monthly_full(snapshot):
    """Covers: date/str/missing/datetime report dates, sentiment <, =, > 0.5, vision
    supported/contradicted/'none'/missing, empty and None lists, exaggeration flags
    rendered as a Python list repr, risk_levels/recurring_topics present, vision + JD present."""
    snapshot("monthly_full", build(monthly_full_data()))


def test_monthly_minimal(snapshot):
    """Only month/year: every metric default, 'None to None' period, no vision/JD section."""
    snapshot("monthly_minimal", minimal_prompt())


@pytest.mark.parametrize("month", [1, 12])
def test_monthly_month_names_in_range(month):
    prompt = build({"month": month, "year": 2026})
    name = {1: "January", 12: "December"}[month]
    assert f"({name} 2026)" in prompt


def test_monthly_month_out_of_range(snapshot):
    variant = build({"month": 13, "year": 2026})
    snapshot("monthly_month_13.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))
    assert "(Month 0 2026)" in build({"month": 0, "year": 2026})


def test_monthly_month_missing_raises():
    """month is effectively required: None reaches `1 <= month`."""
    with pytest.raises(TypeError):
        build({})


def test_monthly_analysis_with_all_defaults(snapshot):
    """An analysis dict with no keys, plus achievement/challenge dicts with no keys."""
    data = monthly_minimal_data()
    data["analyses"] = [{"achievements": [{}], "challenges": [{}]}, {}]
    data["reports"] = [{}]
    variant = build(data)
    snapshot("monthly_analysis_defaults.diff_vs_minimal", prompt_diff(minimal_prompt(), variant))


def test_monthly_sentiment_none_raises():
    """An explicit None sentiment_score is not defaulted (only a missing key is)."""
    data = monthly_minimal_data()
    data["analyses"] = [{"sentiment_score": None}]
    with pytest.raises(TypeError):
        build(data)


def test_monthly_vision_only(snapshot):
    data = monthly_minimal_data()
    data["formatted_vision_data"] = VISION_CURRENT
    snapshot("monthly_vision_only.diff_vs_minimal", prompt_diff(minimal_prompt(), build(data)))


def test_monthly_jd_only(snapshot):
    data = monthly_minimal_data()
    data["formatted_jd_data"] = JD_TEXT
    snapshot("monthly_jd_only.diff_vs_minimal", prompt_diff(minimal_prompt(), build(data)))


def test_monthly_input_not_mutated():
    data = monthly_full_data()
    before = repr(data)
    build(data)
    assert repr(data) == before
