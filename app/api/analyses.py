from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import EmployeeAnalysis, Report, Employee
from app.schemas.analysis_schema import AnalysisResponse
from app.services.llm_service import get_llm_service
from app.services.db_service import get_reports_for_vector_results
from app.services.vector_store_service import search_reports
from app.core.logger import logger
import uuid
from uuid import UUID

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

@router.post("/analyze/{report_id}", response_model=AnalysisResponse)
def analyze_report(report_id: str, db: Session = Depends(get_db)):
    logger.info(f"Request received to analyze report {report_id}")
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
            
        # Check if analysis already exists
        existing_analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.report_id == report_uuid
        ).first()
        
        if existing_analysis:
            # If analysis exists, fetch full analysis data
            analysis_data = {
                "report_id": str(existing_analysis.report_id),  # Convert UUID to string
                "employee_name": employee.name,  # Lookup employee name from the relationship
                "sentiment": existing_analysis.sentiment_score if existing_analysis.sentiment_score is not None else 0.5,
                # Include other fields from existing analysis
                "sentiment_score": existing_analysis.sentiment_score,
                "risk_level": existing_analysis.risk_level,
                "risk_explanation": existing_analysis.risk_explanation,
                "full_analysis_json": existing_analysis.full_analysis_json,
                "achievements_json": existing_analysis.achievements_json,
                "challenges_json": existing_analysis.challenges_json,
                "topics": existing_analysis.topics,
                "action_items": existing_analysis.action_items
            }
            return analysis_data
        
        # Get similar reports for context
        logger.info("Finding similar reports for context")
        similar_reports_chunks = search_reports(
            query=report.report_text,
            employee_id=report.employee_id,
            top_k=3
        )
        similar_texts_chunks = [r.get("text", "") for r in similar_reports_chunks]
        
        # Retrieving Full Reports
        similar_texts = get_reports_for_vector_results(similar_texts_chunks)
        
        # Get LLM service
        llm_service = get_llm_service()
        
        # Generate analysis
        logger.info("Calling LLM service for analysis")
        analysis_result = llm_service.analyze_report(report.report_text, similar_texts, num_ctx = 32768)
        
        # Extract key fields from the enhanced analysis result
        sentiment = analysis_result.get("sentiment", "neutral")
        risk_level = analysis_result.get("risk_level", "low")
        risk_explanation = analysis_result.get("risk_explanation", "")
        topics = analysis_result.get("topics", [])
        achievements = analysis_result.get("achievements", [])
        challenges = analysis_result.get("challenges", [])
        action_items = analysis_result.get("action_items", [])
        
        # Calculate sentiment score
        sentiment_score = 0.0
        if sentiment == "positive":
            sentiment_score = 0.8
        elif sentiment == "negative":
            sentiment_score = 0.2
        elif sentiment == "neutral":
            sentiment_score = 0.5

        # Create a new analysis record with enhanced fields
        new_analysis = EmployeeAnalysis(
            report_id=report_uuid,
            employee_id=report.employee_id,
            sentiment_score=sentiment_score,
            risk_level=risk_level,
            risk_explanation=risk_explanation,
            full_analysis_json=analysis_result,
            achievements_json=achievements,
            challenges_json=challenges,
            topics=topics,
            action_items=action_items
        )
        
        # Save to database
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        logger.info(f"Analysis saved with ID: {new_analysis.analysis_id}")
        
        # Prepare response with all required fields
        analysis_response = {
            "report_id": str(new_analysis.report_id),  # Convert UUID to string
            "employee_name": employee.name,  # Lookup from employee relationship
            "sentiment": new_analysis.sentiment_score if new_analysis.sentiment_score is not None else 0.5,
            "sentiment_score": new_analysis.sentiment_score,
            "risk_level": new_analysis.risk_level,
            "risk_explanation": new_analysis.risk_explanation,
            "full_analysis_json": new_analysis.full_analysis_json,
            "achievements_json": new_analysis.achievements_json,
            "challenges_json": new_analysis.challenges_json,
            "topics": new_analysis.topics,
            "action_items": new_analysis.action_items
        }
        
        return analysis_response
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid report ID format: {str(ve)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error analyzing report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating analysis: {str(e)}")

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
            "employee_name": employee.name,  # Include employee name from related entity
            "sentiment": analysis.sentiment_score if analysis.sentiment_score is not None else 0.5,
            "sentiment_score": analysis.sentiment_score,
            "risk_level": analysis.risk_level,
            "risk_explanation": analysis.risk_explanation,
            "full_analysis_json": analysis.full_analysis_json,
            "achievements_json": analysis.achievements_json,
            "challenges_json": analysis.challenges_json,
            "topics": analysis.topics,
            "action_items": analysis.action_items
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
                    "risk_level": analysis.risk_level
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
            "employee_name": employee.name,  # Include employee name from relationship
            "sentiment": analysis.sentiment_score if analysis.sentiment_score is not None else 0.5,
            "sentiment_score": analysis.sentiment_score,
            "risk_level": analysis.risk_level,
            "risk_explanation": analysis.risk_explanation,
            "full_analysis_json": analysis.full_analysis_json,
            "achievements_json": analysis.achievements_json,
            "challenges_json": analysis.challenges_json,
            "topics": analysis.topics,
            "action_items": analysis.action_items
        }
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



