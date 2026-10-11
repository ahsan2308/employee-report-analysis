from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db
from app.models.import_models import ImportStatus, CSVImportType
from app.schemas.csv_import_schema import (
    CSVImportOptions, 
    CSVImportJobResponse, 
    ImportErrorsResponse
)
from app.services.csv_import_service import get_csv_import_service, list_import_jobs as list_jobs
from app.tasks.import_tasks import process_csv_import
from app.core.logger import logger

# Initialize Router
router = APIRouter(prefix="/imports", tags=["CSV Imports"])


@router.post("/upload", response_model=CSVImportJobResponse)
async def upload_csv_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    stop_on_error: bool = Form(False),
    error_threshold_percent: float = Form(10.0),
    chunk_size: int = Form(1000),
    processing_mode: str = Form("bulk"),
    file_format: str = Form("auto", description="File format: csv, txt, tsv, or auto (detect)"),
    delimiter: Optional[str] = Form(None, description="Field delimiter. None means auto-detect."),
    encoding: Optional[str] = Form(None, description="File encoding. None means auto-detect."),
    csv_type: Optional[str] = Form(None, description="Optional CSV type override (e.g., 'employee_report', 'vision_data')"),
    db: Session = Depends(get_db)
):
    """
    Upload a delimited text file (CSV, TXT, or TSV) for import.
    
    The file will be processed asynchronously, and a job ID is returned for tracking progress.
    **The delimiter will be automatically detected** from the file content, or you can specify it explicitly.
    
    Supported file types:
    - CSV: Comma-delimited (typically)
    - TXT: Tab-delimited (typically, e.g., Vision Data exports)
    - TSV: Tab-separated values
    
    Supported delimiters (auto-detected or explicit):
    - Comma (,)
    - Tab (\\t)
    - Pipe (|)
    - Semicolon (;)
    - Colon (:)
    - Space ( )
    
    Args:
        file: The CSV, TXT, or TSV file to upload
        dry_run: If True, validate the file without writing to the database
        stop_on_error: If True, stop processing on the first error
        error_threshold_percent: Maximum percentage of errors before aborting
        chunk_size: Number of rows to process in each chunk
        processing_mode: Either "row_by_row" or "bulk"
        file_format: File format hint (csv, txt, tsv, or auto). Auto-detect if not specified.
        delimiter: Explicit delimiter character. Auto-detect if not specified.
        encoding: File encoding (e.g., utf-8, windows-1252). Auto-detect if not specified.
        csv_type: Optional CSV type override to force a specific processor
    """
    logger.info(f"Received file upload: {file.filename}, type: {csv_type or 'auto-detect'}")
       
    # Validate file extension - accept CSV, TXT, and TSV
    if not (file.filename.lower().endswith('.csv') or 
            file.filename.lower().endswith('.txt') or 
            file.filename.lower().endswith('.tsv')):
        raise HTTPException(
            status_code=400, 
            detail="File must have a .csv, .txt, or .tsv extension. Delimiter will be auto-detected."
        )
    
    # Validate CSV type if provided
    if csv_type and csv_type not in [t.value for t in CSVImportType]:
        valid_types = ", ".join([t.value for t in CSVImportType])
        raise HTTPException(status_code=400, detail=f"Invalid CSV type. Must be one of: {valid_types}")
    
    # Auto-detect file format from extension if set to "auto"
    if file_format == "auto":
        if file.filename.lower().endswith('.txt'):
            logger.info(f"File {file.filename} detected as TXT format (tab-delimited)")
            file_format = "txt"
        elif file.filename.lower().endswith('.tsv'):
            logger.info(f"File {file.filename} detected as TSV format (tab-delimited)")
            file_format = "tsv"
        elif file.filename.lower().endswith('.csv'):
            logger.info(f"File {file.filename} detected as CSV format")
            file_format = "csv"


    try:
        # Create import options from form data
        options = CSVImportOptions(
            dry_run=dry_run,
            stop_on_error=stop_on_error,
            error_threshold_percent=error_threshold_percent,
            chunk_size=chunk_size,
            processing_mode=processing_mode,
            file_format=file_format,
            delimiter=delimiter,
            encoding=encoding
        )
        
        # Create import job with optional CSV type
        import_service = get_csv_import_service()
        job = import_service.create_import_job(
            filename=file.filename, 
            options=options,
            csv_type=csv_type
        )
        
        # Read file content
        file_content = await file.read()
        
        # Queue the task to process the file using Celery, passing csv_type
        try:
            process_csv_import.delay(
                job_id=str(job.job_id),
                file_content=file_content,
                filename=file.filename,
                options=options.model_dump(),
                csv_type=csv_type
            )
        except Exception as dispatch_error:
            # Without this the job would stay PENDING forever
            import_service.mark_job_failed(str(job.job_id), f"Could not queue the import task: {dispatch_error}")
            raise
        
        # Return job info
        return job
        
    except Exception as e:
        logger.error(f"Error processing CSV upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing upload")

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
        raise HTTPException(status_code=500, detail="Error retrieving import job")

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
        raise HTTPException(status_code=500, detail="Error retrieving import errors")

@router.get("/", response_model=List[CSVImportJobResponse])
def list_import_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    csv_type: Optional[str] = Query(None, description="Filter by CSV type"),
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
            
        # Validate CSV type if provided
        valid_types = [t.value for t in CSVImportType]
        if csv_type and csv_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid CSV type. Must be one of: {', '.join(valid_types)}"
            )
        
        return list_jobs(db, status=status, csv_type=csv_type, limit=limit, offset=offset)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error listing import jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing import jobs")
