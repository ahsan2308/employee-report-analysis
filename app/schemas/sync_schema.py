"""
Pydantic schemas for SQL Server sync API responses.

These schemas define the structure of API responses for sync operations,
ensuring type safety and automatic validation.
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SyncTypeEnum(str, Enum):
    """Valid sync types."""
    EMPLOYEE_REPORTS = "employee_reports"
    VISION_DATA = "vision_data"
    JOB_DESCRIPTIONS = "job_descriptions"


class SyncStatusEnum(str, Enum):
    """Valid sync statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SyncTriggerResponse(BaseModel):
    """Response when triggering a sync operation."""
    sync_id: UUID4
    task_id: str
    sync_type: SyncTypeEnum
    status: SyncStatusEnum
    is_full_sync: bool
    triggered_at: datetime
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                "task_id": "0030c389-1350-485c-b150-6e6a6e5cd210",
                "sync_type": "employee_reports",
                "status": "pending",
                "is_full_sync": False,
                "triggered_at": "2025-11-24T13:13:19Z",
                "message": "Employee reports sync started successfully"
            }
        }


class FullSyncTriggerResponse(BaseModel):
    """Response when triggering a full sync (both types)."""
    sync_type: str = Field(default="full")
    employee_reports_sync_id: UUID4
    vision_data_sync_id: UUID4
    job_descriptions_sync_id: UUID4
    task_id: str
    status: SyncStatusEnum
    triggered_at: datetime
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_type": "full",
                "employee_reports_sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                "vision_data_sync_id": "0c563781-7366-465d-931d-874b98af6277",
                "job_descriptions_sync_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "task_id": "full-sync-task-id",
                "status": "pending",
                "triggered_at": "2025-11-24T13:13:19Z",
                "message": "Full sync (both types) started successfully"
            }
        }


class SyncProgressMetrics(BaseModel):
    """Progress metrics for an ongoing or completed sync."""
    records_queried: int = Field(default=0, description="Total records found in SQL Server")
    records_synced: int = Field(default=0, description="Successfully synced to PostgreSQL")
    records_created: int = Field(default=0, description="New records created")
    records_updated: int = Field(default=0, description="Existing records updated")
    records_skipped: int = Field(default=0, description="Records skipped due to errors")
    error_count: int = Field(default=0, description="Number of errors encountered")
    percent_complete: float = Field(default=0.0, description="Percentage complete (0-100)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "records_queried": 1000,
                "records_synced": 950,
                "records_created": 300,
                "records_updated": 650,
                "records_skipped": 50,
                "error_count": 50,
                "percent_complete": 95.0
            }
        }


class SyncStatusResponse(BaseModel):
    """Detailed status of a sync job."""
    sync_id: UUID4
    sync_type: SyncTypeEnum
    status: SyncStatusEnum
    is_full_sync: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    progress: SyncProgressMetrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Type-specific metrics")
    last_sync_timestamp: Optional[datetime] = Field(None, description="Timestamp of last successful sync")
    error_message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                "sync_type": "employee_reports",
                "status": "completed",
                "is_full_sync": False,
                "started_at": "2025-11-24T13:13:19Z",
                "completed_at": "2025-11-24T13:13:24Z",
                "duration_seconds": 5.7,
                "progress": {
                    "records_queried": 4,
                    "records_synced": 4,
                    "records_created": 3,
                    "records_updated": 1,
                    "records_skipped": 0,
                    "error_count": 0,
                    "percent_complete": 100.0
                },
                "metrics": {
                    "employees_created": 0,
                    "employees_updated": 4,
                    "reports_created": 3,
                    "reports_updated": 1
                },
                "last_sync_timestamp": "2025-11-17T10:53:11Z",
                "error_message": None
            }
        }


class LastSyncResponse(BaseModel):
    """Information about the last successful sync."""
    sync_type: SyncTypeEnum
    last_successful_sync_id: Optional[UUID4] = None
    last_sync_timestamp: Optional[datetime] = None
    records_synced: Optional[int] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_type": "employee_reports",
                "last_successful_sync_id": "9a41f725-d963-4ea0-8d3c-9d0189d50a4d",
                "last_sync_timestamp": "2025-11-17T10:53:11Z",
                "records_synced": 234,
                "completed_at": "2025-11-24T12:23:59Z"
            }
        }


class SyncHistoryItem(BaseModel):
    """Summary item for sync history list."""
    sync_id: UUID4
    sync_type: SyncTypeEnum
    status: SyncStatusEnum
    is_full_sync: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_synced: int = 0
    records_queried: int = 0
    error_count: int = 0
    last_sync_timestamp: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                "sync_type": "employee_reports",
                "status": "completed",
                "is_full_sync": False,
                "started_at": "2025-11-24T13:13:19Z",
                "completed_at": "2025-11-24T13:13:24Z",
                "duration_seconds": 5.7,
                "records_synced": 4,
                "error_count": 0,
                "last_sync_timestamp": "2025-11-17T10:53:11Z"
            }
        }


class SyncHistoryListResponse(BaseModel):
    """Paginated list of sync history."""
    total: int
    page: int
    page_size: int
    pages: int
    items: List[SyncHistoryItem]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 150,
                "page": 1,
                "page_size": 20,
                "pages": 8,
                "items": [
                    {
                        "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                        "sync_type": "employee_reports",
                        "status": "completed",
                        "is_full_sync": False,
                        "started_at": "2025-11-24T13:13:19Z",
                        "completed_at": "2025-11-24T13:13:24Z",
                        "duration_seconds": 5.7,
                        "records_synced": 4,
                        "error_count": 0,
                        "last_sync_timestamp": "2025-11-17T10:53:11Z"
                    }
                ]
            }
        }


class SyncErrorItem(BaseModel):
    """Individual sync error details."""
    row_number: int
    field_name: Optional[str] = None
    error_message: str
    error_category: Optional[str] = None
    row_data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "row_number": 523,
                "field_name": "Employee_ID",
                "error_message": "Employee ID 9999 does not exist in database",
                "error_category": "validation",
                "row_data": {
                    "Employee_ID": 9999,
                    "Name": "John Doe",
                    "From": "2025-01-01"
                }
            }
        }


class SyncErrorsResponse(BaseModel):
    """Paginated list of sync errors."""
    sync_id: UUID4
    total_errors: int
    page: int
    page_size: int
    errors: List[SyncErrorItem]
    
    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
                "total_errors": 45,
                "page": 1,
                "page_size": 100,
                "errors": [
                    {
                        "row_number": 523,
                        "field_name": "Employee_ID",
                        "error_message": "Employee ID 9999 does not exist in database",
                        "error_category": "validation",
                        "row_data": {
                            "Employee_ID": 9999,
                            "Name": "John Doe",
                            "From": "2025-01-01"
                        }
                    }
                ]
            }
        }


class SyncConfigResponse(BaseModel):
    """Current sync service configuration."""
    sql_server: Dict[str, Any]
    allowed_tables: List[str]
    allowed_timestamp_columns: List[str]
    sync_settings: Dict[str, Any]
    sync_schedule: Dict[str, Any]
    sync_enabled: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "sql_server": {
                    "host": "localhost\\SQLEXPRESS",
                    "database": "EmployeeTestDB",
                    "connection_status": "connected"
                },
                "allowed_tables": [
                    "EmployeeReports",
                    "VisionEmployeeData"
                ],
                "allowed_timestamp_columns": [
                    "LastModifiedDate",
                    "ModifiedDate",
                    "UpdatedAt"
                ],
                "sync_settings": {
                    "max_batch_size": 10000,
                    "error_threshold_percent": 10.0,
                    "default_chunk_size": 1000
                },
                "sync_schedule": {
                    "incremental_sync": {
                        "enabled": True,
                        "schedule": "Monday 2:00 AM",
                        "next_run": "2025-11-25T02:00:00Z"
                    },
                    "full_sync": {
                        "enabled": False,
                        "schedule": "Manual trigger only"
                    }
                },
                "sync_enabled": True
            }
        }


class ConnectionTestResponse(BaseModel):
    """Result of SQL Server connection test."""
    status: str
    server: str
    database: str
    available_tables: List[str]
    connection_time_ms: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "connected",
                "server": "localhost\\SQLEXPRESS",
                "database": "EmployeeTestDB",
                "available_tables": [
                    "EmployeeReports",
                    "VisionEmployeeData"
                ],
                "connection_time_ms": 45,
                "message": "Successfully connected to SQL Server"
            }
        }
