from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.serializers import (
    monthly_analysis_response, monthly_analysis_summary, quarterly_analysis_response, task_status_response,
    weekly_analysis_list_item, weekly_analysis_response,
)
from app.schemas.analysis_schema import AnalysisResponse, MonthlyAnalysisResponse, MonthlyAnalysisSummary, QuarterlyAnalysisResponse
from app.repositories import analyses as analysis_repo
from app.repositories.employees import get_employee
from app.repositories.reports import get_report
from app.core.logger import logger
from uuid import UUID
from typing import List

# Add imports for task handling
from app.schemas.task_schema import TaskStatusResponse
from app.services.task_service import create_task_for_analysis, create_task_for_monthly_analysis, create_task_for_quarterly_analysis

# Initialize Router
router = APIRouter(prefix="/analyses", tags=["Analyses"])


# Modify to return a task ID instead of waiting for analysis
@router.post("/analyze/{report_id}", response_model=TaskStatusResponse)
def analyze_report(report_id: str, db: Session = Depends(get_db)):
    logger.info(f"Request received to analyze report {report_id} asynchronously")
    try:
        # Convert string to UUID if needed
        report_uuid = UUID(report_id) if not isinstance(report_id, UUID) else report_id
        
        # Check if report exists
        report = get_report(db, report_uuid)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if employee exists
        employee = get_employee(db, report.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Check if analysis already exists - reuse it if it does
        existing_analysis = analysis_repo.find_weekly_analysis(db, report_uuid)
        
        # Create task (either with existing analysis or as a new task)
        task = create_task_for_analysis(db, report_uuid, employee, existing_analysis)
            
        return task_status_response(task)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail="Error submitting analysis")

# Get analysis by report ID
@router.get("/results/{report_id}", response_model=AnalysisResponse)
def get_analysis_by_report(report_id: str, db: Session = Depends(get_db)):
    try:
        # Convert string to UUID
        report_uuid = UUID(report_id)
        
        # Get the analysis
        analysis = analysis_repo.find_weekly_analysis(db, report_uuid)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        # Get the report to find employee
        report = get_report(db, report_uuid)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Get employee details
        employee = get_employee(db, report.employee_id)
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare and return response with employee name included
        return weekly_analysis_response(analysis, employee)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get all analyses for an employee
@router.get("/employee/{employee_id}")
def get_employee_analyses(employee_id: int, db: Session = Depends(get_db)):
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Analyses with their reports (an analysis whose report is gone is left out)
        analyses_list = [
            weekly_analysis_list_item(analysis, report)
            for analysis, report in analysis_repo.list_weekly_analyses_with_reports(db, employee_id)
        ]
            
        return {"employee_id": employee_id, "employee_name": employee.name, "analyses": analyses_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving employee analyses: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get detailed analysis by ID
@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_by_id(analysis_id: int, db: Session = Depends(get_db)):
    try:
        # Get the analysis
        analysis = analysis_repo.get_weekly_analysis(db, analysis_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        # Get report to find employee
        report = get_report(db, analysis.report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Get employee details
        employee = get_employee(db, report.employee_id)
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Prepare response with employee name
        return weekly_analysis_response(analysis, employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Monthly Analysis Endpoints
@router.post("/monthly/analyze", response_model=TaskStatusResponse)
def analyze_monthly_reports(
    employee_id: int,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Submit a monthly analysis task for an employee.
    
    This endpoint initiates asynchronous processing of monthly reports for the given employee.
    The analysis will include all reports from the specified month and year.
    """
    logger.info(f"Request received to analyze monthly reports for employee {employee_id}, period {year}-{month}")
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Check if analysis already exists - if so, return reference to it
        existing_analysis = analysis_repo.find_monthly_analysis(db, employee_id, year, month)
        
        # Create task (either with existing analysis or as a new task)
        task = create_task_for_monthly_analysis(db, employee_id, year, month, existing_analysis)
            
        return task_status_response(task)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting monthly analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail="Error submitting analysis")

@router.get("/monthly/{analysis_id}", response_model=MonthlyAnalysisResponse)
def get_monthly_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get a specific monthly analysis by ID."""
    try:
        analysis = analysis_repo.get_monthly_analysis(db, analysis_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Monthly analysis not found")
            
        # Get employee details
        employee = get_employee(db, analysis.employee_id)
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare structured response
        return monthly_analysis_response(analysis, employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving monthly analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/monthly/employee/{employee_id}", response_model=List[MonthlyAnalysisSummary])
def get_employee_monthly_analyses(employee_id: int, db: Session = Depends(get_db)):
    """Get all monthly analyses for an employee."""
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get all monthly analyses for this employee
        analyses = analysis_repo.list_monthly_analyses(db, employee_id)
        
        return [monthly_analysis_summary(analysis) for analysis in analyses]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving employee monthly analyses: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/monthly/employee/{employee_id}/{year}/{month}", response_model=MonthlyAnalysisResponse)
def get_employee_monthly_analysis_by_period(
    employee_id: int, 
    year: int, 
    month: int, 
    db: Session = Depends(get_db)
):
    """Get a specific monthly analysis by employee, year and month."""
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get the specific monthly analysis
        analysis = analysis_repo.find_monthly_analysis(db, employee_id, year, month)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Monthly analysis not found for {year}-{month}")
        
        # Return formatted response
        return monthly_analysis_response(analysis, employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving monthly analysis by period: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Quarterly Analysis Endpoints
@router.post("/quarterly/analyze", response_model=TaskStatusResponse)
def analyze_quarterly_reports(
    employee_id: int,
    year: int = Query(..., ge=2000, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    db: Session = Depends(get_db)
):
    """
    Submit a quarterly analysis task for an employee.
    
    This endpoint initiates asynchronous processing of quarterly performance for the given employee.
    The analysis will aggregate data from the three months in the specified quarter.
    """
    logger.info(f"Request received to analyze quarterly performance for employee {employee_id}, period {year}-Q{quarter}")
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Check if analysis already exists
        existing_analysis = analysis_repo.find_quarterly_analysis(db, employee_id, year, quarter)
        
        # Create task (either with existing analysis or as a new task)
        task = create_task_for_quarterly_analysis(db, employee_id, year, quarter, existing_analysis)
            
        return task_status_response(task)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting quarterly analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail="Error submitting analysis")

@router.get("/quarterly/{analysis_id}", response_model=QuarterlyAnalysisResponse)
def get_quarterly_analysis(
    analysis_id: int = Path(..., description="ID of the quarterly analysis to retrieve"),
    db: Session = Depends(get_db)
):
    """Get a specific quarterly analysis by ID."""
    try:
        analysis = analysis_repo.get_quarterly_analysis(db, analysis_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Quarterly analysis not found")
            
        # Get employee details
        employee = get_employee(db, analysis.employee_id)
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare structured response
        return quarterly_analysis_response(analysis, employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quarterly analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/quarterly/employee/{employee_id}/{year}/{quarter}", response_model=QuarterlyAnalysisResponse)
def get_employee_quarterly_analysis_by_period(
    employee_id: int = Path(..., description="Employee ID"),
    year: int = Path(..., description="Year of analysis", ge=2000, le=2100),
    quarter: int = Path(..., description="Quarter (1-4)", ge=1, le=4),
    db: Session = Depends(get_db)
):
    """Get a specific quarterly analysis by employee, year and quarter."""
    try:
        # Check if employee exists
        employee = get_employee(db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get the specific quarterly analysis
        analysis = analysis_repo.find_quarterly_analysis(db, employee_id, year, quarter)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Quarterly analysis not found for {year}-Q{quarter}")
        
        # Return formatted response
        return quarterly_analysis_response(analysis, employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quarterly analysis by period: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


