"""
Visualization Service

Provides data aggregation and transformation functions for visualizations.
This service acts as a layer between the raw data and visualization endpoints.
"""
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import json
from functools import lru_cache
import re

from app.models.db_models import Employee, Report, EmployeeAnalysis
from app.database import get_database
from app.core.logger import logger

# Simple in-memory cache for expensive calculations
_cache = {}
_cache_expiry = {}
DEFAULT_CACHE_SECONDS = 300  # 5 minutes

def get_sentiment_trends(
    db: Session,  # Add db session parameter
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    start_date: Optional[date] = None,  # Changed from datetime to date
    end_date: Optional[date] = None,    # Changed from datetime to date
    interval: str = "month",
    cache_ttl: int = DEFAULT_CACHE_SECONDS
) -> Dict[str, Any]:
    """
    Get sentiment trends over time, optionally filtered by employee, department, and date range.
    
    Args:
        db: SQLAlchemy database session.
        employee_id: Optional filter for a specific employee
        department: Optional filter for a specific department/wing
        start_date: Optional start date for the trend analysis
        end_date: Optional end date for the trend analysis
        interval: Time grouping interval ('day', 'week', 'month', 'quarter', 'year')
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Dictionary with sentiment trend data ready for visualization
    """
    # Generate cache key based on parameters
    cache_key = f"sentiment_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check if we have cached results
    if cache_key in _cache and _cache_expiry.get(cache_key, 0) > datetime.now().timestamp():
        logger.debug(f"Using cached sentiment trends for key: {cache_key}")
        return _cache[cache_key]
    
    logger.info(f"Calculating sentiment trends with interval={interval}")
    
    # Simplify date handling - only use date components, ignore time
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date.split('T')[0].split(' ')[0], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse start_date: {start_date}, ignoring filter")
            start_date = None
    elif isinstance(start_date, datetime):  # Handle if datetime object is somehow passed
        start_date = start_date.date()

    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date.split('T')[0].split(' ')[0], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse end_date: {end_date}, ignoring filter")
            end_date = None
    elif isinstance(end_date, datetime):  # Handle if datetime object is somehow passed
        end_date = end_date.date()
                   
    # Base query for employee analyses
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
        
    # Apply filters with null-safety
    if employee_id:
        try:
            employee_id = int(employee_id) if not isinstance(employee_id, int) else employee_id
            query = query.filter(Report.employee_id == employee_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid employee_id format: {employee_id}, ignoring filter")
        
    if department:
        query = query.filter(Employee.wing == department)
            
    # Filter by report date instead of analysis date
    if start_date:
        query = query.filter(Report.report_date >= start_date)
            
    if end_date:
        query = query.filter(Report.report_date <= end_date)
        
    # Group by time interval and get average sentiment
    # Pass report_date as the column name to group by
    results = _group_by_time_interval(query, interval, "report_date")
        
    # Process results into visualization-ready format
    time_periods = []
    sentiment_values = []
        
    for period, avg_sentiment in results:
        if interval == 'day':
            formatted_period = period.strftime('%Y-%m-%d')
        elif interval == 'week':
            formatted_period = f"{period.year}-W{period.isocalendar()[1]}"
        elif interval == 'month':
            formatted_period = period.strftime('%Y-%m')
        elif interval == 'quarter':
            quarter = (period.month - 1) // 3 + 1
            formatted_period = f"{period.year}-Q{quarter}"
        else:  # year
            formatted_period = str(period.year)
                
        time_periods.append(formatted_period)
        sentiment_values.append(round(avg_sentiment, 2))
            
    # Prepare result dictionary
    trend_data = {
        "labels": time_periods,
        "datasets": [{
            "label": "Average Sentiment",
            "data": sentiment_values,
            "metadata": {
                "min": min(sentiment_values) if sentiment_values else 0,
                "max": max(sentiment_values) if sentiment_values else 0,
                "avg": round(sum(sentiment_values) / len(sentiment_values), 2) if sentiment_values else 0
            }
        }]
    }
        
    # Cache the result
    _cache[cache_key] = trend_data
    _cache_expiry[cache_key] = datetime.now().timestamp() + cache_ttl
        
    return trend_data

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

def clear_cache(prefix: Optional[str] = None):
    """
    Clear visualization cache, optionally filtered by key prefix.
    
    Args:
        prefix: Optional prefix to selectively clear cache entries
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

def extract_impact_score(impact_str: str) -> Optional[float]:
    """
    Extract numeric impact score from differently formatted impact strings.
    
    Args:
        impact_str: String containing the impact score in different formats:
                   "6 (Brief reason)" or "9/10" or just "9" or
                   "It has a high impact (8) on the team level..." or
                   "Elevated the quality of reports (Impact rating: 8)"
                   
    Returns:
        Extracted numeric impact score as a float, or None if extraction fails
    """
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
    
    Args:
        db: SQLAlchemy database session
        employee_id: Optional filter for a specific employee
        department: Optional filter for a specific department/wing
        start_date: Optional start date for the trend analysis
        end_date: Optional end date for the trend analysis
        interval: Time grouping interval ('day', 'week', 'month', 'quarter', 'year')
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Dictionary with impact score trend data ready for visualization
    """
    # Generate cache key based on parameters
    cache_key = f"impact_trends_{employee_id}_{department}_{start_date}_{end_date}_{interval}"
    
    # Check if we have cached results
    if cache_key in _cache and _cache_expiry.get(cache_key, 0) > datetime.now().timestamp():
        logger.debug(f"Using cached impact trends for key: {cache_key}")
        return _cache[cache_key]
    
    logger.info(f"Calculating impact score trends with interval={interval}")
    
    # Handle date parameters
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date.split('T')[0].split(' ')[0], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse start_date: {start_date}, ignoring filter")
            start_date = None
    elif isinstance(start_date, datetime):
        start_date = start_date.date()

    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date.split('T')[0].split(' ')[0], "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse end_date: {end_date}, ignoring filter")
            end_date = None
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    # Base query for employee analyses with achievements
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
    if employee_id:
        try:
            employee_id = int(employee_id) if not isinstance(employee_id, int) else employee_id
            query = query.filter(Report.employee_id == employee_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid employee_id format: {employee_id}, ignoring filter")
    
    if department:
        query = query.filter(Employee.wing == department)
    
    if start_date:
        query = query.filter(Report.report_date >= start_date)
    
    if end_date:
        query = query.filter(Report.report_date <= end_date)
    
    # Calculate average impact score per time period
    results_by_period = {}
    for report_date, achievements_json, _, _ in query.all():
        # Skip if no achievements
        if not achievements_json:
            continue
        
        # Determine period based on interval
        if interval == 'day':
            period = report_date.strftime('%Y-%m-%d')
        elif interval == 'week':
            period = f"{report_date.year}-W{report_date.isocalendar()[1]}"
        elif interval == 'month':
            period = report_date.strftime('%Y-%m')
        elif interval == 'quarter':
            quarter = (report_date.month - 1) // 3 + 1
            period = f"{report_date.year}-Q{quarter}"
        else:  # year
            period = str(report_date.year)
        
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
    
    # Prepare result dictionary
    trend_data = {
        "labels": time_periods,
        "datasets": [{
            "label": "Average Impact Score",
            "data": impact_values,
            "metadata": {
                "min": min(impact_values) if impact_values else 0,
                "max": max(impact_values) if impact_values else 0,
                "avg": round(sum(impact_values) / len(impact_values), 2) if impact_values else 0
            }
        }]
    }
    
    # Cache the result
    _cache[cache_key] = trend_data
    _cache_expiry[cache_key] = datetime.now().timestamp() + cache_ttl
    
    return trend_data
