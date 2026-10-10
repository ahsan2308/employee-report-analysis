"""Employee queries."""
from typing import Dict, Any
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
