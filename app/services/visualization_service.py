"""
Visualization Service

Provides data aggregation and transformation functions for visualizations.
This service acts as a layer between the raw data and visualization endpoints.
"""
import copy
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.domain.periods import quarter_of_month
from app.repositories import visualizations as viz_repo
from app.domain.scoring import level_fraction, parse_impact

# Simple in-memory cache for expensive calculations
_cache = {}
_cache_expiry = {}
DEFAULT_CACHE_SECONDS = 300  # 5 minutes

def _convert_rating_to_score(rating: Optional[str]) -> float:
    """
    Convert string-based ratings to numerical scores for visualization.
    
    Args:
        rating: String rating ('low', 'medium', 'high') or None
        
    Returns:
        Numerical score (0.2 for low, 0.5 for medium, 0.8 for high)
        Returns 0.5 (neutral) for None or unrecognized values
    """
    if rating is None:
        logger.debug("Rating is None, defaulting to medium (0.5)")
        return 0.5
    score = level_fraction(rating)
    if score is None:
        logger.warning(f"Unknown rating value: '{rating}', defaulting to medium (0.5)")
        return 0.5
    return score

def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache if available and not expired."""
    if cache_key in _cache and _cache_expiry.get(cache_key, 0) > datetime.now().timestamp():
        logger.debug(f"Using cached data for key: {cache_key}")
        return copy.deepcopy(_cache[cache_key])  # callers may modify what they get
    return None

def _store_in_cache(cache_key: str, data: Dict[str, Any], ttl: int = DEFAULT_CACHE_SECONDS) -> None:
    """Store data in cache with expiration."""
    _cache[cache_key] = copy.deepcopy(data)
    _cache_expiry[cache_key] = datetime.now().timestamp() + ttl
    logger.debug(f"Stored data in cache with key: {cache_key}, expires in {ttl}s")

def _parse_date(date_value: Any) -> Optional[date]:
    """Parse date from various formats."""
    if not date_value:
        return None
        
    if isinstance(date_value, date):
        return date_value
        
    if isinstance(date_value, datetime):
        return date_value.date()
        
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value.split('T')[0].split(' ')[0], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse date: {date_value}, ignoring filter")
            return None
            
    logger.warning(f"Unexpected date format: {type(date_value)}, ignoring filter")
    return None

def _format_time_period(report_date: date, interval: str) -> str:
    """Format a date into a period string based on the interval."""
    if interval == 'day':
        return report_date.strftime('%Y-%m-%d')
    elif interval == 'week':
        iso_year, iso_week, _ = report_date.isocalendar()  # the ISO year: 2024-12-30 is in 2025-W1
        return f"{iso_year}-W{iso_week}"
    elif interval == 'month':
        return report_date.strftime('%Y-%m')
    elif interval == 'quarter':
        return f"{report_date.year}-Q{quarter_of_month(report_date.month)}"
    else:  # year
        return str(report_date.year)

def _build_trend_response(labels: List[str], data: List[float], dataset_label: str) -> Dict[str, Any]:
    """Build a standardized trend response object."""
    return {
        "labels": labels,
        "datasets": [{
            "label": dataset_label,
            "data": data,
            "metadata": {
                "min": min(data) if data else 0,
                "max": max(data) if data else 0,
                "avg": round(sum(data) / len(data), 2) if data else 0
            }
        }]
    }

def _sort_time_periods(periods: List[str], interval: str) -> List[str]:
    """
    Sort time periods chronologically rather than alphabetically.
    
    Args:
        periods: List of period strings formatted by _format_time_period
        interval: The interval type used ('day', 'week', 'month', 'quarter', 'year')
        
    Returns:
        List of period strings in correct chronological order
    """
    if not periods:
        return []
    
    # Define a function to convert period strings back to sortable values
    def period_to_sortable(period: str) -> tuple:
        if interval == 'day':
            # Format: 'YYYY-MM-DD'
            year, month, day = period.split('-')
            return (int(year), int(month), int(day))
        elif interval == 'week':
            # Format: 'YYYY-WNN'
            year, week_part = period.split('-W')
            return (int(year), int(week_part))
        elif interval == 'month':
            # Format: 'YYYY-MM'
            year, month = period.split('-')
            return (int(year), int(month))
        elif interval == 'quarter':
            # Format: 'YYYY-QN'
            year, quarter_part = period.split('-Q')
            return (int(year), int(quarter_part))
        else:  # year
            # Format: 'YYYY'
            return (int(period), 0)
    
    # Sort using the conversion function
    return sorted(periods, key=period_to_sortable)

def get_sentiment_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get sentiment trends over time, optionally filtered by employee, department, and date range.
    """
    # Generate cache key
    cache_key = f"sentiment_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating sentiment trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Average sentiment per period, oldest first
    results = viz_repo.sentiment_by_period(db, interval, employee_id=employee_id, department=department, start_date=start_date, end_date=end_date)
    
    # Process results
    time_periods = []
    sentiment_values = []
    
    for period, avg_sentiment in results:
        formatted_period = _format_time_period(period, interval)
        time_periods.append(formatted_period)
        sentiment_values.append(round(avg_sentiment, 2))
    
    # Build response
    trend_data = _build_trend_response(time_periods, sentiment_values, "Average Sentiment")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def _rating_trends(
    db: Session,
    column_name: str,
    cache_prefix: str,
    dataset_label: str,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Trend of a low/medium/high analysis rating over time, optionally filtered by employee,
    department, and date range. Ratings are converted to numeric scores (0.2, 0.5, 0.8).
    """
    # Generate cache key
    cache_key = f"{cache_prefix}_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating {cache_prefix.replace('_', ' ')} with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Group by time interval and collect data
    results_by_period = {}
    
    for report_date, rating, _, _ in viz_repo.trend_rows(db, column_name, employee_id=employee_id, department=department, start_date=start_date, end_date=end_date):
        # Skip if no rating
        if not rating:
            continue
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        results_by_period.setdefault(period, []).append(_convert_rating_to_score(rating))
    
    # Calculate averages and prepare results
    time_periods = []
    values = []
    
    # Sort periods chronologically
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        time_periods.append(period)
        values.append(round(sum(scores) / len(scores), 2) if scores else 0)
    
    # Build response
    trend_data = _build_trend_response(time_periods, values, dataset_label)
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def get_risk_level_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """Risk level trend over time (low/medium/high as 0.2/0.5/0.8)."""
    return _rating_trends(db, "risk_level", "risk_level_trends", "Average Risk Level", employee_id, department,
                          start_date, end_date, interval, cache_ttl)

def get_credibility_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """Credibility rating trend over time (low/medium/high as 0.2/0.5/0.8)."""
    return _rating_trends(db, "credibility_rating", "credibility_trends", "Average Credibility", employee_id, department,
                          start_date, end_date, interval, cache_ttl)

def get_consistency_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """Consistency score trend over time (low/medium/high as 0.2/0.5/0.8)."""
    return _rating_trends(db, "consistency_score", "consistency_trends", "Average Consistency", employee_id, department,
                          start_date, end_date, interval, cache_ttl)

def get_performance_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """Performance rating trend over time (low/medium/high as 0.2/0.5/0.8)."""
    return _rating_trends(db, "performance_rating", "performance_trends", "Average Performance", employee_id, department,
                          start_date, end_date, interval, cache_ttl)

def extract_impact_score(impact_str: str) -> Optional[float]:
    """Extract numeric impact score from differently formatted impact strings."""
    if not impact_str or not isinstance(impact_str, str):
        return None
    score = parse_impact(impact_str)
    if score is None:
        logger.warning(f"Could not extract impact score from: '{impact_str}'")
    return score

def get_impact_score_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get average impact score trends over time, optionally filtered by employee, department, and date range.
    """
    # Generate cache key
    cache_key = f"impact_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating impact score trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Calculate average impact score per time period
    results_by_period = {}
    for report_date, achievements_json, _, _ in viz_repo.trend_rows(
            db, "achievements_json", require_value=True, employee_id=employee_id, department=department, start_date=start_date, end_date=end_date):
        # Skip if no achievements
        if not achievements_json:
            continue
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        
        # Extract impact scores from achievements
        impact_scores = []
        for achievement in achievements_json:
            # Skip if not a dictionary or no impact field
            if not isinstance(achievement, dict) or 'impact' not in achievement:
                continue
                
            impact_score = extract_impact_score(achievement['impact'])
            if impact_score is not None:
                impact_scores.append(impact_score)
        
        # Add to period data if we have any scores
        if impact_scores:
            if period not in results_by_period:
                results_by_period[period] = []
            results_by_period[period].extend(impact_scores)
    
    # Calculate averages and prepare results
    time_periods = []
    impact_values = []
    
    # Sort periods chronologically ("2025-W10" after "2025-W2")
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        avg_impact = round(sum(scores) / len(scores), 2) if scores else 0
        
        time_periods.append(period)
        impact_values.append(avg_impact)
    
    # Build response
    trend_data = _build_trend_response(time_periods, impact_values, "Average Impact Score")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def get_sentiment_heatmap(
    db: Session,
    dimension: str = "department",  # Options: "department", "employee"
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS,
    employee_id: Optional[int] = None,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a heatmap of sentiment scores across time and another dimension (department or employee).
    
    Args:
        db: Database session
        dimension: The dimension to use for y-axis ("department" or "employee")
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        interval: Time interval for x-axis
        cache_ttl: Cache time-to-live
        employee_id: Optional employee filter
        department: Optional department (wing) filter
        
    Returns:
        Heatmap data with x_labels (time periods), y_labels (departments/employees),
        and cells with x,y coordinates and values
    """
    # Generate cache key
    cache_key = f"sentiment_heatmap_{dimension}_{start_date}_{end_date}_{interval}_{employee_id}_{department}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Generating sentiment heatmap with dimension={dimension}, interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Collect data organized by time period and dimension
    data_points = {}
    time_periods = set()
    dimension_values = set()
    
    rows = viz_repo.heatmap_rows(db, "sentiment_score", employee_id=employee_id, department=department, start_date=start_date, end_date=end_date)
    for report_date, sentiment, department, employee_id, employee_name in rows:
        # Format time period
        period = _format_time_period(report_date, interval)
        time_periods.add(period)
        
        # Determine dimension value
        if dimension == "department":
            dim_value = department
        else:  # employee
            dim_value = f"{employee_name} (#{employee_id})"
        
        dimension_values.add(dim_value)
        
        # Store data point
        if period not in data_points:
            data_points[period] = {}
        
        if dim_value not in data_points[period]:
            data_points[period][dim_value] = []
            
        data_points[period][dim_value].append(sentiment)
    
    # Sort the dimension values and time periods
    sorted_time_periods = _sort_time_periods(list(time_periods), interval)
    sorted_dimension_values = sorted(dimension_values)
    
    # Create mapping dictionaries for indices
    time_period_indices = {period: i for i, period in enumerate(sorted_time_periods)}
    dimension_indices = {dim: i for i, dim in enumerate(sorted_dimension_values)}
    
    # Calculate average values and create cells
    cells = []
    all_values = []
    
    for period, dim_values in data_points.items():
        x_idx = time_period_indices[period]
        
        for dim_value, sentiments in dim_values.items():
            y_idx = dimension_indices[dim_value]
            avg_sentiment = round(sum(sentiments) / len(sentiments), 2)
            
            cells.append({
                "x": x_idx,
                "y": y_idx,
                "value": avg_sentiment
            })
            
            all_values.append(avg_sentiment)
    
    # Calculate metadata
    min_val = min(all_values) if all_values else 0
    max_val = max(all_values) if all_values else 0
    avg_val = round(sum(all_values) / len(all_values), 2) if all_values else 0
    
    # Build response
    heatmap_data = {
        "x_labels": sorted_time_periods,
        "y_labels": sorted_dimension_values,
        "cells": cells,
        "metadata": {
            "min": min_val,
            "max": max_val,
            "avg": avg_val
        }
    }
    
    # Cache result
    _store_in_cache(cache_key, heatmap_data, cache_ttl)
    
    return heatmap_data

def get_impact_score_heatmap(
    db: Session,
    dimension: str = "department",  # Options: "department", "employee"
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS,
    employee_id: Optional[int] = None,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a heatmap of impact scores across time and another dimension (department or employee).
    
    Args:
        db: Database session
        dimension: The dimension to use for y-axis ("department" or "employee")
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        interval: Time interval for x-axis
        cache_ttl: Cache time-to-live
        employee_id: Optional employee filter
        department: Optional department (wing) filter
        
    Returns:
        Heatmap data with x_labels (time periods), y_labels (departments/employees),
        and cells with x,y coordinates and values
    """
    # Generate cache key
    cache_key = f"impact_heatmap_{dimension}_{start_date}_{end_date}_{interval}_{employee_id}_{department}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Generating impact score heatmap with dimension={dimension}, interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Collect data organized by time period and dimension
    data_points = {}
    time_periods = set()
    dimension_values = set()
    
    rows = viz_repo.heatmap_rows(db, "achievements_json", require_value=True, employee_id=employee_id, department=department, start_date=start_date, end_date=end_date)
    for report_date, achievements_json, department, employee_id, employee_name in rows:
        # Skip if no achievements
        if not achievements_json:
            continue
        
        # Format time period
        period = _format_time_period(report_date, interval)
        time_periods.add(period)
        
        # Determine dimension value
        if dimension == "department":
            dim_value = department
        else:  # employee
            dim_value = f"{employee_name} (#{employee_id})"
        
        dimension_values.add(dim_value)
        
        # Extract impact scores
        impact_scores = []
        for achievement in achievements_json:
            if not isinstance(achievement, dict) or 'impact' not in achievement:
                continue
                
            impact_score = extract_impact_score(achievement['impact'])
            if impact_score is not None:
                impact_scores.append(impact_score)
        
        # Store data point if we have scores
        if impact_scores:
            if period not in data_points:
                data_points[period] = {}
            
            if dim_value not in data_points[period]:
                data_points[period][dim_value] = []
                
            data_points[period][dim_value].extend(impact_scores)
    
    # Sort the dimension values and time periods
    sorted_time_periods = _sort_time_periods(list(time_periods), interval)
    sorted_dimension_values = sorted(dimension_values)
    
    # Create mapping dictionaries for indices
    time_period_indices = {period: i for i, period in enumerate(sorted_time_periods)}
    dimension_indices = {dim: i for i, dim in enumerate(sorted_dimension_values)}
    
    # Calculate average values and create cells
    cells = []
    all_values = []
    
    for period, dim_values in data_points.items():
        x_idx = time_period_indices[period]
        
        for dim_value, scores in dim_values.items():
            y_idx = dimension_indices[dim_value]
            avg_score = round(sum(scores) / len(scores), 2)
            
            cells.append({
                "x": x_idx,
                "y": y_idx,
                "value": avg_score
            })
            
            all_values.append(avg_score)
    
    # Calculate metadata
    min_val = min(all_values) if all_values else 0
    max_val = max(all_values) if all_values else 0
    avg_val = round(sum(all_values) / len(all_values), 2) if all_values else 0
    
    # Build response
    heatmap_data = {
        "x_labels": sorted_time_periods,
        "y_labels": sorted_dimension_values,
        "cells": cells,
        "metadata": {
            "min": min_val,
            "max": max_val,
            "avg": avg_val
        }
    }
    
    # Cache result
    _store_in_cache(cache_key, heatmap_data, cache_ttl)
    
    return heatmap_data

def clear_cache(prefix: Optional[str] = None):
    """
    Clear visualization cache, optionally filtered by key prefix.
    """
    global _cache, _cache_expiry
    
    if prefix:
        # Selectively clear cache entries that start with prefix
        keys_to_remove = [k for k in _cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            _cache.pop(key, None)
            _cache_expiry.pop(key, None)
        logger.info(f"Cleared {len(keys_to_remove)} cache entries with prefix '{prefix}'")
    else:
        # Clear all cache
        _cache = {}
        _cache_expiry = {}
        logger.info("Cleared entire visualization cache")

def get_multi_criteria_trends(
    db: Session,
    criteria: List[str],
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get trends for multiple criteria over time, optionally filtered by employee, department, and date range.
    
    Args:
        db: Database session
        criteria: List of criteria to include (e.g., ["sentiment", "risk", "credibility", "consistency", "performance"])
        employee_id: Optional employee ID filter
        department: Optional department filter
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        interval: Time interval for grouping ('day', 'week', 'month', 'quarter', 'year')
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Trend data with time periods as labels and multiple datasets for each criterion
    """
    # Generate cache key
    criteria_key = "_".join(sorted(criteria))
    cache_key = f"multi_criteria_trends_{criteria_key}_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating multi-criteria trends with criteria={criteria}, interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Define color mappings for each criterion to ensure consistent colors
    color_mappings = {
        "sentiment": {
            "backgroundColor": "rgba(52, 152, 219, 0.2)",  # Blue with transparency
            "borderColor": "rgba(52, 152, 219, 1)"         # Solid blue
        },
        "risk": {
            "backgroundColor": "rgba(231, 76, 60, 0.2)",   # Red with transparency
            "borderColor": "rgba(231, 76, 60, 1)"          # Solid red
        },
        "credibility": {
            "backgroundColor": "rgba(241, 196, 15, 0.2)",  # Distinct yellow with transparency
            "borderColor": "rgba(241, 196, 15, 1)"         # Solid yellow
        },
        "consistency": {
            "backgroundColor": "rgba(46, 204, 113, 0.2)",  # Green with transparency
            "borderColor": "rgba(46, 204, 113, 1)"         # Solid green
        },
        "performance": {
            "backgroundColor": "rgba(243, 156, 18, 0.2)",  # Orange with transparency
            "borderColor": "rgba(243, 156, 18, 1)"         # Solid orange
        },
        "impact": {
            "backgroundColor": "rgba(155, 89, 182, 0.2)",  # Purple with transparency
            "borderColor": "rgba(155, 89, 182, 1)"         # Solid purple
        }
    }
    
    # Define mapping between criterion names and their respective functions
    criterion_functions = {
        "sentiment": get_sentiment_trends,
        "risk": get_risk_level_trends,
        "credibility": get_credibility_trends,
        "consistency": get_consistency_trends,
        "performance": get_performance_trends,
        "impact": get_impact_score_trends
    }
    
    # Define display names for each criterion
    criterion_display_names = {
        "sentiment": "Sentiment Score",
        "risk": "Risk Level",
        "credibility": "Credibility Rating",
        "consistency": "Consistency Score",
        "performance": "Performance Rating",
        "impact": "Impact Score"
    }
    
    # Collect all time periods from all criteria
    all_time_periods = set()
    criterion_data = {}
    
    # Fetch data for each criterion
    for criterion in criteria:
        if criterion not in criterion_functions:
            logger.warning(f"Unknown criterion: {criterion}, skipping")
            continue
            
        # Call the appropriate function for this criterion
        criterion_func = criterion_functions[criterion]
        result = criterion_func(
            db=db,
            employee_id=employee_id,
            department=department,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            cache_ttl=cache_ttl  # Pass the cache_ttl parameter
        )
        
        # Store the result and collect time periods
        if result and "labels" in result and "datasets" in result and len(result["datasets"]) > 0:
            criterion_data[criterion] = result
            all_time_periods.update(result["labels"])
    
    # Convert to sorted list of time periods
    time_periods = _sort_time_periods(list(all_time_periods), interval)
    
    # Create datasets for each criterion
    datasets = []
    
    for criterion, result in criterion_data.items():
        # Get the first dataset (there should only be one per criterion)
        source_dataset = result["datasets"][0]
        
        # Create a mapping of time period to value for this criterion
        period_to_value = {
            period: value 
            for period, value in zip(result["labels"], source_dataset["data"])
        }
        
        # Create an array of values matching the combined time periods
        values = [
            period_to_value.get(period, None) 
            for period in time_periods
        ]
        
        # Create dataset with colors
        datasets.append({
            "label": criterion_display_names.get(criterion, criterion.capitalize()),
            "data": values,
            **color_mappings.get(criterion, {}),  # Add colors
            "metadata": source_dataset.get("metadata", {})
        })
    
    # Build response
    multi_criteria_trend_data = {
        "labels": time_periods,
        "datasets": datasets
    }
    
    # Cache result
    _store_in_cache(cache_key, multi_criteria_trend_data, cache_ttl)
    
    return multi_criteria_trend_data
