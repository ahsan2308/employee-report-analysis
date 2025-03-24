import os
from app.database.postgres_database import PostgresDatabase
from app.database.mssql_database import MSSQLDatabase

# Load environment variables
DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()  # Default to PostgreSQL
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
DB_HOST = os.getenv("DB_HOST", "localhost")  # Use 'db' if running in Docker
DB_PORT = os.getenv("DB_PORT", "5432")  # Default PostgreSQL port
DB_NAME = os.getenv("DB_NAME", "employee_reports")
from app.models.base import schema_name

def get_database():
    # Construct the database URL dynamically
    if DB_TYPE == "postgres":
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        return PostgresDatabase(DATABASE_URL, schema_name=schema_name)
    elif DB_TYPE == "mssql":
        DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
        return MSSQLDatabase(DATABASE_URL, schema_name=schema_name)
    else:
        raise ValueError(f"Unsupported database type: {DB_TYPE}")