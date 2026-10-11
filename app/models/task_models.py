from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base
from app.db.base import schema_name

class TaskStatus(str, Enum):
    """Status of a background task (stored as its value)."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """True for COMPLETED and FAILED: the task will not change again."""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED)

class TaskType(str, Enum):
    """Enum for task types."""
    REPORT_ANALYSIS = "REPORT_ANALYSIS"
    MONTHLY_ANALYSIS = "MONTHLY_ANALYSIS"
    QUARTERLY_ANALYSIS = "QUARTERLY_ANALYSIS"

class BackgroundTask(Base):
    """Model for tracking background tasks."""
    
    __tablename__ = "background_tasks"
    
    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    celery_task_id = Column(String, nullable=True)
    # Change to use String type with the enum values instead of a custom PostgreSQL enum type
    task_type = Column(String, nullable=False, default=TaskType.REPORT_ANALYSIS.value)
    
    # Make report_id nullable to support monthly analysis tasks
    report_id = Column(UUID(as_uuid=True), ForeignKey(f"{schema_name}.reports.report_id", ondelete="CASCADE"), nullable=True)
    
    # Add fields for monthly analysis tasks
    employee_id = Column(Integer, ForeignKey(f"{schema_name}.employees.id", ondelete="CASCADE"), nullable=True)
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    quarter = Column(Integer, nullable=True)
    
    # Task status and timing information
    status = Column(String, nullable=False, default=TaskStatus.PENDING.value)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Result and error information
    result_data = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Keep the existing relationship
    report = relationship("Report", back_populates="tasks")
    
    # Properties
    @property
    def duration(self):
        """Calculate task duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def __repr__(self):
        return f"<BackgroundTask id={self.task_id}, status={self.status}, type={self.task_type}>"
    
    @property
    def is_complete(self):
        """Check if task has completed (successfully or with failure)"""
        return TaskStatus(self.status).is_terminal
    
