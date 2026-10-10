"""Level-to-score conversions used when computing analysis trends.

Several scales exist in the codebase (e.g. 2/1/0 for risk, 0.8/0.5/0.2 in
visualizations); only identical copies are shared here.
"""


def consistency_level_score(level):
    """high -> 3, medium -> 2, anything else -> 1 (monthly consistency ratings)."""
    return 3 if level == "high" else (2 if level == "medium" else 1)
