import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.database import get_database
from app.utils.env_loader import load_env_from_file
from app.models.import_models import CSVImportJob, ImportError, ImportStatus

# Load environment variables from specific .env file
load_env_from_file()

def test_import_models():
    """Test the CSV import models creation and basic operations."""
    print("\n=== Testing CSV Import Models ===")
    
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Create a test import job
        test_job = CSVImportJob(
            filename="test_employees_reports.csv",
            status=ImportStatus.PENDING.value,
            total_rows=10,
            employees_created=3,
            reports_created=7
        )
        session.add(test_job)
        session.flush()  # Flush to get the ID
        
        # Create a test error
        test_error = ImportError(
            job_id=test_job.job_id,
            row_number=5,
            field_name="email",
            error_message="Invalid email format",
            row_data={"name": "Test User", "email": "invalid-email"}
        )
        session.add(test_error)
        
        # Commit the changes
        session.commit()
        
        # Retrieve and verify
        saved_job = session.query(CSVImportJob).first()
        saved_error = session.query(ImportError).first()
        
        print(f"Job: {saved_job}")
        print(f"Error: {saved_error}")
        
        # Clean up
        session.delete(saved_error)
        session.delete(saved_job)
        session.commit()
        
        print("=== Test completed successfully ===")

if __name__ == "__main__":
    test_import_models()
