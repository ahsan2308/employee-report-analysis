from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import get_db
from app.api.serializers import task_result_response
from app.schemas.task_schema import TaskStatusResponse, TaskResultResponse 
from app.services.task_service import TaskNotFoundError, get_task_status, get_task_result
from app.models.task_models import TaskStatus
from app.core.logger import logger

# Initialize router
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status_endpoint(task_id: UUID, db: Session = Depends(get_db)):
    """
    Get the current status of a task.
    
    This endpoint allows polling for status updates as a task progresses.
    """
    try:
        task = get_task_status(db, task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Calculate duration if applicable
        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
        
        return {
            "task_id": task.task_id,
            "celery_task_id": task.celery_task_id,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "duration": duration,
            "is_complete": task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving task")

@router.get("/{task_id}/result", response_model=TaskResultResponse)
def get_task_result_endpoint(task_id: UUID, db: Session = Depends(get_db)):
    """
    Get the result of a completed task.
    
    This endpoint returns 404 for an unknown task and 422 if the task is not yet complete.
    """
    try:
        return task_result_response(task_id, get_task_result(db, task_id))
    except TaskNotFoundError as nf:
        raise HTTPException(status_code=404, detail=str(nf))
    except ValueError as ve:
        # Handle case where task is not complete
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error getting task result: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving task result")
