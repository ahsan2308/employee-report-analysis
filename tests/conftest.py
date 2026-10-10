"""Shared test setup.

This module runs before any ``app`` import, so it pins the environment that app
modules read at import time:

* A developer's ``.env`` is never loaded: ``load_env_from_file()`` uses
  ``override=True`` and would otherwise silently replace test settings.
* Database settings come from ``TEST_DATABASE_URL`` only. Without it they point
  at a closed port, so no test can reach a real database by accident.
* Celery uses in-memory transports, Qdrant uses a temporary local path.
"""
import os
import tempfile

import dotenv
from sqlalchemy.engine import make_url

import app.utils.env_loader as _env_loader

# Prime the lru_cache of load_env_from_file() without reading .env.
_env_loader.load_dotenv = lambda *args, **kwargs: False
_env_loader.load_env_from_file()
_env_loader.load_dotenv = dotenv.load_dotenv

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    _url = make_url(TEST_DATABASE_URL)
    os.environ.update(
        DB_HOST=_url.host or "localhost",
        DB_PORT=str(_url.port or 5432),
        DB_NAME=_url.database,
        DB_USER=_url.username or "",
        DB_PASSWORD=_url.password or "",
    )
else:
    os.environ.update(DB_HOST="127.0.0.1", DB_PORT="1", DB_NAME="no_database_configured")

os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["VECTOR_STORE_PATH"] = tempfile.mkdtemp(prefix="qdrant-test-")

import pytest  # noqa: E402

from tests.support.snapshots import SnapshotAsserter  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        help="Write snapshot files instead of comparing against them.",
    )


def pytest_collection_modifyitems(config, items):
    skip_no_db = pytest.mark.skip(reason="set TEST_DATABASE_URL to run integration tests")
    for item in items:
        if "/tests/integration/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(pytest.mark.integration)
            if not TEST_DATABASE_URL:
                item.add_marker(skip_no_db)


@pytest.fixture
def snapshot(request):
    """Compare a value against ``__snapshots__/<name>`` beside the test file."""
    update = request.config.getoption("--snapshot-update") or os.environ.get("SNAPSHOT_UPDATE") == "1"
    return SnapshotAsserter(request.path.parent / "__snapshots__", update=update)
