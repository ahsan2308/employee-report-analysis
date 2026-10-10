"""
Test script for employee analysis database storage functionality.
This script tests whether analysis results are properly stored in the database.
"""
import sys
import os
import uuid
from datetime import date, datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.models.db_models import Employee, Report, EmployeeAnalysis
from app.services.llm_service import get_llm_service
from app.database import get_database
from app.core.logger import logger

def create_test_employee() -> Employee:
    """Create a test employee record."""
    print("\n=== Creating Test Employee ===")
    
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Check if test employee exists
        test_employee = session.query(Employee).filter(Employee.name == "Test Employee").first()
        
        if test_employee:
            print(f"Using existing test employee: ID={test_employee.id}, Name={test_employee.name}")
            return test_employee
            
        # Create new test employee
        test_employee = Employee(
            name="Test Employee",
            wing="Test Wing",
            position="Test Position"
        )
        session.add(test_employee)
        session.commit()
        session.refresh(test_employee)
        
        print(f"Created new test employee: ID={test_employee.id}, Name={test_employee.name}")
        return test_employee

def create_test_report(employee_id: int) -> Report:
    """Create a test report for the given employee."""
    print("\n=== Creating Test Report ===")
    
    # Sample report text
    report_text = """
    Monthly Report - June 2023
    
    Accomplishments:
    - Completed the backend API for the customer portal
    - Fixed 5 critical bugs in the payment processing system
    - Helped onboard new team member
    
    Challenges:
    - Integration with legacy systems is taking longer than expected
    - Limited resources for testing all edge cases
    
    Next Month Goals:
    - Complete the frontend components for customer dashboard
    - Begin work on reporting feature
    - Continue mentoring junior developers
    """
    
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Create a unique report for this test run
        test_report = Report(
            employee_id=employee_id,
            report_date=date.today(),
            report_text=report_text
        )
        
        try:
            session.add(test_report)
            session.commit()
            session.refresh(test_report)
            
            print(f"Created test report: ID={test_report.report_id}")
            return test_report
        except Exception as e:
            session.rollback()
            print(f"Error creating test report: {e}")
            
            # If a unique constraint violation occurred, find an existing report
            existing_report = session.query(Report).filter(Report.employee_id == employee_id).first()
            if existing_report:
                print(f"Using existing report: ID={existing_report.report_id}")
                return existing_report
            raise

def analyze_report(report: Report) -> Dict[str, Any]:
    """Generate analysis for the report using LLM service."""
    print("\n=== Analyzing Report ===")
    
    llm_service = get_llm_service(model="llama3.1:8b")
    
    result = llm_service.analyze_report(report.report_text)
    
    print("Analysis generated successfully")
    return result

def store_analysis(report_id: uuid.UUID, employee_id: int, analysis_result: Dict[str, Any]) -> EmployeeAnalysis:
    """Store the analysis result in the database."""
    print("\n=== Storing Analysis in Database ===")
    
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Extract fields that match our simplified model
        sentiment_value = None
        if "sentiment" in analysis_result:
            # Map sentiment string to numeric score
            sentiment_mapping = {"positive": 0.8, "neutral": 0.5, "negative": 0.2}
            sentiment_value = sentiment_mapping.get(analysis_result["sentiment"], 0.5)
        
        risk_level = analysis_result.get("risk_level")
        risk_explanation = analysis_result.get("risk_explanation")
        
        # Create analysis record
        analysis = EmployeeAnalysis(
            report_id=report_id,
            employee_id=employee_id,
            sentiment_score=sentiment_value,
            risk_level=risk_level,
            risk_explanation=risk_explanation,
            full_analysis_json=analysis_result
        )
        
        session.add(analysis)
        session.commit()
        session.refresh(analysis)
        
        print(f"Analysis stored with ID: {analysis.analysis_id}")
        return analysis

def verify_analysis_storage(analysis_id: int) -> bool:
    """Verify the analysis was properly stored in the database."""
    print("\n=== Verifying Analysis Storage ===")
    
    db_instance = get_database()
    with db_instance.create_session() as session:
        analysis = session.query(EmployeeAnalysis).get(analysis_id)
        
        if not analysis:
            print(f"ERROR: Analysis with ID {analysis_id} not found in database!")
            return False
            
        print("Analysis retrieved from database:")
        print(f"  ID: {analysis.analysis_id}")
        print(f"  Report ID: {analysis.report_id}")
        print(f"  Employee ID: {analysis.employee_id}")
        print(f"  Sentiment Score: {analysis.sentiment_score}")
        print(f"  Risk Level: {analysis.risk_level}")
        print(f"  Analysis Date: {analysis.analysis_date}")
        print(f"  Topics (from JSON): {analysis.full_analysis_json.get('topics', [])}")
        
        return True

def run_test():
    """Run the full test sequence."""
    try:
        # Create test data
        test_employee = create_test_employee()
        test_report = create_test_report(test_employee.id)
        
        # Generate and store analysis
        analysis_result = analyze_report(test_report)
        stored_analysis = store_analysis(
            report_id=test_report.report_id, 
            employee_id=test_employee.id, 
            analysis_result=analysis_result
        )
        
        # Verify storage
        success = verify_analysis_storage(stored_analysis.analysis_id)
        
        if success:
            print("\n=== TEST PASSED: Analysis was properly stored in the database ===")
        else:
            print("\n=== TEST FAILED: Analysis was not properly stored ===")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\n=== TEST FAILED: {e} ===")

if __name__ == "__main__":
    print("Starting Employee Analysis Storage Test")
    print("======================================")
    run_test()
