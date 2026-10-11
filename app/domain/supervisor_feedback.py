"""Supervisor feedback rules: rating scales, rating a response, and the per-form summary cache."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def metric_max_value(metric_type: str, possible_values: Optional[str]) -> Optional[int]:
    """The top of a rating metric's scale: how many non-blank comma-separated options it has.

    None for other metric types or when no options are listed.
    """
    if possible_values and metric_type == 'R':
        return len([v.strip() for v in possible_values.split(',') if v.strip()])
    return None


def rate_response(metric_type: str, value: Optional[str], possible_values: Optional[str],
                  max_value: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
    """(numeric rating, scale maximum) of a rating response, or (None, None).

    The rating is the 1-based position of the value among the metric's options
    ("Poor, Fair, Good, Excellent": "Good" is 3); the maximum is the stored
    max_value, else the number of options.
    """
    if metric_type == 'R' and value and possible_values:
        options = [opt.strip() for opt in possible_values.split(',')]
        value_clean = value.strip()
        if value_clean in options:
            return options.index(value_clean) + 1, max_value or len(options)
    return None, None


def form_cache(responses: List[Tuple[Any, Any]], now: Optional[datetime] = None) -> Tuple[Dict[str, Any], List[Any]]:
    """The feedback_cache of a form from its (response, metric definition) pairs.

    Ratings are normalized to a percentage of their scale so 3- and 4-point
    scales compare. Returns the cache and the ids of rating metrics left out
    because they have no max_value to normalize against.
    """
    total_score = 0
    rating_count = 0
    rating_sum = 0  # percentage-normalized ratings
    text_responses_count = 0
    metrics_completed = 0
    total_metrics = len(responses)
    skipped_metric_ids = []

    # Group responses by section for form_data structure
    sections_dict = {}

    for response, metric_def in responses:
        # Count completed metrics (any response with non-empty text_response)
        if response.text_response and response.text_response.strip():
            metrics_completed += 1

        # For rating metrics, normalize to percentage (fixes scale comparison issue)
        if metric_def.metric_type == 'R' and response.text_response and metric_def.possible_values:
            try:
                possible_vals = [v.strip() for v in metric_def.possible_values.split(',')]
                if response.text_response in possible_vals:
                    position = possible_vals.index(response.text_response) + 1

                    # Example: position 4 of 4 = 100%, position 3 of 3 = 100%
                    if metric_def.max_value and metric_def.max_value > 0:
                        normalized_rating = (position / metric_def.max_value) * 100
                    else:
                        # Cannot normalize safely without max_value
                        skipped_metric_ids.append(metric_def.metric_id)
                        continue

                    rating_sum += normalized_rating
                    rating_count += 1
                    total_score += normalized_rating
            except (ValueError, AttributeError):
                pass

        # Count text-type responses
        if metric_def.metric_type == 'T' and response.text_response:
            text_responses_count += 1

        # Build form_data structure (grouped by section)
        section_key = (metric_def.section_id, metric_def.section)
        if section_key not in sections_dict:
            sections_dict[section_key] = {
                'section_id': metric_def.section_id,
                'section_name': metric_def.section,
                'metrics': []
            }

        sections_dict[section_key]['metrics'].append({
            'metric_id': metric_def.metric_id,
            'metric_name': metric_def.metric_name,
            'metric_type': metric_def.metric_type,
            'possible_values': metric_def.possible_values,
            'max_value': metric_def.max_value,
            'response': response.text_response
        })

    cache = {
        'stats': {
            'total_score': round(total_score, 2),
            'maximum_score': rating_count * 100,
            'average_rating': round(rating_sum / rating_count, 2) if rating_count > 0 else None,
            'text_responses_count': text_responses_count,
            'metrics_completed': metrics_completed,
            'total_metrics': total_metrics,
            'completion_percentage': round((metrics_completed / total_metrics * 100), 2) if total_metrics > 0 else 0
        },
        'form_data': {
            'sections': list(sections_dict.values())
        },
        'generated_at': (now or datetime.now(timezone.utc)).isoformat()
    }
    return cache, skipped_metric_ids
