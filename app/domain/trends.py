"""Trend direction of a series of monthly values ("improving", "declining" or "stable")."""


def analyze_trend(values, keys=None, context="default"):
    """
    Analyze trend using a standardized method across all metrics

    Numeric values are levels (higher is "improving" when they rise);
    strings are monthly trend labels, whose directions are aggregated.

    Args:
        values: List of values to analyze
        keys: Optional keys for sorting values (e.g., months)
        context: The context of analysis (default, risk, complexity)
    """
    if not values or len(values) < 2:
        return "stable"

    # If keys are provided, organize values by keys (e.g., months) in chronological order
    if keys:
        sorted_items = sorted(zip(keys, values))
        values = [v for _, v in sorted_items]

    # Convert string trend values to numeric scores for comparison
    labels = all(isinstance(v, str) for v in values)
    if labels:
        numeric_values = []
        for v in values:
            # Default context (performance, sentiment, quality)
            if context == "default":
                if v in ["improving", "improved", "increased"]:
                    numeric_values.append(1)
                elif v in ["declining", "declined", "decreased"]:
                    numeric_values.append(-1)
                elif v == "mixed":
                    numeric_values.append(0)  # Treat mixed as neutral
                else:  # stable, unchanged
                    numeric_values.append(0)

            # Risk context (risk level, challenges)
            elif context == "risk":
                if v in ["decreasing", "improved"]:
                    numeric_values.append(1)  # Decreasing risk is good
                elif v in ["increasing", "declined"]:
                    numeric_values.append(-1)  # Increasing risk is bad
                else:  # stable, unchanged
                    numeric_values.append(0)

            # Complexity/Growth context
            elif context == "complexity":
                if v in ["increased", "more proactive"]:
                    numeric_values.append(1)  # Increased complexity/proactivity is good
                elif v in ["decreased", "more reactive"]:
                    numeric_values.append(-1)  # Decreased complexity/reactivity is bad
                else:  # stable, unchanged
                    numeric_values.append(0)

        values = numeric_values

    if not labels:
        # Levels (scores, ratings, risk levels): the direction they moved in. The
        # least-squares change across the period, ignoring moves under 5% of the scale.
        count = len(values)
        mean_x = (count - 1) / 2
        mean_y = sum(values) / count
        slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values)) / sum(
            (x - mean_x) ** 2 for x in range(count))
        change = slope * (count - 1)
        tolerance = 0.05 * max(abs(v) for v in values)
        if change > tolerance:
            return "improving"
        if change < -tolerance:
            return "declining"
        return "stable"

    # Trend labels (one direction per month): aggregate the directions
    first, last = values[0], values[-1]
    avg = sum(values) / len(values)

    # If the trend is consistent throughout
    if all(v > 0 for v in values):
        return "improving"
    elif all(v < 0 for v in values):
        return "declining"

    # If trend is mixed but the last value shows clear direction
    if last > first + 0.1:
        return "improving"
    elif last < first - 0.1:
        return "declining"

    # If average shows a clear bias
    if avg > 0.3:
        return "improving"
    elif avg < -0.3:
        return "declining"

    return "stable"
