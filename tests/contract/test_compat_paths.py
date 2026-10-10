"""Old import paths kept during the Phase 3 restructuring.

Alias modules are the moved module itself (patches on either path hit the
same code). Re-export modules expose the same objects as their new home.
Removing any of these is a separate, approved step.
"""
import importlib

import pytest

ALIASES = {
    "app.model_host.ollama": "app.integrations.llm.ollama",
    "app.model_host.vllm": "app.integrations.llm.vllm",
    "app.model_host.ollama_embedding": "app.integrations.embeddings.ollama",
    "app.model_host.vllm_embedding": "app.integrations.embeddings.vllm",
    "app.base.base_llm": "app.integrations.llm.base",
    "app.base.base_embedding": "app.integrations.embeddings.base",
    "app.base.base_vector_store": "app.integrations.vector_store.base",
    "app.vector_store.qdrant_provider": "app.integrations.vector_store.qdrant",
    "app.database.sqlserver_connector": "app.integrations.sqlserver.connector",
    "app.base.base_csv_processor": "app.services.csv.processors.base",
}

REEXPORTS = {
    "app.database": "app.db.database",
    "app.database.postgres_database": "app.db.postgres",
    "app.database.mssql_database": "app.db.mssql",
    "app.models.base": "app.db.base",
    "app.base.base_db": "app.db.base_database",
    "app.model_host": "app.integrations.providers",
    "app.vector_store": "app.integrations.vector_store",
    "app.services.db_service": None,  # spread over app.repositories.* and app.domain.periods
    "app.services.additional_services": None,  # spread over app.services.analysis.*
    "app.schemas.csv_import_schema": None,  # row models live in app.services.csv.row_models
}


@pytest.mark.parametrize("old,new", sorted(ALIASES.items()))
def test_alias_is_the_moved_module(old, new):
    assert importlib.import_module(old) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", sorted(REEXPORTS.items()))
def test_reexported_names_are_the_same_objects(old, new):
    old_module = importlib.import_module(old)
    names = [n for n in vars(old_module) if not n.startswith("__")]
    assert names, old
    for name in names:
        value = getattr(old_module, name)
        home = importlib.import_module(new) if new else importlib.import_module(getattr(value, "__module__", old))
        if hasattr(home, name):
            assert getattr(home, name) is value, f"{old}.{name}"
