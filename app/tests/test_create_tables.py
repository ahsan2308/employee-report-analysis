import sys
import os
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.models.db_models import Employee, Report
from app.database import get_database

# Load environment variables
load_dotenv()

def test_create_tables():
    """Test creating tables in the database."""
    try:
        # Get the database instance
        db_instance = get_database()

        # Create the tables
        db_instance.create_tables()
        print("Tables created successfully!")

    except Exception as e:
        print(f"Failed to create tables: {e}")

if __name__ == "__main__":
    test_create_tables()