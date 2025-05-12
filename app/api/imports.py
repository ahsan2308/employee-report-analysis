from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.database import get_database
from app.models.import_models import CSVImportJob, ImportStatus, ImportError
from app.schemas.csv_import_schema import (
    CSVImportOptions, 
    CSVImportJobResponse, 
    ImportErrorsResponse,
    CSVImportJobCreate
)
from app.services.csv_import_service import get_csv_import_service
from app.tasks.import_tasks import process_csv_import
from app.core.logger import logger

# Initialize Router
router = APIRouter(prefix="/imports", tags=["CSV Imports"])

# Dependency to get database session (consistent with other API files)
def get_db():
    db_instance = get_database()
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()

@router.post("/upload", response_model=CSVImportJobResponse)
async def upload_csv_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    stop_on_error: bool = Form(False),
    error_threshold_percent: float = Form(10.0),
    chunk_size: int = Form(1000),
    processing_mode: str = Form("bulk"),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file for import.
    
    The file will be processed asynchronously, and a job ID is returned for tracking progress.
    """
    logger.info(f"Received CSV upload: {file.filename}")
    
    # Validate file
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must have a .csv extension")
    
    try:
        # Create import options from form data
        options = CSVImportOptions(
            dry_run=dry_run,
            stop_on_error=stop_on_error,
            error_threshold_percent=error_threshold_percent,
            chunk_size=chunk_size,
            processing_mode=processing_mode
        )
        
        # Create import job - now returns a Pydantic model
        import_service = get_csv_import_service()
        job = import_service.create_import_job(filename=file.filename, options=options)
        
        # Read file content
        file_content = await file.read()
        
        # Queue the task to process the file using Celery
        task = process_csv_import.delay(
            job_id=str(job.job_id),  # Use attribute access instead of dictionary access
            file_content=file_content,
            filename=file.filename,
            options=options.model_dump()
        )
        
        # Return job info - it's already a Pydantic model
        return job
        
    except Exception as e:
        logger.error(f"Error processing CSV upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")

@router.get("/{job_id}", response_model=CSVImportJobResponse)
def get_import_job(job_id: str, db: Session = Depends(get_db)):
    """
    Get status and details for a specific import job.
    """
    try:
        # Get job
        import_service = get_csv_import_service()
        job_dict = import_service.get_import_job(job_id)
        
        if not job_dict:
            raise HTTPException(status_code=404, detail="Import job not found")
            
        # Return the dictionary directly
        return job_dict
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving import job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving import job: {str(e)}")

@router.get("/{job_id}/errors", response_model=ImportErrorsResponse)
def get_import_errors(
    job_id: str, 
    page: int = Query(1, ge=1), 
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of errors for a specific import job.
    """
    try:
        # Get job first to verify it exists
        import_service = get_csv_import_service()
        job = import_service.get_import_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")
            
        # Get errors with pagination - now returns dictionaries instead of SQLAlchemy objects
        total, error_dicts = import_service.get_job_errors(job_id, page, page_size)
        
        # No need for conversion since error_dicts already contains all necessary data
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "errors": error_dicts
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving import errors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving import errors: {str(e)}")

@router.get("/", response_model=List[CSVImportJobResponse])
def list_import_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all import jobs with optional filtering.
    """
    try:
        # Validate status if provided
        valid_statuses = [s.value for s in ImportStatus]
        if status and status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Query jobs
        query = db.query(CSVImportJob)
        if status:
            query = query.filter(CSVImportJob.status == status)
            
        # Get total first
        total = query.count()
        
        # Apply pagination and ordering (newest first)
        jobs = query.order_by(CSVImportJob.submitted_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response format
        response = []
        for job in jobs:
            response.append({
                "job_id": str(job.job_id),
                "filename": job.filename,
                "status": job.status,
                "submitted_at": job.submitted_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "total_rows": job.total_rows,
                "processed_rows": job.processed_rows,
                "successful_rows": job.successful_rows,
                "error_count": job.error_count,
                "employees_created": job.employees_created,
                "employees_updated": job.employees_updated,
                "reports_created": job.reports_created,
                "reports_updated": job.reports_updated,
                "percent_complete": 0.0,  # Will be calculated in response model
                "estimated_time_remaining": None
            })
            
        return response
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error listing import jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing import jobs: {str(e)}")
