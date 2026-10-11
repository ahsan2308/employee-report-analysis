"""Level-to-score conversions used when computing analysis trends.

Several scales exist in the codebase (e.g. 2/1/0 for risk, 0.8/0.5/0.2 in
visualizations); only identical copies are shared here.
"""

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
