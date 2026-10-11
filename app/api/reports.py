from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.db_models import Report
from app.schemas.reports_schema import ReportCreate
from app.schemas.reports_schema import ReportForm
from datetime import date
from app.services.vector_store_service import add_report_to_vector_store  
from app.core.logger import logger  # Import the existing logger
from app.domain.reports import compose_report_text
from app.repositories.employees import get_employee
from app.repositories.reports import add_report, list_reports_for_employee

# Initialize Router
router = APIRouter(prefix="/reports", tags=["Reports"])


# Submit a new report
@router.post("/create")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    logger.info("Request received at /reports/create")
    try:
        # Check if the employee exists
        employee = get_employee(db, report.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")
            
        new_report = Report(
            employee_id=report.employee_id,
            report_date=report.report_date,
            report_text=report.report_text,
        )
        add_report(db, new_report)
        
        try:
            # Add the report to vector store for semantic search
            add_report_to_vector_store(
                report_id=str(new_report.report_id),
                employee_id=new_report.employee_id,
                report_date=str(new_report.report_date),
                report_text=new_report.report_text
            )
        except Exception as vector_error:
            # Log the vector store error but don't fail the entire operation
            logger.warning(f"Failed to add report to vector store: {str(vector_error)}")
        
        return {"message": "Report added successfully", "report": new_report}
    except HTTPException as he:
        # Re-raise HTTP exceptions as-is
        raise he
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
        # Check if the employee exists
        employee = get_employee(db, report.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

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
        
        # Create a new report
        new_report = Report(
            employee_id=report.employee_id,
            report_date=date.today(),
            report_text=report_text
        )
        add_report(db, new_report)
        
        try:
            # Add the report to vector store for semantic search
            add_report_to_vector_store(
                report_id=str(new_report.report_id),
                employee_id=new_report.employee_id,
                report_date=str(new_report.report_date),
                report_text=report_text
            )
        except Exception as vector_error:
            # Log the vector store error but don't fail the entire operation
            logger.warning(f"Failed to add report to vector store: {str(vector_error)}")

        return {"message": "Report submitted successfully.", "report_id": new_report.report_id}
    except HTTPException as he:
        # Re-raise HTTP exceptions as-is
        raise he
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