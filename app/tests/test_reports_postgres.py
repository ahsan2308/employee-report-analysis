import sys
import os
import uuid
from datetime import date
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.models.database_postgres import SessionLocal, engine, Base
from app.models.employee_postgres import Employee
from app.models.reports_postgres import Report

# Load environment variables
load_dotenv()

# Ensure tables are created
Base.metadata.create_all(engine)

def test_report_operations():
    """Test inserting and retrieving a report record."""
    try:
        # Open a session
        with SessionLocal() as session:
            # Ensure an employee exists (to satisfy the foreign key)
            new_employee = Employee(name="Ali", wing="Operations", position="Data Analyst")
            session.add(new_employee)
            session.commit()  # Ensure the employee is stored
            
            # Insert a test report
            test_report = Report(
                employee_id=new_employee.id,  # Use the newly created employee's ID
                report_date=date(2025, 3, 14),
                report_text="Ali completed a detailed market analysis.",
                qdrant_id=str(uuid.uuid4())  # Generate a unique identifier
            )
            session.add(test_report)
            session.commit()

            # Retrieve and print the report
            retrieved_report = session.query(Report).first()
            print(f"Retrieved Report: {retrieved_report}")

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    test_report_operations()
