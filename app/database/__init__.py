"""Compatibility re-exports; the implementation lives in app.db.database."""
from app.db.database import (  # noqa: F401
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_TYPE,
    DB_USER,
    MSSQLDatabase,
    PostgresDatabase,
    get_database,
    schema_name,
)
