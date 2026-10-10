"""Configuration resolution: env vars > config/config.yaml > code defaults.

Each scenario runs in a fresh interpreter because most settings are read at
import time. The snapshots are the configuration contract the refactor must keep.
"""
import pytest

FULL_OVERRIDES = {
    "DB_TYPE": "postgres", "DB_USER": "u", "DB_PASSWORD": "p@ss", "DB_HOST": "db.internal",
    "DB_PORT": "6543", "DB_NAME": "reports", "SCHEMA_NAME": "employee_reports",
    "LLM_PROVIDER": "vllm", "EMBEDDING_PROVIDER": "vllm", "EMBEDDING_USE_PREFIX": "true",
    "OLLAMA_BASE_URL": "http://ollama:11434", "OLLAMA_MODEL": "llama3.1:70b", "OLLAMA_API_KEY": "ok",
    "OLLAMA_EMBEDDING_MODEL": "nomic", "VLLM_BASE_URL": "http://vllm:8000", "VLLM_MODEL": "m",
    "VLLM_API_KEY": "vk", "VLLM_EMBEDDING_BASE_URL": "http://vllm-emb:8001", "VLLM_EMBEDDING_MODEL": "e",
    "VECTOR_STORE_TYPE": "QDRANT", "VECTOR_STORE_HOST": "qdrant", "VECTOR_STORE_PORT": "6334",
    "VECTOR_STORE_PATH": "/qdrant/storage", "VECTOR_STORE_MODE": "server",
    "REDIS_HOST": "redis", "CELERY_BROKER_URL": "redis://redis:6379/1",
    "CELERY_RESULT_BACKEND": "redis://redis:6379/2", "CELERY_TASK_SERIALIZER": "json",
    "CELERY_ACCEPT_CONTENT": '["json", "pickle"]', "CELERY_RESULT_SERIALIZER": "json",
    "CELERY_TASK_TRACK_STARTED": "false", "CELERY_TASK_TIME_LIMIT": "900",
    "CELERY_WORKER_CONCURRENCY": "8", "CELERY_TASK_IGNORE_RESULT": "true",
    "CELERY_RESULT_EXPIRES": "60", "CELERY_TASK_PACKAGES": "app.tasks, app.extra",
    "SYNC_ENABLED": "false",
}


def test_defaults(run_probe, snapshot):
    snapshot("config_defaults", run_probe("config", {}))


def test_full_env_overrides(run_probe, snapshot):
    snapshot("config_full_overrides", run_probe("config", FULL_OVERRIDES))


@pytest.mark.parametrize(
    "accept_content", ["json", "[json", '["json","yaml"]'], ids=["single", "malformed", "list"]
)
def test_celery_accept_content_parsing(run_probe, snapshot, request, accept_content):
    result = run_probe("config", {"CELERY_ACCEPT_CONTENT": accept_content})
    snapshot(f"celery_accept_content_{request.node.callspec.id}", result["celery"]["settings"]["accept_content"])


@pytest.mark.known_bug("B8")
def test_bare_key_env_vars_override_yaml_sections(run_probe, snapshot):
    """ConfigProvider.get('host', section='redis') reads the env var HOST, etc."""
    collisions = {
        "HOST": "collides-host", "PORT": "1", "MODEL": "collides-model", "MODE": "server",
        "TYPE": "qdrant", "ENABLED": "false", "COLLECTION_NAME": "other_collection",
        "STORAGE_PATH": "/elsewhere", "EMBEDDING_MODEL": "other-embed",
    }
    snapshot("config_bare_key_collisions", run_probe("config", collisions))


@pytest.mark.parametrize("db_type", ["mssql", "oracle"])
def test_database_type_selection(run_probe, snapshot, db_type):
    snapshot(f"get_database_{db_type}", run_probe("config", {"DB_TYPE": db_type})["get_database"])
