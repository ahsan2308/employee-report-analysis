"""Submitting weekly reports: store the report, then index it for semantic search."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.db_models import Report
from app.repositories.employees import get_employee
from app.repositories.reports import add_report
from app.services.vector_store_service import add_report_to_vector_store


class EmployeeNotFound(LookupError):
    """The report names an employee that does not exist."""


def submit_report(db: Session, employee_id: int, report_date: date, report_text: str) -> Report:
    """Store an employee's report and add it to the vector store.

    The report is kept when the vector store step fails; that failure is only logged.
    Raises EmployeeNotFound for an unknown employee.
    """
    if not get_employee(db, employee_id):
        raise EmployeeNotFound(employee_id)

    report = add_report(db, Report(employee_id=employee_id, report_date=report_date, report_text=report_text))
    try:
        add_report_to_vector_store(
            report_id=str(report.report_id),
            employee_id=report.employee_id,
            report_date=str(report.report_date),
            report_text=report.report_text
        )
    except Exception as vector_error:
        logger.warning(f"Failed to add report to vector store: {str(vector_error)}")
    return report
