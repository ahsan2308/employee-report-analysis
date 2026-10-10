"""Synthetic inputs for the LLM prompt-contract golden tests.

Every builder returns a fresh object so tests can mutate freely. The data is
realistic in shape (it mirrors what app/tasks/analysis_tasks.py and
app/services/additional_services.py pass in) but entirely invented.
"""
import difflib
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------

def prompt_diff(base: str, variant: str, base_name: str = "base", variant_name: str = "variant") -> str:
    """Unified diff of two prompts. Given a locked base, the diff locks the variant byte-for-byte."""
    return "".join(
        difflib.unified_diff(
            base.splitlines(keepends=True),
            variant.splitlines(keepends=True),
            fromfile=base_name,
            tofile=variant_name,
            n=2,
        )
    )


class IsoOnly:
    """Date-like value that is NOT a ``datetime.date`` but has ``isoformat()``."""

    def __init__(self, text: str):
        self.text = text

    def isoformat(self) -> str:
        return self.text


class IsoMonth:
    """Has ``month`` and ``isoformat()`` but does not support subtraction."""

    def __init__(self, month: int, text: str):
        self.month = month
        self.text = text

    def isoformat(self) -> str:
        return self.text

    def __str__(self) -> str:
        return f"IsoMonth<{self.text}>"


class MonthOnly:
    """Has ``month`` but no ``isoformat()``."""

    def __init__(self, month: int, label: str):
        self.month = month
        self.label = label

    def __str__(self) -> str:
        return f"MonthOnly<{self.label}>"


# --------------------------------------------------------------------------
# Shared text blocks
# --------------------------------------------------------------------------

EMPLOYEE_INFO = {
    "name": "Sana Qureshi",
    "position": "Assistant Director (Analysis)",
    "wing": "Analysis Wing / Section B / DHQ North",
}

REPORT_TEXT = (
    "Accomplishments:\n"
    "1. Finalised the quarterly threat-assessment brief and presented it to the Wing Director.\n"
    "2. Cross-referenced 42 field reports against the case registry; resolved 9 discrepancies.\n"
    "Challenges:\n"
    "- Registry access was down for two days, delaying validation.\n"
    "Next week:\n"
    "- Draft the provincial liaison summary.\n"
    "Confidence level: 2"
)

VISION_CURRENT = (
    "\nCurrent Report Period Activity Data:\n"
    "\n- Time Period: 2026-03-08 to 2026-03-14\n"
    "  Main Activity: Report Processing\n"
    "  Details:\n"
    "    - Number of Reports Reviewed: 42 (field reports reviewed)\n"
    "      ---> title: Field report 17, status: validated\n"
)

VISION_HISTORICAL = (
    "\nHistorical Activity Data:\n"
    "\n- Time Period: 2026-03-01 to 2026-03-07\n"
    "  Main Activity: Report Processing\n"
    "  Details:\n"
    "    - Number of Reports Reviewed: 15 (field reports reviewed)\n"
)

JD_TEXT = (
    "Primary Role: Assistant Director (Analysis) (effective 2025-07-01)\n"
    "Key Responsibilities:\n"
    "- Produce analytical products for Wing leadership\n"
    "- Validate field reporting against registries\n"
    "Additional Charge: Liaison Officer (effective 2026-01-15)\n"
)


# --------------------------------------------------------------------------
# Weekly (employee_analysis_prompt)
# --------------------------------------------------------------------------

def weekly_full_kwargs() -> Dict[str, Any]:
    return {
        "report_text": REPORT_TEXT,
        "formatted_vision_data": VISION_CURRENT + VISION_HISTORICAL,
        "recent_reports": [
            {"date": date(2026, 3, 7), "text": "Reviewed 15 field reports. Started the threat-assessment draft."},
            {"date": date(2026, 2, 28), "text": "Attended training on registry tooling. Confidence level: 3"},
        ],
        "similar_reports": [
            {"date": date(2025, 11, 22), "text": "Presented the monthly brief to Section Head."},
        ],
        "formatted_jd_data": JD_TEXT,
        "employee_info": dict(EMPLOYEE_INFO),
    }


def weekly_minimal_kwargs() -> Dict[str, Any]:
    return {"report_text": REPORT_TEXT}


# --------------------------------------------------------------------------
# Monthly (monthly_analysis_prompt)
# --------------------------------------------------------------------------

def _weekly_analysis(day: date, sentiment: Any, **overrides) -> Dict[str, Any]:
    base = {
        "date": day,
        "sentiment_score": sentiment,
        "risk_level": "low",
        "risk_explanation": "Steady delivery with minor tooling delays.",
        "achievements": [
            {
                "description": "Finalised threat-assessment brief",
                "impact_score": 7,
                "impact_reason": "Briefed to Wing Director; Wing level impact",
                "vision_verification": "supported",
            },
            {
                "description": "Resolved registry discrepancies",
                "impact_score": 5,
                "impact_reason": "Section-level data quality",
                "vision_verification": "contradicted",
            },
            {
                "description": "Mentored a new analyst",
                "impact_score": 3,
                "impact_reason": "Individual level",
                "vision_verification": "none",
            },
            {"description": "Updated desk SOP", "impact_score": 2, "impact_reason": "Desk level"},
        ],
        "challenges": [
            {"description": "Registry outage delayed validation", "severity": "high"},
            {"description": "Late inputs from partner unit"},
        ],
        "action_items": ["Request registry redundancy", "Schedule liaison sync"],
        "topics": ["threat assessment", "registry validation"],
        "credibility_rating": "high",
        "credibility_explanation": "Claims are specific and consistent.",
        "consistency_score": "high",
        "exaggeration_flags": ["'resolved all discrepancies' vs 9 of 42"],
        "performance_rating": "high",
        "performance_summary": "Strong analytical output this week.",
        "performance_strengths": ["Analytical rigour", "Timely briefs"],
        "performance_improvement_areas": ["Delegation"],
    }
    base.update(overrides)
    return base


def monthly_full_data() -> Dict[str, Any]:
    return {
        "employee_id": 101,
        "employee_info": dict(EMPLOYEE_INFO),
        "reports": [
            {"date": date(2026, 3, 7), "text": "Week 1 report text."},
            {"date": "2026-03-14", "text": "Week 2 report text (string date)."},
            {"text": "Week 3 report with no date."},
            {"date": datetime(2026, 3, 28, 17, 45)},
        ],
        "analyses": [
            _weekly_analysis(date(2026, 3, 7), 0.8),
            _weekly_analysis("2026-03-14", 0.2, risk_level="high", exaggeration_flags=[]),
            _weekly_analysis(
                datetime(2026, 3, 21, 9, 0),
                0.5,
                achievements=[],
                challenges=None,
                action_items=[],
                topics=None,
                performance_strengths=[],
                performance_improvement_areas=None,
            ),
        ],
        "metrics": {
            "avg_sentiment": 0.5,
            "sentiment_trend": "improving",
            "report_count": 4,
            "achievement_count": 8,
            "challenge_count": 4,
            "recurring_topics": ["threat assessment", "registry validation"],
            "risk_levels": {"low": 2, "high": 1},
        },
        "period_start": date(2026, 3, 1),
        "period_end": date(2026, 3, 31),
        "month": 3,
        "year": 2026,
        "formatted_vision_data": VISION_CURRENT,
        "formatted_jd_data": JD_TEXT,
    }


def monthly_minimal_data() -> Dict[str, Any]:
    """Only what the builder cannot do without: a month number."""
    return {"month": 3, "year": 2026}


# --------------------------------------------------------------------------
# Quarterly (quarterly_analysis_prompt)
# --------------------------------------------------------------------------

def _monthly_analysis(month: int, month_name: Optional[str], **overrides) -> Dict[str, Any]:
    base = {
        "month": month,
        "period_start": f"2026-{month:02d}-01",
        "period_end": f"2026-{month:02d}-28",
        "monthly_summary": f"Solid month ({month}) with consistent analytical output.",
        "progress_trends": {
            "performance_trend": "improving",
            "sentiment_trend": "positive",
            "risk_level_pattern": "decreasing",
            "challenge_resolution_progress": "improved",
        },
        "monthly_achievements": [
            {
                "description": "Delivered quarterly threat brief",
                "impact_score": 8,
                "impact_reason": "Wing-level decision input",
                "vision_verification": "supported",
            },
            {
                "description": "Registry clean-up",
                "impact_score": 5,
                "impact_reason": "Section data quality",
                "vision_verification": "contradicted",
            },
            {"description": "Peer mentoring"},
        ],
        "recurring_challenges": [
            {"description": "Registry outages", "severity": "high", "status": "ongoing"},
            {"description": "Late partner inputs"},
        ],
        "consistency_assessment": {
            "task_completion_reliability": "high",
            "work_quality_consistency": "medium",
            "performance_stability": "high",
            "notable_strengths": ["Analytical rigour"],
            "notable_weaknesses": ["Delegation"],
        },
        "growth_indicators": {
            "complexity_of_tasks": "increased",
            "skill_development_evidence": "high",
            "confidence_level_change": "increased",
            "approach_to_challenges": "more proactive",
        },
        "focus_areas": [
            {"project": "Threat assessment", "time_investment": "high", "priority_level": "high"},
            {"project": "Liaison"},
        ],
        "monthly_risk_assessment": {
            "overall_risk_level": "low",
            "risk_explanation": "No material risks.",
            "significant_risks": ["Single point of failure on registry"],
            "escalating_risks": [],
            "risk_mitigation_recommendations": ["Cross-train a backup analyst"],
        },
        "strategic_recommendations": [
            {"action": "Lead the provincial liaison summary", "priority": "high"},
            {"action": "Document registry workarounds"},
        ],
    }
    if month_name is not None:
        base["month_name"] = month_name
    base.update(overrides)
    return base


def quarterly_full_data() -> Dict[str, Any]:
    weekly_jan = _weekly_analysis(date(2026, 1, 10), 0.7)
    weekly_jan_dt = _weekly_analysis(datetime(2026, 1, 24, 8, 30), "0.3", exaggeration_flags=["inflated count"])
    weekly_feb_bad_sentiment = _weekly_analysis(
        IsoMonth(2, "2026-02-14"),
        "not-a-number",
        achievements=None,
        challenges=[],
        topics=[],
        action_items=None,
        exaggeration_flags=None,
        performance_strengths=None,
        performance_improvement_areas=[],
    )
    weekly_feb_none_sentiment = _weekly_analysis(MonthOnly(2, "week-of-feb-21"), None)
    weekly_mar_neutral = _weekly_analysis(date(2026, 3, 14), 0.5)
    weekly_string_date = _weekly_analysis("2026-03-21", 0.9)  # no .month -> never matched
    weekly_other_month = _weekly_analysis(date(2026, 5, 2), 0.9)  # no monthly analysis for May
    weekly_no_date = {"sentiment_score": 0.1}

    return {
        "employee_info": dict(EMPLOYEE_INFO),
        "monthly_analyses": [
            _monthly_analysis(1, "January"),
            _monthly_analysis(
                2,
                "February",
                monthly_achievements=[],
                recurring_challenges=None,
                focus_areas=[],
                strategic_recommendations=None,
                consistency_assessment={},
                growth_indicators={},
                monthly_risk_assessment={},
                progress_trends={},
            ),
            _monthly_analysis(3, "March"),
        ],
        "weekly_analyses": [
            weekly_jan,
            weekly_jan_dt,
            weekly_feb_bad_sentiment,
            weekly_feb_none_sentiment,
            weekly_mar_neutral,
            weekly_string_date,
            weekly_other_month,
            weekly_no_date,
        ],
        "metrics": {
            "avg_sentiment": 0.62,
            "sentiment_trend": "improving",
            "achievement_count": 21,
            "challenge_count": 7,
            "recurring_topics": ["threat assessment", "liaison"],
            "risk_levels": {"low": 9, "medium": 3},
            "weekly_report_count": 12,
            "performance_stability": "high",
            "task_reliability_trend": "improving",
            "quality_consistency_trend": "stable",
            "risk_trend": "decreasing",
            "challenge_resolution_trend": "improving",
            "achievement_impact_avg": 6.4,
            "weekly_credibility_data": {
                "avg_credibility_rating": "high",
                "credibility_trend": "stable",
                "exaggeration_frequency": 2,
            },
            "detailed_topics": [
                {"topic": "threat assessment", "frequency": 9},
                {"topic": "liaison"},
                {},
            ],
            "performance_rating_aggregation": {
                "most_common_rating": "high",
                "rating_trend": "improving",
                "rating_distribution": {"high": 0.6667, "medium": 0.3333},
            },
            "monthly_progress_trends": [
                {"month": 1, "performance_trend": "improving"},
                {"month": 2},
                {"month": 13, "sentiment_trend": "negative"},
            ],
            "monthly_summaries": [
                {"month": "January", "summary": "Strong start."},
                {"month": "February"},
                {},
            ],
        },
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 3, 31),
        "quarter": 1,
        "year": 2026,
        "formatted_vision_data": VISION_CURRENT + VISION_HISTORICAL,
        "formatted_jd_data": JD_TEXT,
    }


def quarterly_minimal_data() -> Dict[str, Any]:
    return {}


# --------------------------------------------------------------------------
# Fake LLM providers for LLMService
# --------------------------------------------------------------------------

class _Recorder:
    def __init__(self, text_responses: Optional[List[Any]] = None):
        self.calls: List[Dict[str, Any]] = []
        self._text = list(text_responses or [])

    @staticmethod
    def _next(queue: List[Any]):
        item = queue.pop(0) if queue else ""
        if isinstance(item, BaseException):
            raise item
        return item

    def generate_text(self, prompt, max_tokens=1000, temperature=0.7, num_ctx=8192, **kwargs):
        self.calls.append(
            {"method": "generate_text", "prompt": prompt, "max_tokens": max_tokens,
             "temperature": temperature, "num_ctx": num_ctx, "extra": kwargs}
        )
        return self._next(self._text)


class FakeTextProvider(_Recorder):
    """Provider WITHOUT native structured output (forces the text/JSON-extraction path)."""


class FakeStructuredProvider(_Recorder):
    """Provider WITH ``generate_structured_output``."""

    def __init__(self, structured_responses: List[Any], text_responses: Optional[List[Any]] = None):
        super().__init__(text_responses)
        self._structured = list(structured_responses)

    def generate_structured_output(self, prompt, json_schema=None, max_tokens=1000, temperature=0.0, num_ctx=8192, **kwargs):
        self.calls.append(
            {"method": "generate_structured_output", "prompt": prompt, "json_schema": json_schema,
             "max_tokens": max_tokens, "temperature": temperature, "num_ctx": num_ctx, "extra": kwargs}
        )
        return self._next(self._structured)


def describe_calls(calls: List[Dict[str, Any]], task_prompt: str) -> List[Dict[str, Any]]:
    """JSON-friendly view of provider calls.

    The task prompt itself is locked by the prompt snapshots, so here we record
    only whether the call starts with it plus the exact suffix appended to it.
    """
    out = []
    for call in calls:
        prompt = call["prompt"]
        row = {k: v for k, v in call.items() if k != "prompt"}
        row["prompt_starts_with_task_prompt"] = prompt.startswith(task_prompt)
        row["prompt_suffix_after_task_prompt"] = prompt[len(task_prompt):] if prompt.startswith(task_prompt) else prompt
        schema = row.get("json_schema")
        if isinstance(schema, type):
            row["json_schema"] = f"<pydantic model {schema.__name__}>"
        out.append(row)
    return out
