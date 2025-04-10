from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_database
from app.models.db_models import EmployeeAnalysis, Report
from app.schemas.analysis_schema import EmployeeAnalysisResponse
from app.services.llm_service import get_llm_service
from app.services.db_service import get_reports_for_vector_results
from app.services.vector_store_service import search_reports
from app.core.logger import logger
import uuid

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

@router.post("/analyze/{report_id}", response_model=EmployeeAnalysisResponse)
def analyze_report(report_id: str, db: Session = Depends(get_db)):
    """
    Analyze an existing report using the LLM service.
    
    Parameters:
    - report_id: The UUID of the report to analyze
    
    Returns:
    - The created analysis object
    """
    logger.info(f"Starting analysis for report {report_id}")
    try:
        # Convert string ID to UUID if needed
        try:
            report_uuid = uuid.UUID(report_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid report ID format")
        
        # Verify the report exists
        report = db.query(Report).filter(Report.report_id == report_uuid).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if analysis already exists
        existing_analysis = db.query(EmployeeAnalysis).filter(
            EmployeeAnalysis.report_id == report_uuid
        ).first()
        
        if existing_analysis:
            logger.info(f"Analysis already exists for report {report_id}")
            return existing_analysis
            
        # Get similar reports for context
        logger.info("Finding similar reports for context")
        similar_reports_chunks = search_reports(
            query=report.report_text,
            employee_id=report.employee_id,
            top_k=3
        )
        similar_texts_chunks = [r.get("text", "") for r in similar_reports_chunks]
        
        # Rerieving Full Reports
        similar_texts = get_reports_for_vector_results(similar_texts_chunks)
        
        # Get LLM service
        llm_service = get_llm_service()
        
        # Generate analysis
        logger.info("Calling LLM service for analysis")
        analysis_result = llm_service.analyze_report(report.report_text, similar_texts)
        
        # Extract specific fields
        sentiment = analysis_result.get("sentiment", "neutral").lower()
        risk_level = analysis_result.get("risk_level", "low").lower()
        risk_explanation = analysis_result.get("risk_explanation", "No explanation provided")

        # Map sentiment to score
        sentiment_mapping = {"positive": 0.8, "neutral": 0.5, "negative": 0.2}
        sentiment_score = sentiment_mapping.get(sentiment, 0.5)

        
        # Create analysis record
        logger.info("Creating analysis database record")
        new_analysis = EmployeeAnalysis(
            report_id=report.report_id,
            employee_id=report.employee_id,
            sentiment_score=sentiment_score,
            risk_level=risk_level,
            risk_explanation=risk_explanation,
            full_analysis_json=analysis_result,
        )
        
        # Save to database
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        logger.info(f"Analysis saved with ID: {new_analysis.analysis_id}")
        
        return new_analysis
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating analysis: {str(e)}")
    


