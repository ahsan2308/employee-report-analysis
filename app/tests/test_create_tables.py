import sys
import os
from app.utils.env_loader import load_env_from_file

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.database import get_database

# Load environment variables from specific .env file
load_env_from_file()

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