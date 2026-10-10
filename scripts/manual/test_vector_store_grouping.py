"""
Test script to verify the vector store group by functionality with longer reports.
This script compares search results with and without the group_by_report parameter.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Ensure the parent directory is in the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.vector_store_service import add_report_to_vector_store, search_reports, setup_collection
from app.db.database import get_database
from app.models.db_models import Employee, Report
from app.core.logger import logger

# Test data
EMPLOYEE_ID = 3482  # Use the specified employee ID
TEST_QUERY = "performance issues with coding tasks and project delays"
CLEANUP_AFTER_TEST = True  # Clean up test data when done

def ensure_test_employee_exists() -> bool:
    """
    Ensure the test employee with ID 3482 exists in the database.
    Creates the employee if it doesn't exist.
    """
    db_instance = get_database()
    with db_instance.create_session() as session:
        # Check if employee exists
        employee = session.query(Employee).filter(Employee.id == EMPLOYEE_ID).first()
        if employee:
            logger.info(f"Using existing employee with ID {EMPLOYEE_ID}")
            return True
            
        # Create employee if it doesn't exist
        try:
            new_employee = Employee(
                id=EMPLOYEE_ID,
                name="Test Employee",
                wing="IT Department",
                position="Software Developer"
            )
            session.add(new_employee)
            session.commit()
            logger.info(f"Created test employee with ID {EMPLOYEE_ID}")
            return True
        except Exception as e:
            logger.error(f"Failed to create test employee: {e}")
            return False

def create_test_reports() -> List[Dict[str, Any]]:
    """
    Create test reports in the database and return their details.
    """
    base_date = datetime.now().date()
    
    # Prepare report data
    report_texts = [
        """
        Weekly Performance Review - Software Engineer
        
        The employee has shown mixed results this month in their development activities. Their UI work on the customer portal has been excellent, with all assigned components delivered ahead of schedule. The designs are clean and the implementation matches specifications perfectly.
        
        However, there are some performance issues with coding tasks related to the backend services that need attention. The database optimization work was delayed by two days, and the code quality doesn't meet our standards. Several pull requests had to be sent back for revisions due to inefficient algorithms and missing test cases.
        
        They are struggling with complex algorithms and code optimization, particularly when working with our legacy codebase. The refactoring task for the payment processing module was only partially completed, and what was delivered contains performance bottlenecks.
        
        On the positive side, their documentation is excellent and they collaborate well with the team. Their knowledge sharing sessions have been well-received, and they've been helpful in onboarding the new team members. They've also been proactive in suggesting improvements to our development workflow.
        
        In terms of project management, they need to improve their estimation skills. Several tasks took significantly longer than estimated, which affected our sprint planning. We should consider providing additional training on agile estimation techniques.
        
        Goals for next month:
        1. Complete the database optimization work with documented performance improvements
        2. Implement at least two of the suggested workflow improvements
        3. Attend the advanced algorithms workshop scheduled for next week
        4. Improve estimation accuracy by breaking down tasks more granularly
        """,
        
        """
        Monthly Performance Review - Software Engineer
        
        Overall, this has been a decent month for the employee. They've completed most assigned tasks and have been a reliable team member. Their work on the reporting dashboard was particularly impressive, with the new visualization components receiving positive feedback from stakeholders.
        
        There has been improvement in meeting deadlines compared to last month, but we still see occasional performance issues. The deployment automation pipeline they were tasked with building is behind schedule by a week. This has impacted the DevOps team's ability to proceed with their infrastructure upgrades.
        
        The employee needs more training on coding tasks, especially in the area of testing and debugging. Their unit test coverage is below our target of 80%, averaging around 65% for their components. Several bugs have been discovered in production that should have been caught by proper testing.
        
        Project delays have become a recurring theme, though not always due to their own work. In some cases, dependencies on other teams have caused bottlenecks. However, they need to be more proactive in escalating these issues earlier rather than waiting until deadlines are imminent.
        
        They're very responsive to feedback and have a positive attitude. After our discussion last month about code quality, there has been a noticeable improvement in the structure and readability of their code. They've also started contributing to our internal documentation, which has been helpful.
        
        Areas for improvement:
        1. Increase unit test coverage to at least 80%
        2. Implement more robust error handling in their code
        3. Be more proactive in communicating potential delays
        4. Complete the assigned LinkedIn Learning courses on advanced JavaScript
        
        I recommend scheduling bi-weekly check-ins rather than monthly to provide more timely feedback and support.
        """,
        
        """
        Quarterly Performance Review - Software Engineer
        
        This quarter has been challenging for the employee and the team as a whole. The product launch timeline has been aggressive, and everyone has been under pressure to deliver.
        
        The employee is behind on several key projects. The API gateway migration that was scheduled to be completed by the end of the quarter is only about 60% done. This has created a bottleneck for the mobile team who are waiting on these endpoints.
        
        The main concern is with their coding tasks where they consistently miss requirements or misinterpret specifications. There have been multiple instances where features had to be reworked after QA or product review. This has contributed to significant project delays and has affected team morale.
        
        There are significant performance issues that need to be addressed urgently in their code. The reporting module they developed is experiencing timeouts when processing larger datasets, and the caching implementation is not working as expected. These issues are affecting our SLA commitments to customers.
        
        Communication has been another area of concern. They often work in isolation without providing status updates, making it difficult for me as their manager to have visibility into potential problems. When issues do arise, they're sometimes defensive rather than solution-oriented.
        
        On a positive note, they did excellent work on the authentication service refactoring. The code is clean, well-documented, and the performance improvements are measurable. This demonstrates their capability when they're working on tasks that align well with their strengths.
        
        We've scheduled additional training sessions and assigned a senior developer as a mentor to help them improve. I'm also implementing a more structured check-in process to ensure better communication and earlier identification of potential issues.
        
        Development plan:
        1. Complete a code review workshop with the architecture team
        2. Pair programming sessions with senior developers twice weekly
        3. Implement a daily standup specifically for the API gateway project
        4. Take the advanced troubleshooting course offered by our L&D team
        
        We'll reassess progress in one month to determine if additional interventions are needed.
        """
    ]
    
    # Create reports in the database
    db_instance = get_database()
    created_reports = []
    
    with db_instance.create_session() as session:
        # Delete any existing test reports for this employee to start fresh
        existing_reports = session.query(Report).filter(Report.employee_id == EMPLOYEE_ID).all()
        for report in existing_reports:
            session.delete(report)
        
        # Create new test reports
        for i, report_text in enumerate(report_texts):
            report_date = base_date - timedelta(days=30 * i)
            new_report = Report(
                employee_id=EMPLOYEE_ID,
                report_date=report_date,
                report_text=report_text
            )
            session.add(new_report)
            session.flush()  # Flush to get the generated report_id
            
            # Add to our tracking list
            created_reports.append({
                "report_id": str(new_report.report_id),
                "employee_id": EMPLOYEE_ID,
                "report_date": report_date.strftime("%Y-%m-%d"),
                "report_text": report_text
            })
        
        session.commit()
    
    logger.info(f"Created {len(created_reports)} test reports with IDs: {[r['report_id'] for r in created_reports]}")
    return created_reports

def cleanup_test_data():
    """Clean up all test data created for this test."""
    if not CLEANUP_AFTER_TEST:
        logger.info("Skipping cleanup as CLEANUP_AFTER_TEST is False")
        return
        
    logger.info("Cleaning up test data...")
    db_instance = get_database()
    
    with db_instance.create_session() as session:
        # Delete reports
        reports = session.query(Report).filter(Report.employee_id == EMPLOYEE_ID).all()
        report_ids = [str(r.report_id) for r in reports]
        
        for report in reports:
            session.delete(report)
        
        session.commit()
        logger.info(f"Deleted {len(reports)} test reports")
        
        # Note: The employee is kept for potential future tests

def run_comparison_test(reports: List[Dict[str, Any]]) -> None:
    """
    Run search tests both with and without the group_by_report parameter
    and compare the results to show the difference.
    """
    # First, ensure the collection exists
    if not setup_collection():
        logger.error("Failed to setup vector collection")
        return
    
    # Add test reports to vector store
    if not add_report_to_vector_store(reports=reports):
        logger.error("Failed to add test reports to vector store")
        return
    
    logger.info("Successfully added test reports to vector store")
    
    # Run search without grouping
    logger.info(f"Searching for: '{TEST_QUERY}' WITHOUT grouping")
    results_without_grouping = search_reports(
        query=TEST_QUERY,
        employee_id=EMPLOYEE_ID,
        top_k=50,  # Increased to see more results
        score_threshold=0.1,  # Lower threshold to ensure we get results
        bypass_threshold=True,
        group_by_report=False
    )
    
    # Run search with grouping
    logger.info(f"Searching for: '{TEST_QUERY}' WITH grouping")
    results_with_grouping = search_reports(
        query=TEST_QUERY,
        employee_id=EMPLOYEE_ID,
        top_k=50,  # Increased to see more results
        score_threshold=0.1,  # Lower threshold to ensure we get results
        bypass_threshold=True,
        group_by_report=True
    )
    
    # Print results for comparison
    print("\n" + "="*80)
    print("SEARCH RESULTS COMPARISON")
    print("="*80)
    
    print(f"\nWITHOUT GROUPING: Found {len(results_without_grouping)} results")
    # Count how many results we get per report
    report_counts_without = {}
    for r in results_without_grouping:
        report_id = r.get("report_id", "unknown")
        report_counts_without[report_id] = report_counts_without.get(report_id, 0) + 1
    
    for report_id, count in report_counts_without.items():
        print(f"Report {report_id}: {count} chunks returned")
    
    print("\nResults detail:")
    for i, result in enumerate(results_without_grouping):
        print(f"{i+1}. Score: {result.get('score', 0):.4f}, Report ID: {result.get('report_id', 'unknown')}")
        print(f"   Text: {result.get('text', '')[:100]}...")
    
    print(f"\nWITH GROUPING: Found {len(results_with_grouping)} results")
    # With grouping, we should have at most one result per report
    report_counts_with = {}
    for r in results_with_grouping:
        report_id = r.get("report_id", "unknown")
        report_counts_with[report_id] = report_counts_with.get(report_id, 0) + 1
    
    for report_id, count in report_counts_with.items():
        print(f"Report {report_id}: {count} chunks returned")
        # Verify we're getting only one chunk per report
        if count > 1:
            print(f"WARNING: Got {count} chunks for report {report_id} even with grouping!")
    
    print("\nResults detail:")
    for i, result in enumerate(results_with_grouping):
        print(f"{i+1}. Score: {result.get('score', 0):.4f}, Report ID: {result.get('report_id', 'unknown')}")
        print(f"   Text: {result.get('text', '')[:100]}...")
    
    # Summarize the difference
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"WITHOUT grouping: {len(results_without_grouping)} total results from {len(report_counts_without)} unique reports")
    print(f"WITH grouping: {len(results_with_grouping)} total results from {len(report_counts_with)} unique reports")
    
    # Check which mode provided more unique reports
    if len(report_counts_with) > len(report_counts_without):
        print(f"GROUP BY provided more diverse results: {len(report_counts_with)} unique reports vs {len(report_counts_without)} without grouping")
    
    # Verify the key benefit: grouping should return at most one chunk per report
    without_multiple_chunks = sum(1 for count in report_counts_without.values() if count > 1)
    with_multiple_chunks = sum(1 for count in report_counts_with.values() if count > 1)
    
    print(f"WITHOUT grouping: {without_multiple_chunks} reports had multiple chunks in results")
    print(f"WITH grouping: {with_multiple_chunks} reports had multiple chunks in results")
    
    if with_multiple_chunks == 0:
        print("\n✅ SUCCESS: Group by functionality is working correctly!")
    else:
        print("\n❌ FAILURE: Group by functionality is NOT working correctly.")

if __name__ == "__main__":
    logger.info("Starting vector store group by test with longer reports")
    
    try:
        # First ensure our test employee exists
        if not ensure_test_employee_exists():
            logger.error("Failed to ensure test employee exists. Aborting test.")
            sys.exit(1)
            
        # Create test reports in the database
        test_reports = create_test_reports()
        
        # Run the comparison test
        run_comparison_test(test_reports)
        
        # Clean up test data
        cleanup_test_data()
        
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Attempt cleanup even if test fails
        try:
            cleanup_test_data()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}")
