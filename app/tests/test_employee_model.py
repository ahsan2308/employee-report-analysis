import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.models.database_postgres import SessionLocal, engine
from app.models.employee_postgres import Employee
from app.models.database_postgres import Base

# Load environment variables
load_dotenv()

# Create tables if they don't exist
Base.metadata.create_all(engine)

def test_database_operations():
    """Test inserting and retrieving an employee record."""
    try:
        # Open a session
        with SessionLocal() as session:
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
