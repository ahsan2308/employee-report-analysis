from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import Employee
from app.schemas.employee_schema import EmployeeCreate 

# Initialize Router
router = APIRouter(prefix="/employees", tags=["Employees"])

# Dependency to get database session
def get_db():
    db_instance = get_database()  
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()

# Create new employee 
@router.post("/")
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        new_employee = Employee(name=employee.name, wing=employee.wing, position=employee.position)
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        return {"message": "Employee added successfully", "employee": new_employee}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating employee: {str(e)}")

# Get all employees 
@router.get("/")
def get_all_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    if not employees:
        raise HTTPException(status_code=404, detail="No employees found")
    return employees
