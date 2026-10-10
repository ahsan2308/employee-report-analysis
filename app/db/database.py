import os

from app.db.postgres import PostgresDatabase
from app.db.mssql import MSSQLDatabase

from app.core.settings import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_TYPE, DB_USER
from app.db.base import schema_name

# One database object, and so one engine and connection pool, per process and URL.
# Keyed by process ID: a forked child (a Celery worker, a gunicorn worker) must not
# use the parent's pooled connections, so it builds its own engine.
_databases = {}


def get_database():
    # Construct the database URL dynamically
    if DB_TYPE == "postgres":
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        database_class = PostgresDatabase
    elif DB_TYPE == "mssql":
        DATABASE_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
        database_class = MSSQLDatabase
    else:
        raise ValueError(f"Unsupported database type: {DB_TYPE}")

    pid = os.getpid()
    _forget_inherited_databases(pid)
    key = (pid, database_class, DATABASE_URL)
    database = _databases.get(key)
    if database is None:
        database = database_class(DATABASE_URL, schema_name=schema_name)
        _databases[key] = database
    return database


def _forget_inherited_databases(pid: int) -> None:
    """Drop databases created by a parent process without closing its connections."""
    for key in [key for key in _databases if key[0] != pid]:
        # close=False: the sockets belong to the parent, which keeps using them
        _databases.pop(key).engine.dispose(close=False)
