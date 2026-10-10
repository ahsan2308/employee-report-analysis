import sys
import os
from dotenv import load_dotenv
from sqlalchemy.sql import text  # Import the text function

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database import get_database

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection using SQLAlchemy."""
    try:
        # Get the database instance
        db_instance = get_database()

        # Test the connection
        with db_instance.engine.connect() as connection:
            # Use SQLAlchemy's text() to execute the raw SQL query
            result = connection.execute(text("SELECT version();"))
            db_version = result.fetchone()
            print(f"Successfully connected to the database. Version: {db_version[0]}")

    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    test_database_connection()