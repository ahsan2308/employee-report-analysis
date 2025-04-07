import sys
import os
from sqlalchemy import inspect

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.database import get_database
from app.utils.env_loader import load_env_from_file

# Important: Import all model classes so SQLAlchemy knows about them
from app.models.db_models import Employee, Report, QdrantMapping, EmployeeAnalysis

# Load environment variables from specific .env file
load_env_from_file()

def test_create_tables():
    """Test creating tables in the database."""
    try:
        # Get the database instance
        db_instance = get_database()
        
        # Print existing tables before creation
        with db_instance.create_session() as session:
            inspector = inspect(session.bind)
            schema_name = os.getenv("SCHEMA_NAME", "public")
            tables_before = inspector.get_table_names(schema=schema_name)
            print(f"Tables before creation: {tables_before}")

        # Create the tables
        print("Creating tables...")
        db_instance.create_tables()
        
        # Print tables after creation attempt
        with db_instance.create_session() as session:
            inspector = inspect(session.bind)
            tables_after = inspector.get_table_names(schema=schema_name)
            print(f"Tables after creation: {tables_after}")
            
            # Check which tables were actually created
            new_tables = set(tables_after) - set(tables_before)
            print(f"New tables created: {new_tables}")

        print("Tables creation process completed!")

    except Exception as e:
        print(f"Failed to create tables: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_create_tables()