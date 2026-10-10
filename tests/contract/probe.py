"""Subprocess probe used by the contract tests.

Usage: python -m tests.contract.probe <config|imports>

Runs in a fresh interpreter so import-time configuration is resolved from the
environment the test passes in, never from the test session or a developer's
.env. Prints one JSON document on stdout.
"""
import importlib
import io
import json
import os
import pkgutil
import sys
import traceback
from contextlib import redirect_stdout

import app.utils.env_loader as env_loader

env_loader.load_dotenv = lambda *args, **kwargs: False
env_loader.load_env_from_file()

CONFIG_MODULES = [
    "app.db.postgres",
    "app.db.base",
    "app.integrations.providers",
    "app.integrations.vector_store",
    "app.services.vector_store_service",
    "app.services.llm_service",
    "app.services.embedding_service",
    "app.db.database",
    "app.tasks.analysis_tasks",
    "app.worker.celery_app",
]


def _public_settings(module) -> dict:
    """Module-level UPPER_CASE names holding plain values (the resolved settings)."""
    plain = (str, int, float, bool, type(None), list, tuple, dict)
    return {
        name: value
        for name, value in sorted(vars(module).items())
        if name.isupper() and isinstance(value, plain)
    }


def probe_config() -> dict:
    result = {}
    for name in CONFIG_MODULES:
        importlib.import_module(name)
        result[name] = _public_settings(sys.modules[name])

    # app.worker re-exports the Celery instance under the submodule's name.
    celery_module = sys.modules["app.worker.celery_app"]

    conf = celery_module.celery_app.conf
    result["celery"] = {
        "broker_url": celery_module.broker_url,
        "result_backend": celery_module.result_backend,
        "settings": celery_module.celery_settings,
        "task_packages": celery_module.task_packages,
        "beat_schedule": {key: {k: str(v) for k, v in entry.items()} for key, entry in conf.beat_schedule.items()},
    }

    import app.db.database as database

    try:
        db = database.get_database()
        result["get_database"] = {
            "class": type(db).__name__,
            "url": db.engine.url.render_as_string(hide_password=False),
            "schema_name": db.schema_name,
        }
    except Exception as exc:  # characterize unsupported DB_TYPE
        result["get_database"] = {"error": f"{type(exc).__name__}: {exc}"}

    from app.core.config_provider import ConfigProvider

    provider = ConfigProvider()
    lookups = [
        ("host", None, "redis"), ("port", None, "redis"), ("host", None, "vector_db"),
        ("port", "6333", "vector_db"), ("model", None, "llm"), ("mode", "local", "vector_db"),
        ("type", "qdrant", "vector_db"), ("enabled", True, "vector_db.batch_processing"),
        ("collection_name", None, "vector_db"), ("hnsw_ef", 128, "vector_db.search"),
        ("max_attempts", 3, "vector_db.batch_processing.retry"), ("missing_key", "fallback", "vector_db"),
        ("missing_key", "fallback", "no.such.section"), ("database", None, None),
    ]
    result["config_provider"] = {f"{section}:{key}": provider.get(key, default, section=section) for key, default, section in lookups}
    return result


def probe_imports() -> dict:
    import app

    outcomes = {}
    names = sorted(info.name for info in pkgutil.walk_packages(app.__path__, "app."))
    for name in names:
        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                importlib.import_module(name)
            outcomes[name] = "ok"
        except BaseException as exc:  # noqa: BLE001 - recording the outcome is the point
            message = str(exc).splitlines()[0] if str(exc) else ""
            if "connection to server" in message:
                message = "<database connection refused>"  # wording depends on host/IPv4/IPv6
            outcomes[name] = f"{type(exc).__name__}: {message}"
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(app.__file__)))
            outcomes[name] = outcomes[name].replace(repo_root, "<repo>")
        if captured.getvalue():
            outcomes[name] += " [prints to stdout at import]"
    return outcomes


def probe_worker_tasks() -> dict:
    """Tasks a worker started with `celery -A app.worker.celery_app` registers.

    The worker imports only the -A module, then runs the loader's default
    module import (where autodiscovery happens) before consuming.
    """
    importlib.import_module("app.worker.celery_app")
    app_ = sys.modules["app.worker.celery_app"].celery_app  # app.worker shadows the submodule name
    app_.loader.import_default_modules()
    return {"tasks": sorted(name for name in app_.tasks if not name.startswith("celery."))}


def probe_tables_after_database_import() -> dict:
    """Tables registered when a script imports only the database layer (e.g. to call create_tables())."""
    database = importlib.import_module("app.db.database")
    base = database.get_database().Base  # builds an engine, does not connect
    return {"tables": sorted(base.metadata.tables)}


PROBES = {
    "config": probe_config,
    "imports": probe_imports,
    "worker_tasks": probe_worker_tasks,
    "tables_after_database_import": probe_tables_after_database_import,
}


if __name__ == "__main__":
    mode = sys.argv[1]
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()  # import-time prints must not corrupt the JSON
    try:
        data = PROBES[mode]()
    except Exception:
        sys.stdout = real_stdout
        traceback.print_exc(file=sys.stderr)
        raise
    sys.stdout = real_stdout
    print(json.dumps(data, default=str, sort_keys=True))
