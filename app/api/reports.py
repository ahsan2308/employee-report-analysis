from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import Report
from app.schemas.reports_schema import ReportCreate
from app.models.db_models import Employee

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
@router.post("/")
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    try:
        new_report = Report(
            employee_id=report.employee_id,
            report_date=report.report_date,
            report_text=report.report_text,
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        return {"message": "Report added successfully", "report": new_report}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating report: {str(e)}")

# Get reports for an employee
# Get all reports for a specific employee
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