"""Scores for ratings, sentiment and achievement impact.

Three scales are in use, each defined once here:
- rating_score: high/medium/low as 3/2/1, for averages and trends of ratings
- risk_score: high/medium/low risk as 2/1/0
- 0-1 fractions (sentiment_score, level_fraction): 0.8/0.5/0.2, as weekly
  sentiment is stored and as the charts plot ratings
"""
import re
from typing import Iterable, Optional

RATING_SCORES = {"high": 3, "medium": 2, "low": 1}


def rating_score(level):
    """high -> 3, medium -> 2, low -> 1 (any case); None for anything else.

    Callers leave None out of averages and trends, so an unrecognised rating
    neither raises nor lowers a score.
    """
    if not isinstance(level, str):
        return None
    return RATING_SCORES.get(level.strip().lower())


def score_level(average):
    """The level for an average rating score: above 2.5 high, above 1.5 medium, else low."""
    if average > 2.5:
        return "high"
    if average > 1.5:
        return "medium"
    return "low"


def risk_score(level) -> int:
    """high -> 2, medium -> 1, anything else -> 0 (monthly risk levels in quarterly trends)."""
    return 2 if level == "high" else (1 if level == "medium" else 0)


SENTIMENT_SCORES = {"positive": 0.8, "neutral": 0.5, "negative": 0.2}
LEVEL_FRACTIONS = {"high": 0.8, "medium": 0.5, "low": 0.2}


def sentiment_score(sentiment) -> float:
    """The stored score of a weekly sentiment: positive 0.8, neutral 0.5, negative 0.2, else 0.0."""
    return SENTIMENT_SCORES.get(sentiment, 0.0)


def sentiment_label(score) -> str:
    """The sentiment a 0-1 score stands for: below 0.5 negative, above positive, else (or unreadable) neutral."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "neutral"
    if score < 0.5:
        return "negative"
    if score > 0.5:
        return "positive"
    return "neutral"


def level_fraction(level) -> Optional[float]:
    """high -> 0.8, medium -> 0.5, low -> 0.2 (any case); None for anything else."""
    if not isinstance(level, str):
        return None
    return LEVEL_FRACTIONS.get(level.strip().lower())


_IMPACT_PATTERNS = (
    (re.match, r"^(\d+(\.\d+)?)\s*\("),                 # "8 (Good impact)"
    (re.match, r"^(\d+(\.\d+)?)/\d+"),                   # "9/10"
    (re.match, r"^(\d+(\.\d+)?)$"),                       # "9"
    (re.search, r"\((\d+(\.\d+)?)\)"),                  # "It has a high impact (8) on the team"
    (re.search, r"(?i)Impact rating:\s*(\d+(\.\d+)?)"),  # "Impact rating: 7"
)


def parse_impact(value) -> Optional[float]:
    """An achievement's impact as a number: a number as is, or one read from text
    such as "8 (reason)", "9/10", "9", "high impact (8)" or "Impact rating: 7".
    None when there is no number to read."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not value or not isinstance(value, str):
        return None
    for find, pattern in _IMPACT_PATTERNS:
        found = find(pattern, value)
        if found:
            return float(found.group(1))
    return None


def average_impact(achievements: Iterable[dict]) -> Optional[float]:
    """Mean impact of achievements (impact_score, else the legacy impact text), to 2 places.

    Achievements without a readable impact are left out; None when none has one.
    """
    scores = []
    for achievement in achievements:
        impact = achievement.get("impact_score")
        score = parse_impact(impact if impact is not None else achievement.get("impact"))
        if score is not None:
            scores.append(score)
    return round(sum(scores) / len(scores), 2) if scores else None
