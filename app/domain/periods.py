"""Calendar periods: report weeks, months and quarters, and parsing period dates."""
from typing import List, Tuple
from datetime import date, datetime, timedelta
import calendar
import re

MONTH_NAMES = ("January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December")


def month_name(month: int) -> str:
    """ "March" for 3; "Month 13" for a number outside 1-12."""
    return MONTH_NAMES[month - 1] if isinstance(month, int) and 1 <= month <= 12 else f"Month {month}"


def months_in_quarter(quarter: int) -> List[int]:
    """The month numbers in a quarter: [4, 5, 6] for quarter 2."""
    return [(quarter - 1) * 3 + offset for offset in (1, 2, 3)]


def quarter_of_month(month: int) -> int:
    """The quarter (1-4) a month (1-12) falls in."""
    return (month - 1) // 3 + 1


def report_week_start(report_date: date) -> date:
    """A weekly report covers the 7 days ending on its report date; this is the first of them."""
    return report_date - timedelta(days=6)


def parse_period_date(value: str) -> date:
    """Parse a report-period date string.

    Accepts MM/DD/YYYY (DD/MM/YYYY when that is not a valid date), YYYY-MM-DD,
    and MM-DD-YYYY (DD-MM-YYYY when that is not a valid date). A trailing time,
    as spreadsheet exports write it ("2024-03-01 00:00:00", "2024-03-01T10:30"),
    is ignored. Raises ValueError for anything else.
    """
    value = re.sub(r"[ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?$", "", value.strip())
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
        formats = ("%m/%d/%Y", "%d/%m/%Y")
    elif re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
        formats = ("%Y-%m-%d",)
    elif re.fullmatch(r"\d{1,2}-\d{1,2}-\d{4}", value):
        formats = ("%m-%d-%Y", "%d-%m-%Y")
    else:
        raise ValueError(f"Unrecognised date: {value}")
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value}")


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
    
    start_month, _, end_month = months_in_quarter(quarter)
    
    start_date = date(year, start_month, 1)
    # Last day of end month
    last_day = calendar.monthrange(year, end_month)[1]
    end_date = date(year, end_month, last_day)
    
    return start_date, end_date
