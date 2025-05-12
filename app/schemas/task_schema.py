from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

class TaskStatus(str, Enum):
    """Task status enum for API schemas"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @property
    def is_terminal(self) -> bool:
        """Return True if this is a terminal state (completed or failed)"""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED)

class TaskStatusResponse(BaseModel):
    """Schema for returning task status information"""
    task_id: UUID
    celery_task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds
    is_complete: bool
    
    class Config:
        from_attributes = True  

class TaskResultResponse(BaseModel):
    """Schema for returning task results"""
    task_id: UUID
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
