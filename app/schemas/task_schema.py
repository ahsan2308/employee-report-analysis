from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.task_models import TaskStatus

class TaskStatusResponse(BaseModel):
    """Schema for returning task status information"""
    task_id: UUID
    celery_task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None  
    is_complete: bool
    
    model_config = ConfigDict(from_attributes=True)

class TaskResultResponse(BaseModel):
    """Schema for returning task results"""
    task_id: UUID
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
