"""Employee queries."""
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from app.db.database import get_database
from app.models.db_models import Employee
from app.core.logger import logger


def get_employee_info(employee_id: int) -> Dict[str, Any]:
    """
    Fetch basic information about an employee.
    
    Args:
        employee_id: The employee's ID
        
    Returns:
        Dictionary with employee information or None if not found
    """
    db_instance = get_database()
    
    try:
        with db_instance.create_session() as session:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                logger.error(f"Employee with ID {employee_id} not found")
                return None
                
            return {
                "id": employee.id,
                "name": employee.name,
                "wing": employee.wing,
                "position": employee.position
            }
    except Exception as e:
        logger.error(f"Error fetching employee info: {e}")
        return None


def get_employee(session: Session, employee_id: int) -> Optional[Employee]:
    """The employee row, in the caller's session."""
    return session.query(Employee).filter(Employee.id == employee_id).first()


def list_employees(session: Session) -> List[Employee]:
    return session.query(Employee).all()


def add_employee(session: Session, employee: Employee) -> Employee:
    """Insert an employee; the session is rolled back if the insert fails."""
    try:
        session.add(employee)
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(employee)
    return employee


def all_employee_ids(session: Session) -> Set[int]:
    return {employee_id for (employee_id,) in session.query(Employee.id).all()}


def upsert_employee(session: Session, employee_id: int, name: str, position: str, wing: str) -> bool:
    """Update an employee's position and wing, or create the employee with this id.

    The name of an existing employee is kept. Returns True when the employee was created.
    """
    existing = get_employee(session, employee_id)
    if existing:
        existing.position = position
        existing.wing = wing
        return False
    session.add(Employee(id=employee_id, name=name, position=position, wing=wing))
    session.flush()
    return True
