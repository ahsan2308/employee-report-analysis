from app.db.postgres import PostgresDatabase
from app.db.mssql import MSSQLDatabase

from app.core.settings import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_TYPE, DB_USER
from app.db.base import schema_name

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