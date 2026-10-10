"""Golden master for StructuredPrompts.quarterly_analysis_prompt.

NOTE: the builder currently writes ``generated_quarterly_prompt.txt`` into the
current working directory and prints a debug line on every call, so every test
here runs inside a temporary directory.
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


def test_quarterly_weekly_matched_by_month_number_only():
    """Weeks from a different year but the same month number are attached too."""
    data = {
        "monthly_analyses": [{"month": 1, "month_name": "January"}],
        "weekly_analyses": [{"date": date(2025, 1, 11)}, {"date": date(2026, 1, 10)}],
    }
    prompt = build(data)
    assert "WEEKLY ANALYSES FOR JANUARY:" in prompt
    assert "WEEK 1 (2025-01-04 to 2025-01-11)" in prompt
    assert "WEEK 2 (2026-01-03 to 2026-01-10)" in prompt


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


def test_quarterly_progress_trend_month_must_be_int():
    with pytest.raises(TypeError):
        build({"metrics": {"monthly_progress_trends": [{"month": "January"}]}})


def test_quarterly_writes_debug_file_and_prints(_isolated_cwd, capsys, snapshot):
    """Side effect of every call: debug file in CWD (overwritten) + stdout line."""
    prompt = build(quarterly_minimal_data())
    written = (_isolated_cwd / "generated_quarterly_prompt.txt").read_text(encoding="utf-8")
    bar = "=" * 100
    assert written == (
        f"{bar}\nGENERATED QUARTERLY ANALYSIS PROMPT:\n{bar}\n\n{prompt}\n\n{bar}\n"
        f"Total prompt length: {len(prompt)} characters\n{bar}\n"
    )
    out = capsys.readouterr().out
    assert out == f"[DEBUG] Quarterly prompt saved to generated_quarterly_prompt.txt ({len(prompt)} characters)\n"
    snapshot("quarterly_minimal_length", {"chars": len(prompt)})
