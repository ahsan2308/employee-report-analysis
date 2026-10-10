from celery import Celery
import os
import json
import platform
import socket

from app.core.config_provider import get_config_provider
from app.core.logger import logger  # Use the application's logger
from celery.schedules import crontab

# Get configuration
config = get_config_provider()

# Get Redis container name with environment variable priority
REDIS_HOST = os.getenv('REDIS_HOST') or config.get('host', 'redis-container', section='redis')

# Detect environment
IS_WINDOWS = platform.system() == 'Windows'

# Helper function to check if we can resolve a hostname
def can_resolve_hostname(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False

# Determine Redis connection info with hostname resolution check
def get_redis_connection_url():
    # First check environment variables
    broker_url = os.getenv('CELERY_BROKER_URL')
    
    # If not set in env, get from config
    if not broker_url:
        broker_url = config.get('broker_url', section='celery')
    
    # Special handling for Windows with Docker
    if IS_WINDOWS and REDIS_HOST in broker_url:
        logger.info(f"Running on Windows. Redis Docker container hostname detected: {REDIS_HOST}")
        
        # Check if hostname is resolvable (inside Docker network)
        if not can_resolve_hostname(REDIS_HOST):
            logger.info(f"Cannot resolve {REDIS_HOST}, using localhost instead")
            broker_url = broker_url.replace(REDIS_HOST, 'localhost')
    
    return broker_url

# Do the same for result backend with configuration-based host name
def get_result_backend_url():
    # First check environment variables
    result_backend = os.getenv('CELERY_RESULT_BACKEND')
    
    # If not set in env, get from config
    if not result_backend:
        result_backend = config.get('result_backend', section='celery')
    
    # Special handling for Windows with Docker
    if IS_WINDOWS and REDIS_HOST in result_backend:
        # Check if hostname is resolvable (inside Docker network)
        if not can_resolve_hostname(REDIS_HOST):
            logger.info(f"Cannot resolve {REDIS_HOST}, using localhost for result backend")
            result_backend = result_backend.replace(REDIS_HOST, 'localhost')
    
    return result_backend

# Get the appropriate connection URLs
broker_url = get_redis_connection_url()
result_backend = get_result_backend_url()

logger.info(f"Initializing Celery with broker: {broker_url}")
logger.info(f"Result backend: {result_backend}")

# Initialize Celery app
celery_app = Celery(
    "employee_report_analysis",
    broker=broker_url,
    backend=result_backend,
)

# Parse accept_content properly to ensure it's a list
def parse_accept_content():
    accept_content_env = os.getenv('CELERY_ACCEPT_CONTENT')
    if accept_content_env:
        # Try to parse as JSON if it's a string representation of a list
        if accept_content_env.startswith('[') and accept_content_env.endswith(']'):
            try:
                return json.loads(accept_content_env)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse CELERY_ACCEPT_CONTENT: {accept_content_env}")
                return ['json']
        # Handle case where it's a single string value
        return [accept_content_env]
    
    # Use config value or default
    config_value = config.get('accept_content', section='celery')
    # If config value is already a list, use it
    if isinstance(config_value, list):
        return config_value
    # If it's a single string, wrap it in a list
    if isinstance(config_value, str):
        return [config_value]
    # Default
    return ['json']

# Configure Celery settings
celery_settings = {
    'task_serializer': os.getenv('CELERY_TASK_SERIALIZER') or config.get('task_serializer', 'json', section='celery'),
    'accept_content': parse_accept_content(),
    'result_serializer': os.getenv('CELERY_RESULT_SERIALIZER') or config.get('result_serializer', 'json', section='celery'),
    'task_track_started': os.getenv('CELERY_TASK_TRACK_STARTED', 'true').lower() == 'true',
    'task_time_limit': int(os.getenv('CELERY_TASK_TIME_LIMIT') or config.get('task_time_limit', 1800, section='celery')),
    'worker_concurrency': int(os.getenv('CELERY_WORKER_CONCURRENCY') or config.get('worker_concurrency', 2, section='celery')),
    
    # task_ignore_result: When True, no results are stored. When False, results are stored in result backend
    # Default to False so we can track task status and results
    'task_ignore_result': os.getenv('CELERY_TASK_IGNORE_RESULT', 'false').lower() == 'true' 
        if os.getenv('CELERY_TASK_IGNORE_RESULT') 
        else config.get('task_ignore_result', False, section='celery'),
    
    # result_expires: Number of seconds after which task results expire (default: 1 day)
    'result_expires': int(os.getenv('CELERY_RESULT_EXPIRES') or config.get('result_expires', 86400, section='celery')),
}

# The soft limit raises SoftTimeLimitExceeded inside the task, so its error
# handler can mark the run FAILED before the hard limit kills the process.
_soft_time_limit = os.getenv('CELERY_TASK_SOFT_TIME_LIMIT') or config.get('task_soft_time_limit', None, section='celery')
celery_settings['task_soft_time_limit'] = (
    int(_soft_time_limit) if _soft_time_limit
    else celery_settings['task_time_limit'] - min(60, celery_settings['task_time_limit'] // 10)
)

# Windows-specific settings
if IS_WINDOWS:
    celery_settings['worker_pool'] = 'solo'
    logger.info("Windows detected: Using 'solo' worker pool for compatibility")

# Log the settings
for key, value in celery_settings.items():
    logger.info(f"Celery setting {key}: {value}")

# Apply settings
celery_app.conf.update(celery_settings)

# Parse task packages from env var or config
def parse_task_packages():
    # Check environment variable first
    task_packages_env = os.getenv('CELERY_TASK_PACKAGES')
    if task_packages_env:
        # Try to parse as JSON list
        if task_packages_env.startswith('[') and task_packages_env.endswith(']'):
            try:
                return json.loads(task_packages_env)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse CELERY_TASK_PACKAGES: {task_packages_env}")
                return ['app.tasks']
        # Handle comma-separated format
        return [pkg.strip() for pkg in task_packages_env.split(',')]
    
    # Fall back to config
    return config.get('task_packages', ['app.tasks'], section='celery')

# Auto-discover tasks using configuration with env var priority
task_packages = parse_task_packages()
logger.info(f"Auto-discovering tasks in packages: {task_packages}")
celery_app.autodiscover_tasks(
    packages=task_packages,
    related_name=None,
)

# Check if sync is enabled from environment variable
SYNC_ENABLED = os.getenv('SYNC_ENABLED', 'true').lower() == 'true'

# Configure beat schedule
beat_schedule = {
    # ...existing schedules (analysis tasks, etc.)...
}

# Add sync schedules only if sync is enabled
if SYNC_ENABLED:
    logger.info("SYNC_ENABLED=true: Adding scheduled sync tasks to beat schedule")
    
    # PRODUCTION: Weekly schedule (Monday 2:00 AM)
    beat_schedule['sync-incremental-weekly'] = {
        'task': 'sync.incremental',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2:00 AM
        'options': {'queue': 'sync'}
    }
    
    # TEST: Uncomment to run every minute for testing
    # beat_schedule['sync-incremental-weekly'] = {
    #     'task': 'sync.incremental',
    #     'schedule': crontab(minute='*'),  # Every minute
    #     'options': {'queue': 'sync'}
    # }

# Apply the beat schedule
celery_app.conf.beat_schedule = beat_schedule

# Optional: Define task routing to use dedicated sync queue
celery_app.conf.task_routes = {
    'sync.*': {'queue': 'sync'},
    'app.tasks.analysis_tasks.*': {'queue': 'analysis'},
    'app.tasks.import_tasks.*': {'queue': 'imports'},
    'csv_import.process': {'queue': 'imports'},  
}
