import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database import get_database
from app.models.db_models import Employee
from sqlalchemy import text

# Load environment variables
load_dotenv()

db_instance = get_database()

def test_database_operations():
    """Test inserting and retrieving an employee record."""
    try:
        # Open a session
        with db_instance.create_session() as session:
            # Insert a test employee
            new_employee = Employee(name="Ali", wing="Operations", position="Data Analyst")
            session.add(new_employee)
            session.commit()

            # Retrieve and print the employee
            retrieved_employee = session.query(Employee).first()
            print(f"Retrieved Employee: {retrieved_employee}")

    except Exception as e:
        print(f"Database error: {e}")
        
if __name__ == "__main__":
    test_database_operations()
