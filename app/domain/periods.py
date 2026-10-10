"""Calendar period helpers (month and quarter date ranges)."""
from typing import Tuple
from datetime import date
import calendar


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given month.
    
    Args:
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Tuple of (start_date, end_date) for the month
    """
    # Get the first day of the month
    start_date = date(year, month, 1)
    
    # Get the last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    return start_date, end_date


def get_quarter_date_range(year: int, quarter: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given quarter.
    
    Args:
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Tuple of (start_date, end_date) for the quarter
    """
    if quarter < 1 or quarter > 4:
        raise ValueError(f"Quarter must be between 1 and 4, got {quarter}")
    
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    
    start_date = date(year, start_month, 1)
    # Last day of end month
    last_day = calendar.monthrange(year, end_month)[1]
    end_date = date(year, end_month, last_day)
    
    return start_date, end_date
