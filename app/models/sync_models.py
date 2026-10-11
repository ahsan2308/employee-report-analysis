"""
Database models for SQL Server to PostgreSQL sync tracking.

These models track sync operations, store metadata about what was synced,
and provide a history of all sync jobs.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base
from app.db.base import schema_name


class SyncType(str, enum.Enum):
    """Types of data that can be synced."""
    EMPLOYEE_REPORTS = "employee_reports"
    VISION_DATA = "vision_data"
    JOB_DESCRIPTIONS = "job_descriptions"
    SUPERVISOR_FEEDBACK = "supervisor_feedback"


class SyncStatus(str, enum.Enum):
    """Status of a sync operation."""
    PENDING = "pending"      # Sync scheduled but not started
    RUNNING = "running"      # Currently syncing
    COMPLETED = "completed"  # Sync finished successfully
    FAILED = "failed"        # Sync failed with errors
    PARTIAL = "partial"      # Sync completed but with some errors


class SyncHistory(Base):
    """
    Model for tracking SQL Server to PostgreSQL sync operations.
    
    Each record represents one sync job, storing:
    - What was synced (sync_type)
    - When it happened (timestamps)
    - How many records were processed
    - Any errors encountered
    - Metadata about the sync operation
    """
    __tablename__ = "sync_history"
    
    # Primary key
    sync_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sync metadata
    sync_type = Column(String, nullable=False)  # From SyncType enum
    status = Column(String, default=SyncStatus.PENDING.value, nullable=False)  # From SyncStatus enum
    
    # Timestamps
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Last successful sync timestamp (critical for incremental sync)
    last_sync_timestamp = Column(DateTime, nullable=True, index=True)
    
    # Sync metrics
    records_queried = Column(Integer, default=0)      # Total records found in SQL Server
    records_synced = Column(Integer, default=0)       # Successfully synced to PostgreSQL
    records_created = Column(Integer, default=0)      # New records created
    records_updated = Column(Integer, default=0)      # Existing records updated
    records_skipped = Column(Integer, default=0)      # Records skipped (e.g., validation errors)
    error_count = Column(Integer, default=0)          # Number of errors encountered
    
    # Error details (if any)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)  # Structured error information
    
    # Sync configuration and metadata
    sync_options = Column(JSONB, nullable=True)  # Options used for this sync (incremental, full, etc.)
    sync_metadata = Column(JSONB, nullable=True)  # Additional metadata (SQL Server connection info, etc.)
    
    # Table constraints
    __table_args__ = (
        # Ensure valid status values
        CheckConstraint(
            status.in_([s.value for s in SyncStatus]),
            name='check_valid_sync_status'
        ),
        # Ensure valid sync type values
        CheckConstraint(
            sync_type.in_([t.value for t in SyncType]),
            name='check_valid_sync_type'
        ),
        # Index for finding last successful sync by type
        Index('ix_sync_history_type_timestamp', 'sync_type', 'last_sync_timestamp'),
        # Index for querying sync history by date
        Index('ix_sync_history_started_at', 'started_at'),
        # Schema
        {'schema': schema_name}
    )
    
    def __repr__(self):
        return f"<SyncHistory(id={self.sync_id}, type={self.sync_type}, status={self.status}, records={self.records_synced})>"
    
    @property
    def duration_seconds(self):
        """How long the sync ran, once it has finished."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_full_sync(self) -> bool:
        """Whether this was a full sync; a missing flag means incremental."""
        if self.sync_options and isinstance(self.sync_options, dict):
            return self.sync_options.get('is_full_sync', False)
        return False

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "sync_id": str(self.sync_id),
            "sync_type": self.sync_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_sync_timestamp": self.last_sync_timestamp.isoformat() if self.last_sync_timestamp else None,
            "records_queried": self.records_queried,
            "records_synced": self.records_synced,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "error_count": self.error_count,
            "error_message": self.error_message,
            "sync_options": self.sync_options,
            "duration_seconds": self.duration_seconds
        }
