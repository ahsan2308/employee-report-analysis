"""
Visualization Service

Provides data aggregation and transformation functions for visualizations.
This service acts as a layer between the raw data and visualization endpoints.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
import re

from app.models.db_models import Employee, Report, EmployeeAnalysis
from app.core.logger import logger

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
        
    rating_lower = rating.lower().strip()
    
    if rating_lower == 'low':
        return 0.2
    elif rating_lower == 'medium':
        return 0.5
    elif rating_lower == 'high':
        return 0.8
    else:
        logger.warning(f"Unknown rating value: '{rating}', defaulting to medium (0.5)")
        return 0.5

def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache if available and not expired."""
    if cache_key in _cache and _cache_expiry.get(cache_key, 0) > datetime.now().timestamp():
        logger.debug(f"Using cached data for key: {cache_key}")
        return _cache[cache_key]
    return None

def _store_in_cache(cache_key: str, data: Dict[str, Any], ttl: int = DEFAULT_CACHE_SECONDS) -> None:
    """Store data in cache with expiration."""
    _cache[cache_key] = data
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
        return f"{report_date.year}-W{report_date.isocalendar()[1]}"
    elif interval == 'month':
        return report_date.strftime('%Y-%m')
    elif interval == 'quarter':
        quarter = (report_date.month - 1) // 3 + 1
        return f"{report_date.year}-Q{quarter}"
    else:  # year
        return str(report_date.year)

def _apply_common_filters(query, employee_id, department, start_date, end_date):
    """Apply common filters to a query."""
    # Filter by employee
    if employee_id:
        try:
            employee_id = int(employee_id) if not isinstance(employee_id, int) else employee_id
            query = query.filter(Report.employee_id == employee_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid employee_id format: {employee_id}, ignoring filter")
    
    # Filter by department
    if department:
        query = query.filter(Employee.wing == department)
    
    # Filter by date range
    if start_date:
        query = query.filter(Report.report_date >= start_date)
    
    if end_date:
        query = query.filter(Report.report_date <= end_date)
    
    return query

def _group_by_time_interval(query, interval: str, date_column_name: str):
    """
    Group query results by a specified time interval.
    
    Args:
        query: SQLAlchemy query to apply grouping to
        interval: Time interval to group by ('day', 'week', 'month', 'quarter', 'year')
        date_column_name: Name of the date column to use for grouping
        
    Returns:
        Query with appropriate grouping applied
    """
    date_column = getattr(Report, date_column_name)
    
    if interval == 'day':
        # Group by day
        return query.group_by(
            func.date_trunc('day', date_column)
        ).values(
            func.date_trunc('day', date_column),
            func.avg(EmployeeAnalysis.sentiment_score)
        )
    elif interval == 'week':
        # Group by week
        return query.group_by(
            func.date_trunc('week', date_column)
        ).values(
            func.date_trunc('week', date_column),
            func.avg(EmployeeAnalysis.sentiment_score)
        )
    elif interval == 'month':
        # Group by month
        return query.group_by(
            func.date_trunc('month', date_column)
        ).values(
            func.date_trunc('month', date_column),
            func.avg(EmployeeAnalysis.sentiment_score)
        )
    elif interval == 'quarter':
        # Group by quarter
        return query.group_by(
            func.date_trunc('quarter', date_column)
        ).values(
            func.date_trunc('quarter', date_column),
            func.avg(EmployeeAnalysis.sentiment_score)
        )
    else:  # year
        # Group by year
        return query.group_by(
            func.date_trunc('year', date_column)
        ).values(
            func.date_trunc('year', date_column),
            func.avg(EmployeeAnalysis.sentiment_score)
        )

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
    
    # Base query
    query = db.query(  
        Report.report_date.label('report_date'),  
        EmployeeAnalysis.sentiment_score,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id 
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Group by time interval
    results = _group_by_time_interval(query, interval, "report_date")
    
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

def get_risk_level_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get risk level trends over time, optionally filtered by employee, department, and date range.
    Risk levels (low, medium, high) are converted to numeric scores (0.2, 0.5, 0.8) for visualization.
    """
    # Generate cache key
    cache_key = f"risk_level_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating risk level trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(  
        Report.report_date.label('report_date'),  
        EmployeeAnalysis.risk_level,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id 
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Group by time interval and collect data
    results_by_period = {}
    
    for report_date, risk_level, _, _ in query.all():
        # Skip if no risk level
        if not risk_level:
            continue
            
        # Convert string risk level to numeric score
        risk_score = _convert_rating_to_score(risk_level)
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        
        # Add to period data
        if period not in results_by_period:
            results_by_period[period] = []
        results_by_period[period].append(risk_score)
    
    # Calculate averages and prepare results
    time_periods = []
    risk_values = []
    
    # Sort periods chronologically
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        avg_risk = round(sum(scores) / len(scores), 2) if scores else 0
        
        time_periods.append(period)
        risk_values.append(avg_risk)
    
    # Build response
    trend_data = _build_trend_response(time_periods, risk_values, "Average Risk Level")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def get_credibility_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get credibility rating trends over time, optionally filtered by employee, department, and date range.
    Credibility ratings (low, medium, high) are converted to numeric scores (0.2, 0.5, 0.8) for visualization.
    """
    # Generate cache key
    cache_key = f"credibility_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating credibility trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(  
        Report.report_date.label('report_date'),  
        EmployeeAnalysis.credibility_rating,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id 
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Group by time interval and collect data
    results_by_period = {}
    
    for report_date, credibility_rating, _, _ in query.all():
        # Skip if no credibility rating
        if not credibility_rating:
            continue
            
        # Convert string credibility rating to numeric score
        credibility_score = _convert_rating_to_score(credibility_rating)
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        
        # Add to period data
        if period not in results_by_period:
            results_by_period[period] = []
        results_by_period[period].append(credibility_score)
    
    # Calculate averages and prepare results
    time_periods = []
    credibility_values = []
    
    # Sort periods chronologically
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        avg_credibility = round(sum(scores) / len(scores), 2) if scores else 0
        
        time_periods.append(period)
        credibility_values.append(avg_credibility)
    
    # Build response
    trend_data = _build_trend_response(time_periods, credibility_values, "Average Credibility")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def get_consistency_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get consistency score trends over time, optionally filtered by employee, department, and date range.
    Consistency scores (low, medium, high) are converted to numeric scores (0.2, 0.5, 0.8) for visualization.
    """
    # Generate cache key
    cache_key = f"consistency_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating consistency trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(  
        Report.report_date.label('report_date'),  
        EmployeeAnalysis.consistency_score,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id 
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Group by time interval and collect data
    results_by_period = {}
    
    for report_date, consistency_score, _, _ in query.all():
        # Skip if no consistency score
        if not consistency_score:
            continue
            
        # Convert string consistency score to numeric score
        numeric_score = _convert_rating_to_score(consistency_score)
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        
        # Add to period data
        if period not in results_by_period:
            results_by_period[period] = []
        results_by_period[period].append(numeric_score)
    
    # Calculate averages and prepare results
    time_periods = []
    consistency_values = []
    
    # Sort periods chronologically
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        avg_consistency = round(sum(scores) / len(scores), 2) if scores else 0
        
        time_periods.append(period)
        consistency_values.append(avg_consistency)
    
    # Build response
    trend_data = _build_trend_response(time_periods, consistency_values, "Average Consistency")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def get_performance_trends(
    db: Session,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get performance rating trends over time, optionally filtered by employee, department, and date range.
    Performance ratings (low, medium, high) are converted to numeric scores (0.2, 0.5, 0.8) for visualization.
    """
    # Generate cache key
    cache_key = f"performance_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Calculating performance trends with interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(  
        Report.report_date.label('report_date'),  
        EmployeeAnalysis.performance_rating,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id 
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Group by time interval and collect data
    results_by_period = {}
    
    for report_date, performance_rating, _, _ in query.all():
        # Skip if no performance rating
        if not performance_rating:
            continue
            
        # Convert string performance rating to numeric score
        performance_score = _convert_rating_to_score(performance_rating)
        
        # Determine period based on interval
        period = _format_time_period(report_date, interval)
        
        # Add to period data
        if period not in results_by_period:
            results_by_period[period] = []
        results_by_period[period].append(performance_score)
    
    # Calculate averages and prepare results
    time_periods = []
    performance_values = []
    
    # Sort periods chronologically
    for period in _sort_time_periods(list(results_by_period.keys()), interval):
        scores = results_by_period[period]
        avg_performance = round(sum(scores) / len(scores), 2) if scores else 0
        
        time_periods.append(period)
        performance_values.append(avg_performance)
    
    # Build response
    trend_data = _build_trend_response(time_periods, performance_values, "Average Performance")
    
    # Cache result
    _store_in_cache(cache_key, trend_data, cache_ttl)
    
    return trend_data

def extract_impact_score(impact_str: str) -> Optional[float]:
    """Extract numeric impact score from differently formatted impact strings."""
    if not impact_str or not isinstance(impact_str, str):
        return None
    
    # Case 1: Extract number before parenthesis (e.g., "8 (Good impact)")
    parenthesis_match = re.match(r'^(\d+(\.\d+)?)\s*\(', impact_str)
    if parenthesis_match:
        return float(parenthesis_match.group(1))
    
    # Case 2: Extract number before slash (e.g., "9/10")
    slash_match = re.match(r'^(\d+(\.\d+)?)/\d+', impact_str)
    if slash_match:
        return float(slash_match.group(1))
    
    # Case 3: Just a number (e.g., "9")
    number_match = re.match(r'^(\d+(\.\d+)?)$', impact_str)
    if number_match:
        return float(number_match.group(1))
    
    # Case 4: Number inside parentheses within text (e.g., "It has a high impact (8) on the team")
    embedded_parentheses_match = re.search(r'\((\d+(\.\d+)?)\)', impact_str)
    if embedded_parentheses_match:
        return float(embedded_parentheses_match.group(1))
    
    # Case 5: Number after "Impact rating:" or similar label
    rating_label_match = re.search(r'Impact rating:\s*(\d+(\.\d+)?)', impact_str, re.IGNORECASE)
    if rating_label_match:
        return float(rating_label_match.group(1))
    
    # Failed to extract
    logger.warning(f"Could not extract impact score from: '{impact_str}'")
    return None

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
    
    # Base query
    query = db.query(
        Report.report_date.label('report_date'),
        EmployeeAnalysis.achievements_json,
        Report.employee_id,
        Employee.wing
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id
    ).join(
        Employee, Report.employee_id == Employee.id
    ).filter(EmployeeAnalysis.achievements_json.isnot(None))
    
    # Apply filters
    query = _apply_common_filters(query, employee_id, department, start_date, end_date)
    
    # Calculate average impact score per time period
    results_by_period = {}
    for report_date, achievements_json, _, _ in query.all():
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
    
    # Sort periods chronologically
    for period in sorted(results_by_period.keys()):
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
    cache_ttl: int = DEFAULT_CACHE_SECONDS
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
        
    Returns:
        Heatmap data with x_labels (time periods), y_labels (departments/employees),
        and cells with x,y coordinates and values
    """
    # Generate cache key
    cache_key = f"sentiment_heatmap_{dimension}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Generating sentiment heatmap with dimension={dimension}, interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(
        Report.report_date,
        EmployeeAnalysis.sentiment_score,
        Employee.wing.label('department'),
        Employee.id.label('employee_id'),
        Employee.name.label('employee_name')
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id
    ).join(
        Employee, Report.employee_id == Employee.id
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(Report.report_date >= start_date)
    
    if end_date:
        query = query.filter(Report.report_date <= end_date)
    
    # Collect data organized by time period and dimension
    data_points = {}
    time_periods = set()
    dimension_values = set()
    
    for report_date, sentiment, department, employee_id, employee_name in query.all():
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
    cache_ttl: int = DEFAULT_CACHE_SECONDS
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
        
    Returns:
        Heatmap data with x_labels (time periods), y_labels (departments/employees),
        and cells with x,y coordinates and values
    """
    # Generate cache key
    cache_key = f"impact_heatmap_{dimension}_{start_date}_{end_date}_{interval}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    logger.info(f"Generating impact score heatmap with dimension={dimension}, interval={interval}")
    
    # Parse dates
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    
    # Base query
    query = db.query(
        Report.report_date,
        EmployeeAnalysis.achievements_json,
        Employee.wing.label('department'),
        Employee.id.label('employee_id'),
        Employee.name.label('employee_name')
    ).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id
    ).join(
        Employee, Report.employee_id == Employee.id
    ).filter(EmployeeAnalysis.achievements_json.isnot(None))
    
    # Apply date filters
    if start_date:
        query = query.filter(Report.report_date >= start_date)
    
    if end_date:
        query = query.filter(Report.report_date <= end_date)
    
    # Collect data organized by time period and dimension
    data_points = {}
    time_periods = set()
    dimension_values = set()
    
    for report_date, achievements_json, department, employee_id, employee_name in query.all():
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
