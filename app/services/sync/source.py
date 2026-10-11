"""The SQL Server the syncs read from: what is configured, and whether it can be reached."""
import time
from typing import Any, Dict

from app.core import settings
from app.core.logger import logger
from app.integrations.sqlserver.connector import create_sqlserver_connector


def sync_configuration() -> Dict[str, Any]:
    """The sync setup: SQL Server connection (tested now), allowed tables and columns, settings, schedule."""
    connector = create_sqlserver_connector()
    connection_status = "connected" if connector.test_connection() else "disconnected"
    sync_enabled = settings.sync_enabled()
    return {
        "sql_server": {
            "host": connector.server,
            "database": connector.database,
            "connection_status": connection_status
        },
        "allowed_tables": list(connector.get_allowed_tables()),
        "allowed_timestamp_columns": list(connector.get_allowed_timestamp_columns()),
        "sync_settings": {
            "max_batch_size": connector.max_batch_size,
            "error_threshold_percent": settings.sync_error_threshold_percent(),
            "default_chunk_size": settings.SYNC_BATCH_SIZE
        },
        "sync_schedule": {
            "incremental_sync": {
                "enabled": sync_enabled,
                "schedule": settings.SYNC_SCHEDULE_DESCRIPTION,
                "next_run": None  # Would need to query Celery beat for actual next run
            },
            "full_sync": {
                "enabled": False,
                "schedule": "Manual trigger only"
            }
        },
        "sync_enabled": sync_enabled
    }


def check_connection() -> Dict[str, Any]:
    """Try to reach SQL Server and time it; never raises (an error is reported in the result)."""
    try:
        connector = create_sqlserver_connector()
        
        start_time = time.time()
        connection_successful = connector.test_connection()
        connection_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        if not connection_successful:
            return {
                "status": "disconnected",
                "server": connector.server,
                "database": connector.database,
                "available_tables": [],
                "connection_time_ms": connection_time,
                "message": "Failed to connect to SQL Server"
            }
        
        return {
            "status": "connected",
            "server": connector.server,
            "database": connector.database,
            "available_tables": list(connector.get_allowed_tables()),
            "connection_time_ms": connection_time,
            "message": "Successfully connected to SQL Server"
        }
        
    except Exception as e:
        logger.error(f"Error testing SQL Server connection: {str(e)}")
        return {
            "status": "error",
            "server": "unknown",
            "database": "unknown",
            "available_tables": [],
            "connection_time_ms": 0,
            "message": f"Error: {str(e)}"
        }
