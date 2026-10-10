"""Alembic against a real database. Each test creates and drops its own database."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
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


@pytest.mark.known_bug("B16")
def test_upgrade_from_empty_database_fails_at_first_revision(scratch_database):
    result = run([sys.executable, "-m", "alembic", "upgrade", "head"], scratch_database)
    assert result.returncode != 0
    assert 'relation "employee_reports.reports" does not exist' in result.stderr
    assert "-> 65a702f08ade" in result.stderr


def test_models_match_migration_head(scratch_database):
    """Tables built by create_all() and stamped at head show no autogenerate drift."""
    # create_all() does not create the schema; migrations/env.py does (CREATE SCHEMA IF NOT EXISTS).
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(database=scratch_database["DB_NAME"])
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA employee_reports"))
    engine.dispose()

    create = run([sys.executable, "-c", "from app.database import get_database; get_database().create_tables()"], scratch_database)
    assert create.returncode == 0, create.stderr[-2000:]

    stamp = run([sys.executable, "-m", "alembic", "stamp", "head"], scratch_database)
    assert stamp.returncode == 0, stamp.stderr[-2000:]

    check = run([sys.executable, "-m", "alembic", "check"], scratch_database)
    assert check.returncode == 0, check.stderr[-2000:]
    assert "No new upgrade operations detected." in check.stdout + check.stderr
