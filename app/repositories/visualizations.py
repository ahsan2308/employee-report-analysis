"""Rows behind the trend and heatmap charts: weekly analyses joined to their reports and employees."""
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.db_models import Employee, EmployeeAnalysis, Report


def apply_report_filters(query, employee_id, department, start_date, end_date):
    """Filter a query over reports by employee, department (wing) and report date range."""
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


def average_sentiment_by_period(query, interval: str, date_column_name: str):
    """
    Group query results by a specified time interval.
    
    Args:
        query: SQLAlchemy query to apply grouping to
        interval: Time interval to group by ('day', 'week', 'month', 'quarter', 'year')
        date_column_name: Name of the date column to use for grouping
        
    Returns:
        List of (period, average sentiment) rows
    """
    date_column = getattr(Report, date_column_name)
    unit = interval if interval in ('day', 'week', 'month', 'quarter') else 'year'
    period = func.date_trunc(unit, date_column)
    # Ordered by period, so the trend reads chronologically
    return query.group_by(period).order_by(period).with_entities(
        period,
        func.avg(EmployeeAnalysis.sentiment_score)
    ).all()


def _analysis_query(session: Session, *columns):
    return session.query(*columns).join(
        EmployeeAnalysis, Report.report_id == EmployeeAnalysis.report_id
    ).join(
        Employee, Report.employee_id == Employee.id
    )


def trend_query(session: Session, column_name: str, employee_id=None, department=None,
                start_date: Optional[date] = None, end_date: Optional[date] = None, require_value: bool = False):
    """(report_date, analysis column, employee_id, wing) for the weekly analyses matching the filters.

    require_value leaves out analyses whose column is NULL.
    """
    column = getattr(EmployeeAnalysis, column_name)
    query = _analysis_query(session, Report.report_date.label('report_date'), column, Report.employee_id, Employee.wing)
    if require_value:
        query = query.filter(column.isnot(None))
    return apply_report_filters(query, employee_id, department, start_date, end_date)


def trend_rows(session: Session, column_name: str, **filters) -> List[Any]:
    return trend_query(session, column_name, **filters).all()


def sentiment_by_period(session: Session, interval: str, **filters) -> List[Any]:
    """(period start, average sentiment score) per period, oldest first."""
    return average_sentiment_by_period(trend_query(session, "sentiment_score", **filters), interval, "report_date")


def heatmap_rows(session: Session, column_name: str, employee_id=None, department=None,
                 start_date: Optional[date] = None, end_date: Optional[date] = None,
                 require_value: bool = False) -> List[Any]:
    """(report_date, analysis column, department, employee_id, employee_name), by date then employee."""
    column = getattr(EmployeeAnalysis, column_name)
    query = _analysis_query(
        session,
        Report.report_date,
        column,
        Employee.wing.label('department'),
        Employee.id.label('employee_id'),
        Employee.name.label('employee_name')
    )
    if require_value:
        query = query.filter(column.isnot(None))
    # A fixed row order keeps the output stable
    query = apply_report_filters(query, employee_id, department, start_date, end_date)
    return query.order_by(Report.report_date, Employee.id).all()
