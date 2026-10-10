import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def run_probe(tmp_path):
    """Run tests/contract/probe.py in a clean interpreter with exactly ``env`` set."""

    def run(mode: str, env: dict) -> dict:
        clean_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONHASHSEED": "0",
            **env,
        }
        completed = subprocess.run(
            [sys.executable, "-m", "tests.contract.probe", mode],
            cwd=tmp_path, env=clean_env, capture_output=True, text=True, timeout=180,
        )
        assert completed.returncode == 0, completed.stderr[-4000:]
        return json.loads(completed.stdout.strip().splitlines()[-1])

    return run


@pytest.fixture(scope="session")
def api_app():
    """app.api.main imported without a database (its import runs create_tables).

    Only the DDL call is patched: routers bind ``get_database`` at import, so
    patching that would leak a mock into every later test in the session.
    """
    from unittest import mock

    if "app.api.main" not in sys.modules:
        with mock.patch("app.database.postgres_database.PostgresDatabase.create_tables"):
            import app.api.main  # noqa: F401
    return sys.modules["app.api.main"].app
