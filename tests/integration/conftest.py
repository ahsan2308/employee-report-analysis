"""Fixtures for tests that run against the disposable Postgres in TEST_DATABASE_URL."""
import pytest
from sqlalchemy import text


def truncate_all_tables(database) -> None:
    import app.models  # noqa: F401  (registers every model on Base.metadata)
    from app.models.base import Base

    tables = ", ".join(
        f'"{table.schema}"."{table.name}"' if table.schema else f'"{table.name}"'
        for table in Base.metadata.sorted_tables
    )
    with database.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def database():
    from app.database import get_database

    db = get_database()
    db.create_tables()
    yield db
    db.engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _tables_exist(database):
    """Legacy suites assume the tables exist; a fresh CI database has none."""


@pytest.fixture
def clean_db(database):
    """Empty every application table before the test."""
    truncate_all_tables(database)
    return database


@pytest.fixture
def db_session(clean_db):
    session = clean_db.create_session()
    yield session
    session.close()


@pytest.fixture
def client(clean_db):
    """FastAPI TestClient over the real app (main.py runs create_tables on import)."""
    from fastapi.testclient import TestClient

    from app.api.main import app

    with TestClient(app) as test_client:
        yield test_client
