from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import EmployeeAnalysis, Report, Employee, MonthlyAnalysis
from app.schemas.analysis_schema import AnalysisResponse, MonthlyAnalysisResponse, MonthlyAnalysisSummary
from app.services.llm_service import get_llm_service
from app.services.db_service import get_reports_for_vector_results, get_monthly_analysis_by_params
from app.services.vector_store_service import search_reports
from app.core.logger import logger
import uuid
from uuid import UUID
from datetime import datetime
from typing import List

# Add imports for task handling
from app.models.task_models import BackgroundTask, TaskStatus, TaskType
from app.tasks.analysis_tasks import analyze_report_task
from app.schemas.task_schema import TaskStatusResponse
from app.services.task_service import create_task_for_analysis, create_task_for_monthly_analysis

# Initialize Router
router = APIRouter(prefix="/analyses", tags=["Analyses"])

# Dependency to get database session
def get_db():
    db_instance = get_database()  
    session = db_instance.create_session()
    try:
        yield session
    finally:
        session.close()

# Modify to return a task ID instead of waiting for analysis
@router.post("/analyze/{report_id}", response_model=TaskStatusResponse)
def analyze_report(report_id: str, db: Session = Depends(get_db)):
    logger.info(f"Request received to analyze report {report_id} asynchronously")
    try:
        # Convert string to UUID if needed
        report_uuid = UUID(report_id) if not isinstance(report_id, UUID) else report_id
        
        # Check if report exists
        report = db.query(Report).filter(Report.report_id == report_uuid).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == report.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Check if analysis already exists - reuse it if it does
        existing_analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.report_id == report_uuid
        ).first()
        
        # Create task (either with existing analysis or as a new task)
        task = create_task_for_analysis(db, report_uuid, employee, existing_analysis)
            
        return {
            "task_id": task.task_id,
            "celery_task_id": task.celery_task_id,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "is_complete": task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting analysis: {str(e)}")

# Get analysis by report ID
@router.get("/results/{report_id}", response_model=AnalysisResponse)
def get_analysis_by_report(report_id: str, db: Session = Depends(get_db)):
    try:
        # Convert string to UUID
        report_uuid = UUID(report_id)
        
        # Get the analysis
        analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.report_id == report_uuid
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        # Get the report to find employee
        report = db.query(Report).filter(
            Report.report_id == report_uuid
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Get employee details
        employee = db.query(Employee).filter(
            Employee.id == report.employee_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare and return response with employee name included
        return {
            "report_id": str(analysis.report_id),
            "employee_name": employee.name,
            "sentiment": analysis.sentiment_score if analysis.sentiment_score is not None else 0.5,
            "sentiment_score": analysis.sentiment_score,
            "risk_level": analysis.risk_level,
            "risk_explanation": analysis.risk_explanation,
            "full_analysis_json": analysis.full_analysis_json,
            "achievements_json": analysis.achievements_json,
            "challenges_json": analysis.challenges_json,
            "topics": analysis.topics,
            "action_items": analysis.action_items,
            "credibility_assessment": {
                "rating": analysis.credibility_rating or "medium",
                "explanation": analysis.credibility_explanation or "No credibility assessment was performed for this analysis.",
                "exaggeration_flags": analysis.exaggeration_flags or [],
                "consistency_score": analysis.consistency_score or "medium"
            },
            "performance_assessment": {
                "rating": analysis.performance_rating or "medium",
                "summary": analysis.performance_summary or "No performance assessment was performed for this analysis.",
                "key_strengths": analysis.performance_strengths or [],
                "improvement_areas": analysis.performance_improvement_areas or []
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID format")
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all analyses for an employee
@router.get("/employee/{employee_id}")
def get_employee_analyses(employee_id: int, db: Session = Depends(get_db)):
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get analyses for employee
        analyses = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.employee_id == employee_id
        ).all()
        
        analyses_list = []
        for analysis in analyses:
            # Get report for this analysis
            report = db.query(Report).filter(
                Report.report_id == analysis.report_id
            ).first()
            
            if report:
                analyses_list.append({
                    "analysis_id": analysis.analysis_id,
                    "report_id": str(analysis.report_id),
                    "report_date": report.report_date,
                    "sentiment_score": analysis.sentiment_score,
                    "risk_level": analysis.risk_level,
                    "performance_rating": analysis.performance_rating
                })
            
        return {"employee_id": employee_id, "employee_name": employee.name, "analyses": analyses_list}
    except Exception as e:
        logger.error(f"Error retrieving employee analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get detailed analysis by ID
@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_by_id(analysis_id: int, db: Session = Depends(get_db)):
    try:
        # Get the analysis
        analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.analysis_id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
            
        # Get report to find employee
        report = db.query(Report).filter(
            Report.report_id == analysis.report_id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Get employee details
        employee = db.query(Employee).filter(
            Employee.id == report.employee_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Prepare response with employee name
        return {
            "report_id": str(analysis.report_id),
            "employee_name": employee.name,
            "sentiment": analysis.sentiment_score if analysis.sentiment_score is not None else 0.5,
            "sentiment_score": analysis.sentiment_score,
            "risk_level": analysis.risk_level,
            "risk_explanation": analysis.risk_explanation,
            "full_analysis_json": analysis.full_analysis_json,
            "achievements_json": analysis.achievements_json,
            "challenges_json": analysis.challenges_json,
            "topics": analysis.topics,
            "action_items": analysis.action_items,
            "credibility_assessment": {
                "rating": analysis.credibility_rating or "medium",
                "explanation": analysis.credibility_explanation or "No credibility assessment was performed for this analysis.",
                "exaggeration_flags": analysis.exaggeration_flags or [],
                "consistency_score": analysis.consistency_score or "medium"
            },
            "performance_assessment": {
                "rating": analysis.performance_rating or "medium",
                "summary": analysis.performance_summary or "No performance assessment was performed for this analysis.",
                "key_strengths": analysis.performance_strengths or [],
                "improvement_areas": analysis.performance_improvement_areas or []
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Check if analysis already exists - if so, return reference to it
        existing_analysis = get_monthly_analysis_by_params(employee_id, year, month)
        
        # Create task (either with existing analysis or as a new task)
        task = create_task_for_monthly_analysis(db, employee_id, year, month, existing_analysis)
            
        return {
            "task_id": task.task_id,
            "celery_task_id": task.celery_task_id,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "is_complete": task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting monthly analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting analysis: {str(e)}")

@router.get("/monthly/{analysis_id}", response_model=MonthlyAnalysisResponse)
def get_monthly_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get a specific monthly analysis by ID."""
    try:
        analysis = db.query(MonthlyAnalysis).filter(
            MonthlyAnalysis.analysis_id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Monthly analysis not found")
            
        # Get employee details
        employee = db.query(Employee).filter(
            Employee.id == analysis.employee_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare structured response
        return {
            "analysis_id": analysis.analysis_id,
            "employee_id": analysis.employee_id,
            "employee_name": employee.name,
            "year": analysis.year,
            "month": analysis.month,
            "period_start": analysis.period_start,
            "period_end": analysis.period_end,
            "avg_sentiment_score": analysis.avg_sentiment_score,
            
            "progress_trends": {
                "sentiment_trend": analysis.sentiment_trend,
                "performance_trend": analysis.performance_trend,
                "risk_level_pattern": analysis.risk_level_pattern,
                "challenge_resolution_progress": analysis.challenge_resolution_progress
            },
            
            "monthly_achievements": analysis.monthly_achievements or [],
            "recurring_challenges": analysis.recurring_challenges or [],
            
            "consistency_assessment": {
                "task_completion_reliability": analysis.task_completion_reliability,
                "work_quality_consistency": analysis.work_quality_consistency,
                "performance_stability": analysis.performance_stability,
                "notable_strengths": analysis.consistency_notable_strengths or [],
                "notable_weaknesses": analysis.consistency_notable_weaknesses or []
            },
            
            "growth_indicators": {
                "complexity_of_tasks": analysis.complexity_of_tasks,
                "skill_development_evidence": analysis.skill_development_evidence,
                "confidence_level_change": analysis.confidence_level_change,
                "approach_to_challenges": analysis.approach_to_challenges
            },
            
            "focus_areas": analysis.focus_areas or [],
            
            "monthly_risk_assessment": {
                "overall_risk_level": analysis.risk_level,
                "risk_explanation": analysis.risk_explanation,
                "significant_risks": analysis.significant_risks or [],
                "escalating_risks": analysis.escalating_risks or [],
                "risk_mitigation_recommendations": analysis.risk_mitigation_recommendations or []
            },
            
            "strategic_recommendations": analysis.strategic_recommendations or [],
            "monthly_summary": analysis.monthly_summary
        }
        
    except Exception as e:
        logger.error(f"Error retrieving monthly analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/monthly/employee/{employee_id}", response_model=List[MonthlyAnalysisSummary])
def get_employee_monthly_analyses(employee_id: int, db: Session = Depends(get_db)):
    """Get all monthly analyses for an employee."""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get all monthly analyses for this employee
        analyses = db.query(MonthlyAnalysis).filter(
            MonthlyAnalysis.employee_id == employee_id
        ).order_by(MonthlyAnalysis.year.desc(), MonthlyAnalysis.month.desc()).all()
        
        return [
            {
                "analysis_id": analysis.analysis_id,
                "employee_id": analysis.employee_id,
                "year": analysis.year,
                "month": analysis.month,
                "period_start": analysis.period_start,
                "period_end": analysis.period_end,
                "performance_trend": analysis.performance_trend,
                "sentiment_trend": analysis.sentiment_trend,
                "risk_level": analysis.risk_level,
                "achievement_count": len(analysis.monthly_achievements) if analysis.monthly_achievements else 0,
                "challenge_count": len(analysis.recurring_challenges) if analysis.recurring_challenges else 0,
                "monthly_summary": analysis.monthly_summary
            } for analysis in analyses
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving employee monthly analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        # Get the specific monthly analysis
        analysis = db.query(MonthlyAnalysis).filter(
            MonthlyAnalysis.employee_id == employee_id,
            MonthlyAnalysis.year == year,
            MonthlyAnalysis.month == month
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Monthly analysis not found for {year}-{month}")
        
        # Return formatted response
        return {
            "analysis_id": analysis.analysis_id,
            "employee_id": analysis.employee_id,
            "employee_name": employee.name,
            "year": analysis.year,
            "month": analysis.month,
            "period_start": analysis.period_start,
            "period_end": analysis.period_end,
            "avg_sentiment_score": analysis.avg_sentiment_score,
            
            "progress_trends": {
                "sentiment_trend": analysis.sentiment_trend,
                "performance_trend": analysis.performance_trend,
                "risk_level_pattern": analysis.risk_level_pattern,
                "challenge_resolution_progress": analysis.challenge_resolution_progress
            },
            
            "monthly_achievements": analysis.monthly_achievements or [],
            "recurring_challenges": analysis.recurring_challenges or [],
            
            "consistency_assessment": {
                "task_completion_reliability": analysis.task_completion_reliability,
                "work_quality_consistency": analysis.work_quality_consistency,
                "performance_stability": analysis.performance_stability,
                "notable_strengths": analysis.consistency_notable_strengths or [],
                "notable_weaknesses": analysis.consistency_notable_weaknesses or []
            },
            
            "growth_indicators": {
                "complexity_of_tasks": analysis.complexity_of_tasks,
                "skill_development_evidence": analysis.skill_development_evidence,
                "confidence_level_change": analysis.confidence_level_change,
                "approach_to_challenges": analysis.approach_to_challenges
            },
            
            "focus_areas": analysis.focus_areas or [],
            
            "monthly_risk_assessment": {
                "overall_risk_level": analysis.risk_level,
                "risk_explanation": analysis.risk_explanation,
                "significant_risks": analysis.significant_risks or [],
                "escalating_risks": analysis.escalating_risks or [],
                "risk_mitigation_recommendations": analysis.risk_mitigation_recommendations or []
            },
            
            "strategic_recommendations": analysis.strategic_recommendations or [],
            "monthly_summary": analysis.monthly_summary
        }
        
    except Exception as e:
        logger.error(f"Error retrieving monthly analysis by period: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



