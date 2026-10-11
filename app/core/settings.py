"""Application settings, resolved once at import.

Every value keeps the exact precedence it had in the module that used to read
it: environment variable (after loading the project's .env) > config/config.yaml
(through ConfigProvider) > code default. The modules that used these values
re-export them under their original names.

Celery settings stay in app/worker/celery_app.py (except the task time
limit, which other modules need), and the SQL Server connector reads its
SQLSERVER_* variables when a connection is created. The sync_* functions read
their variables on each call, as their callers always have.
"""
import os

from app.core.config_provider import get_config_provider
from app.utils.env_loader import load_env_from_file

load_env_from_file()
config = get_config_provider()

# --- Database (app.db) ---
DB_TYPE = os.getenv("DB_TYPE", "postgres").lower()  # Default to PostgreSQL
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
DB_HOST = os.getenv("DB_HOST", "localhost")  # Use 'db' if running in Docker
DB_PORT = os.getenv("DB_PORT", "5432")  # Default PostgreSQL port
DB_NAME = os.getenv("DB_NAME", "employee_reports")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "public")

# --- LLM and embedding providers (app.integrations.providers) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
EMBEDDING_USE_PREFIX = os.getenv("EMBEDDING_USE_PREFIX", "false").lower() == "true"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", None)

OLLAMA_EMBEDDING_BASE_URL = os.getenv("OLLAMA_EMBEDDING_BASE_URL", OLLAMA_BASE_URL)
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_EMBEDDING_API_KEY = os.getenv("OLLAMA_EMBEDDING_API_KEY", OLLAMA_API_KEY)

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", None)

VLLM_EMBEDDING_BASE_URL = os.getenv("VLLM_EMBEDDING_BASE_URL", "http://localhost:8001")
VLLM_EMBEDDING_MODEL = os.getenv("VLLM_EMBEDDING_MODEL", "BAAI/bge-m3")
VLLM_EMBEDDING_API_KEY = os.getenv("VLLM_EMBEDDING_API_KEY", VLLM_API_KEY)

# Default models used by app.services.llm_service and app.services.embedding_service
if LLM_PROVIDER == "vllm":
    LLM_DEFAULT_MODEL = os.getenv("VLLM_MODEL") or config.get("model", "meta-llama/Meta-Llama-3.1-8B-Instruct", section="llm")
else:
    LLM_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL") or config.get("model", "llama3.1:8b", section="llm")

if EMBEDDING_PROVIDER == "vllm":
    EMBEDDING_DEFAULT_MODEL = os.getenv("VLLM_EMBEDDING_MODEL") or config.get("embedding_model", "BAAI/bge-m3", section="llm")
else:
    EMBEDDING_DEFAULT_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL") or config.get("embedding_model", "bge-m3", section="llm")

# --- Vector store (app.integrations.vector_store, app.services.vector_store_service) ---
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", config.get("type", "qdrant", section="vector_db")).lower()
VECTOR_STORE_HOST = os.getenv("VECTOR_STORE_HOST", config.get("host", "localhost", section="vector_db"))
VECTOR_STORE_PORT = os.getenv("VECTOR_STORE_PORT", config.get("port", "6333", section="vector_db"))
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", config.get("storage_path", "./qdrant_data", section="vector_db"))
VECTOR_STORE_MODE = os.getenv("VECTOR_STORE_MODE", config.get("mode", "local", section="vector_db"))

COLLECTION_NAME = config.get("collection_name", "employee_reports", section="vector_db")
VECTOR_BATCH_MODE = config.get("enabled", True, section="vector_db.batch_processing")
VECTOR_EMBEDDING_BATCH_SIZE = config.get("embedding_batch_size", 256, section="vector_db.batch_processing")
VECTOR_UPSERT_BATCH_SIZE = config.get("upsert_batch_size", 1000, section="vector_db.batch_processing")
VECTOR_BATCH_MAX_RETRIES = config.get("max_attempts", 3, section="vector_db.batch_processing.retry")

# --- Analysis context limits (app.tasks.analysis_tasks) ---
VECTOR_SEARCH_HNSW_EF = config.get("hnsw_ef", 128, section="vector_db.search")
MAX_CONTENT_ITEMS_PER_ENTITY_FOR_WEEKLY_ANALYSIS = config.get("max_content_items_per_entity_for_weekly_analysis", 10, section="vector_db.search")
MAX_CONTENT_ITEMS_PER_ENTITY_FOR_MONTHLY_ANALYSIS = config.get("max_content_items_per_entity_for_monthly_analysis", 10, section="vector_db.search")
MAX_CONTENT_ITEMS_PER_ENTITY_FOR_QUARTERLY_ANALYSIS = config.get("max_content_items_per_entity_for_quarterly_analysis", 10, section="vector_db.search")
MAX_CONTENT_ITEM_LENGTH_WEEKLY = config.get("max_content_item_length_weekly", 300, section="vector_db.search")
MAX_CONTENT_ITEM_LENGTH_MONTHLY = config.get("max_content_item_length_monthly", 250, section="vector_db.search")
MAX_CONTENT_ITEM_LENGTH_QUARTERLY = config.get("max_content_item_length_quarterly", 200, section="vector_db.search")

# --- Celery task limits (app.worker.celery_app, app.services.task_service) ---
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT") or config.get("task_time_limit", 1800, section="celery"))

# --- Sync (app.services.sync_service, app.api.sync_routes, app.worker.celery_app) ---
SYNC_BATCH_SIZE = 1000  # rows read from SQL Server per batch
SYNC_STALE_AFTER_MINUTES = 60  # a sync PENDING/RUNNING longer than this is marked failed

# The weekly incremental sync run by Celery beat (crontab fields; day 0 is Sunday)
SYNC_SCHEDULE_DAY_OF_WEEK = 1
SYNC_SCHEDULE_HOUR = 2
SYNC_SCHEDULE_MINUTE = 0
_WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
SYNC_SCHEDULE_DESCRIPTION = (
    f"{_WEEKDAYS[SYNC_SCHEDULE_DAY_OF_WEEK]} "
    f"{(SYNC_SCHEDULE_HOUR % 12) or 12}:{SYNC_SCHEDULE_MINUTE:02d} {'AM' if SYNC_SCHEDULE_HOUR < 12 else 'PM'}"
)


def sync_enabled() -> bool:
    """SYNC_ENABLED (default true): whether the weekly sync is scheduled."""
    return os.getenv("SYNC_ENABLED", "true").lower() == "true"


def sync_error_threshold_percent() -> float:
    """SYNC_ERROR_THRESHOLD_PERCENT (default 10.0); raises ValueError when not a number."""
    return float(os.getenv("SYNC_ERROR_THRESHOLD_PERCENT", "10.0"))


# --- API (app.api.main) ---
# Comma-separated origins allowed by CORS; "*" (the default) allows any origin
CORS_ALLOW_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()]
