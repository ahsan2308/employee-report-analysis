"""
Bring the database schema up to date: `python -m app.db.migrate`.

The API's start script runs this before uvicorn, so a deploy applies new
migrations by itself. It always migrates the schema the app uses
(settings.SCHEMA_NAME); migrations/env.py on its own defaults to
employee_reports.

- A database tracked by Alembic (it has alembic_version) is upgraded to head.
- An empty database is built at head (migrations/env.py creates the current
  schema and stamps it).
- A database with tables but no alembic_version was built by the app itself
  (create_all) and cannot be placed in the revision history safely, so it is
  left alone, with a message saying how to start tracking it.

Exits 1 when the database cannot be reached or a migration fails, so the API
does not start against a schema it does not expect.
"""
import os
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app.core import settings
from app.db.database import get_database

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECT_ATTEMPTS = 15  # the database container may still be starting
CONNECT_WAIT_SECONDS = 2


def _alembic_config() -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    return config


def _schema_state(engine, schema: str) -> str:
    """'tracked', 'empty' or 'untracked' (tables but no alembic_version)."""
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            inspector = inspect(engine)
            if inspector.has_table("alembic_version", schema=schema):
                return "tracked"
            return "untracked" if inspector.get_table_names(schema=schema) else "empty"
        except OperationalError as e:
            if attempt == CONNECT_ATTEMPTS:
                raise
            print(f"Database not reachable yet ({attempt}/{CONNECT_ATTEMPTS}): {str(e).splitlines()[0]}")
            time.sleep(CONNECT_WAIT_SECONDS)


def main() -> int:
    schema = settings.SCHEMA_NAME
    # migrations/env.py reads SCHEMA_NAME; give it the schema the app uses
    os.environ["SCHEMA_NAME"] = schema
    try:
        state = _schema_state(get_database().engine, schema)
    except OperationalError as e:
        print(f"Cannot reach the database to run migrations: {e}", file=sys.stderr)
        return 1

    if state == "untracked":
        print(
            f"Schema '{schema}' has tables but no alembic_version, so its migration state is unknown; "
            "skipping migrations. To start tracking it, run `alembic stamp <revision>` with the revision "
            "its tables match (`alembic history` lists them), then restart.",
            file=sys.stderr,
        )
        return 0

    print(f"Migrating schema '{schema}' ({state}) to head")
    try:
        command.upgrade(_alembic_config(), "head")
    except Exception as e:  # noqa: BLE001 - any failure must stop the start
        print(f"Migration failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
