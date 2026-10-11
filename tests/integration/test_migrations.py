"""Alembic against a real database. Each test creates and drops its own database."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def scratch_database():
    admin_url = make_url(os.environ["TEST_DATABASE_URL"])
    name = f"migrations_{uuid.uuid4().hex[:8]}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    env = {
        **os.environ,
        "DB_HOST": admin_url.host or "localhost",
        "DB_PORT": str(admin_url.port or 5432),
        "DB_USER": admin_url.username or "",
        "DB_PASSWORD": admin_url.password or "",
        "DB_NAME": name,
        # migrations/env.py defaults SCHEMA_NAME to employee_reports (the models default to public).
        "SCHEMA_NAME": "employee_reports",
    }
    yield env
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()


def run(args, env):
    return subprocess.run(args, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=300)


def _tables(env):
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(database=env["DB_NAME"])
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names(schema="employee_reports"))
    finally:
        engine.dispose()


def test_upgrade_head_builds_an_empty_database(scratch_database):
    """B16 fixed: the history cannot be replayed from nothing, so `upgrade head` builds the current schema."""
    result = run([sys.executable, "-m", "alembic", "upgrade", "head"], scratch_database)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Empty database: creating the current schema and stamping head" in result.stdout

    heads = run([sys.executable, "-m", "alembic", "heads"], scratch_database)
    current = run([sys.executable, "-m", "alembic", "current"], scratch_database)
    assert heads.stdout.split()[0] in current.stdout

    check = run([sys.executable, "-m", "alembic", "check"], scratch_database)
    assert check.returncode == 0, check.stderr[-2000:]

    again = run([sys.executable, "-m", "alembic", "upgrade", "head"], scratch_database)
    assert again.returncode == 0, again.stderr[-2000:]
    assert "Empty database" not in again.stdout


def test_stamp_head_on_an_empty_database_creates_no_tables(scratch_database):
    result = run([sys.executable, "-m", "alembic", "stamp", "head"], scratch_database)
    assert result.returncode == 0, result.stderr[-2000:]
    assert _tables(scratch_database) == {"alembic_version"}


def test_upgrade_to_an_older_revision_still_replays_history(scratch_database):
    """Only `upgrade head` builds from scratch; other targets run the revisions (which need the base tables)."""
    result = run([sys.executable, "-m", "alembic", "upgrade", "65a702f08ade"], scratch_database)
    assert result.returncode != 0
    assert 'relation "employee_reports.reports" does not exist' in result.stderr


def test_models_match_migration_head(scratch_database):
    """Tables built by create_all() and stamped at head show no autogenerate drift."""
    # create_all() does not create the schema; migrations/env.py does (CREATE SCHEMA IF NOT EXISTS).
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(database=scratch_database["DB_NAME"])
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA employee_reports"))
    engine.dispose()

    create = run([sys.executable, "-c", "from app.db.database import get_database; get_database().create_tables()"], scratch_database)
    assert create.returncode == 0, create.stderr[-2000:]

    stamp = run([sys.executable, "-m", "alembic", "stamp", "head"], scratch_database)
    assert stamp.returncode == 0, stamp.stderr[-2000:]

    check = run([sys.executable, "-m", "alembic", "check"], scratch_database)
    assert check.returncode == 0, check.stderr[-2000:]
    assert "No new upgrade operations detected." in check.stdout + check.stderr


# --------------------------------------------------------------------------- python -m app.db.migrate (run by the API's start script)

def _migrate(env):
    return run([sys.executable, "-m", "app.db.migrate"], env)


def _engine(env):
    return create_engine(make_url(os.environ["TEST_DATABASE_URL"]).set(database=env["DB_NAME"]))


def _version(env, schema="employee_reports"):
    engine = _engine(env)
    try:
        with engine.connect() as connection:
            return connection.execute(text(f'SELECT version_num FROM "{schema}".alembic_version')).scalar()
    finally:
        engine.dispose()


def _head(env):
    return run([sys.executable, "-m", "alembic", "heads"], env).stdout.split()[0]


def test_migrate_builds_an_empty_database_at_head(scratch_database):
    result = _migrate(scratch_database)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Migrating schema 'employee_reports' (empty) to head" in result.stdout
    assert _version(scratch_database) == _head(scratch_database)
    assert "csv_import_jobs" in _tables(scratch_database)


def test_migrate_upgrades_a_tracked_database(scratch_database):
    """A database at the 4.0.0 head gets the partial import status migration."""
    built = _migrate(scratch_database)
    assert built.returncode == 0, built.stderr[-2000:]
    downgrade = run([sys.executable, "-m", "alembic", "downgrade", "3379963e0751"], scratch_database)
    assert downgrade.returncode == 0, downgrade.stderr[-2000:]

    result = _migrate(scratch_database)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "(tracked)" in result.stdout
    assert _version(scratch_database) == _head(scratch_database)


def test_migrate_leaves_an_untracked_database_alone(scratch_database):
    """Tables built by the app itself (create_all) and never stamped: no guessing, the API still starts."""
    engine = _engine(scratch_database)
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA employee_reports"))
    engine.dispose()
    create = run([sys.executable, "-c", "from app.db.database import get_database; get_database().create_tables()"],
                 scratch_database)
    assert create.returncode == 0, create.stderr[-2000:]

    result = _migrate(scratch_database)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "has tables but no alembic_version" in result.stderr
    assert "alembic_version" not in _tables(scratch_database)


def test_migrate_uses_the_schema_the_app_uses(scratch_database):
    """migrations/env.py alone defaults to employee_reports; the app (and so migrate) defaults to public."""
    env = {k: v for k, v in scratch_database.items() if k != "SCHEMA_NAME"}
    result = _migrate(env)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Migrating schema 'public' (empty) to head" in result.stdout
    assert _version(env, schema="public") == _head(scratch_database)


def test_migrate_fails_when_the_database_is_unreachable(scratch_database):
    env = dict(scratch_database, DB_PORT="1")
    result = run([sys.executable, "-c",
                  "import app.db.migrate as m; m.CONNECT_ATTEMPTS = 1; raise SystemExit(m.main())"], env)
    assert result.returncode == 1
    assert "Cannot reach the database" in result.stderr
