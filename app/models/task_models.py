from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
import enum
from app.models.base import Base
from app.models.base import schema_name

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundTask(Base):
    """Model for tracking asynchronous background tasks."""
    __tablename__ = "background_tasks"
    
    # Primary key
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Celery task ID
    celery_task_id = Column(String, nullable=False, index=True)
    
    # Task type (e.g., 'analyze_report', 'generate_visualization')
    task_type = Column(String, nullable=False, index=True)
    
    # Foreign key to relevant objects (e.g., report)
    report_id = Column(UUID(as_uuid=True), ForeignKey(f"{schema_name}.reports.report_id"), nullable=True, index=True)
    
    # Task status
    status = Column(String, nullable=False, default=TaskStatus.PENDING.value, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results (stored as JSON)
    result_data = Column(JSON, nullable=True)
    
    # Error message (if task failed)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    report = relationship("Report", back_populates="tasks")
    
    # Properties
    @property
    def duration(self):
        """Calculate task duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_complete(self):
        """Check if task has completed (successfully or with failure)"""
        return self.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
    
    @property
    def is_active(self):
        """Check if task is still active"""
        return self.status in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)

# Add a relationship from Report to BackgroundTask
from app.models.db_models import Report
Report.tasks = relationship("BackgroundTask", back_populates="report", cascade="all, delete-orphan")
