from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.reports_schema import ReportCreate
from app.schemas.reports_schema import ReportForm
from datetime import date
from app.services.report_service import EmployeeNotFound, submit_report
from app.core.logger import logger  # Import the existing logger
from app.domain.reports import compose_report_text
from app.repositories.employees import get_employee
from app.repositories.reports import list_reports_for_employee

# Initialize Router
router = APIRouter(prefix="/reports", tags=["Reports"])


# Submit a new report
@router.post("/create")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    logger.info("Request received at /reports/create")
    try:
        new_report = submit_report(db, report.employee_id, report.report_date, report.report_text)
        
        return {"message": "Report added successfully", "report": new_report}
    except EmployeeNotFound:
        raise HTTPException(status_code=404, detail="Employee not found.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating report")

# Submit a weekly report form
@router.post("/form")
def submit_report_form(report: ReportForm, db: Session = Depends(get_db)):
    """Submit a weekly report form."""
    logger.info("Request received at /reports/form")
    try:
        # Same text format as reports imported from CSV or synced
        report_text = compose_report_text(
            tasks_completed=report.key_tasks_completed,
            impact=report.impact_outcome,
            challenges=report.challenges_faced,
            support_required=report.support_required,
            tasks_planned=report.tasks_planned_next_week,
            confidence_level=report.confidence_level,
            nothing_to_report_reason=report.nothing_to_report_reason
        )
        
        new_report = submit_report(db, report.employee_id, date.today(), report_text)

        return {"message": "Report submitted successfully.", "report_id": new_report.report_id}
    except EmployeeNotFound:
        raise HTTPException(status_code=404, detail="Employee not found.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting report: {str(e)}")
        raise HTTPException(status_code=500, detail="Error submitting report")

# Get reports for an employee
@router.get("/{employee_id}")
def get_employee_reports(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all reports for a given employee ID."""
    
    # Check if employee exists
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Fetch reports for this employee
    reports = list_reports_for_employee(db, employee_id)
    
    if not reports:
        return {"message": "No reports found for this employee.", "employee_id": employee_id}

    return {"employee_id": employee_id, "employee_name": employee.name, "reports": reports}