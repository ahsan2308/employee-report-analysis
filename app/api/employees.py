from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.db_models import Employee
from app.schemas.employee_schema import EmployeeCreate 
from app.core.logger import logger
from app.repositories.employees import add_employee, list_employees

# Initialize Router
router = APIRouter(prefix="/employees", tags=["Employees"])


# Create new employee 
@router.post("/")
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        new_employee = add_employee(db, Employee(name=employee.name, wing=employee.wing, position=employee.position))
        return {"message": "Employee added successfully", "employee": new_employee}
    except Exception as e:
        logger.error(f"Error creating employee: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating employee")

# Get all employees 
@router.get("/")
def get_all_employees(db: Session = Depends(get_db)):
    employees = list_employees(db)
    if not employees:
        raise HTTPException(status_code=404, detail="No employees found")
    return employees
