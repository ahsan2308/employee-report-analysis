from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import Report
from app.schemas.reports_schema import ReportCreate
from app.models.db_models import Employee
from app.schemas.reports_schema import ReportForm
from datetime import date
from app.services.vector_store_service import add_report_to_vector_store  # Updated import

# Initialize Router
router = APIRouter(prefix="/reports", tags=["Reports"])

# Dependency to get database session
def get_db():
    db_instance = get_database()  
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()

# Submit a new report
@router.post("/create")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    print("Request received at /reports/create")
    try:
        new_report = Report(
            employee_id=report.employee_id,
            report_date=report.report_date,
            report_text=report.report_text,
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        # Add the report to vector store for semantic search
        add_report_to_vector_store(
            report_id=str(new_report.report_id),
            employee_id=new_report.employee_id,
            report_date=str(new_report.report_date),
            report_text=new_report.report_text
        )
        
        return {"message": "Report added successfully", "report": new_report}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating report: {str(e)}")

# Submit a weekly report form
@router.post("/form")
def submit_report_form(report: ReportForm, db: Session = Depends(get_db)):
    """Submit a weekly report form."""
    print("Request received at /reports/form")
    try:
        # Check if the employee exists
        employee = db.query(Employee).filter(Employee.id == report.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found.")

        # Format report text
        report_text = (
            f"Key Tasks: {report.key_tasks_completed}\n"
            f"Impact: {report.impact_outcome}\n"
            f"Challenges: {report.challenges_faced}\n"
            f"Support: {report.support_required}\n"
            f"Planned Tasks: {report.tasks_planned_next_week}\n"
            f"Confidence Level: {report.confidence_level}\n"
            f"Nothing to Report Reason: {report.nothing_to_report_reason}"
        )
        
        # Create a new report
        new_report = Report(
            employee_id=report.employee_id,
            report_date=date.today(),
            report_text=report_text
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        # Add the report to vector store for semantic search
        add_report_to_vector_store(
            report_id=str(new_report.report_id),
            employee_id=new_report.employee_id,
            report_date=str(new_report.report_date),
            report_text=report_text
        )

        return {"message": "Report submitted successfully.", "report_id": new_report.report_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting report: {str(e)}")

# Get reports for an employee
@router.get("/{employee_id}")
def get_employee_reports(employee_id: int, db: Session = Depends(get_db)):
    """Retrieve all reports for a given employee ID."""
    
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Fetch reports for this employee
    reports = db.query(Report).filter(Report.employee_id == employee_id).all()
    
    if not reports:
        return {"message": "No reports found for this employee.", "employee_id": employee_id}

    return {"employee_id": employee_id, "employee_name": employee.name, "reports": reports}