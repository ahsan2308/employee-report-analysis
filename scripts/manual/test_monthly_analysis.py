"""
Test script for Monthly Analysis functionality.

This script tests the complete end-to-end workflow for monthly analysis:
1. Create a test employee
2. Create test weekly reports for a month
3. Submit monthly analysis request
4. Poll for task completion
5. Retrieve and validate monthly analysis results
6. Test all monthly analysis endpoints
7. Clean up test data
"""
import requests
import json
import time
from datetime import datetime, timedelta, date
import uuid
import sys
import os
import random

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change to match your API server
MAX_WAIT_TIME = 180  # Maximum time to wait for task completion (seconds)
POLL_INTERVAL = 3    # Seconds between polling for task status

# Colors for console output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def log_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def log_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def log_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def log_header(message):
    print(f"\n{Colors.BOLD}{message}{Colors.END}")

# Helper functions
def create_test_employee():
    """Create a test employee and return the employee data."""
    log_header("Creating test employee")
    
    # Generate a unique name to avoid conflicts
    timestamp = int(time.time())
    employee_data = {
        "name": f"Test Employee {timestamp}",
        "wing": "Test Wing",
        "position": "Test Position"
    }
    
    response = requests.post(f"{API_BASE_URL}/employees/", json=employee_data)
    
    if response.status_code != 200:
        log_error(f"Failed to create test employee: {response.text}")
        sys.exit(1)
    
    employee = response.json()["employee"]
    log_success(f"Created test employee: {employee['name']} (ID: {employee['id']})")
    return employee

def create_test_reports(employee_id, year, month):
    """Create test weekly reports for the given month and return report IDs."""
    log_header(f"Creating test reports for {year}-{month}")
    
    # Determine the number of days in the month
    if month == 2:
        days_in_month = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
    elif month in [4, 6, 9, 11]:
        days_in_month = 30
    else:
        days_in_month = 31
    
    # Create 4 weekly reports within the month
    report_ids = []
    start_day = 1
    for week in range(4):
        # Calculate report date for this week
        report_day = min(start_day + (week * 7), days_in_month)
        report_date = date(year, month, report_day)
        
        # Generate random sentiment (positive/neutral/negative) for variety
        sentiment = random.choice(["positive", "neutral", "negative"])
        
        # Generate appropriate confidence level based on sentiment
        if sentiment == "positive":
            confidence = random.randint(4, 5)
        elif sentiment == "neutral":
            confidence = random.randint(3, 4)
        else:
            confidence = random.randint(1, 3)
        
        # Generate tasks with variety for interesting analysis
        tasks_completed = [
            "Completed weekly status report",
            f"Finalized project documentation for phase {week+1}",
            f"Attended team meeting on {report_date.strftime('%A')}",
            f"Reviewed code for feature #{random.randint(100, 999)}"
        ]
        
        # Add some challenges that persist across reports
        recurring_challenges = [
            "Limited access to test environment",
            "Waiting for stakeholder feedback",
            "Technical debt in legacy system"
        ]
        
        # Add some unique challenges
        unique_challenges = [
            f"Unexpected issue with database migration on {report_date.strftime('%A')}",
            f"Meeting rescheduled due to conflicting priorities",
            f"Resource allocation constraints for phase {week+1}"
        ]
        
        # Choose challenges based on week number for consistency
        if week == 0:
            challenges = recurring_challenges[:2] + [unique_challenges[0]]
        elif week == 1:
            challenges = recurring_challenges[:2] + [unique_challenges[1]]
        elif week == 2:
            challenges = recurring_challenges[1:] + [unique_challenges[2]]
        else:
            challenges = [recurring_challenges[0], recurring_challenges[2]]
        
        # Generate report text with a specific format
        report_text = f"""
Key Tasks: {'; '.join(tasks_completed)}

Impact: Completed all scheduled tasks on time. Made progress on {random.choice(['Project Alpha', 'Project Beta', 'Project Gamma'])}. Received positive feedback from team lead.

Challenges: {'; '.join(challenges)}

Support: Need access to additional {random.choice(['documentation', 'resources', 'training'])} for upcoming tasks.

Planned Tasks: Continue work on current project; Prepare for next sprint planning; Schedule demo with stakeholders.

Confidence Level: {confidence}

Nothing to Report Reason: 
"""
        
        # Submit the report
        report_data = {
            "employee_id": employee_id,
            "report_date": report_date.isoformat(),
            "report_text": report_text
        }
        
        response = requests.post(f"{API_BASE_URL}/reports/create", json=report_data)
        
        if response.status_code != 200:
            log_error(f"Failed to create test report for week {week+1}: {response.text}")
            continue
        
        report_id = response.json()["report"]["report_id"]
        report_ids.append(report_id)
        log_success(f"Created report for {report_date.isoformat()} (ID: {report_id})")
        
        # Analyze each report to populate weekly analyses
        analysis_response = requests.post(f"{API_BASE_URL}/analyses/analyze/{report_id}")
        
        if analysis_response.status_code != 200:
            log_warning(f"Failed to submit analysis for report {report_id}: {analysis_response.text}")
            continue
        
        task_id = analysis_response.json().get("task_id")
        log_info(f"Submitted analysis task {task_id} for report {report_id}")
        
        # Wait for analysis to complete
        log_info(f"Waiting for analysis of report {report_id} to complete...")
        wait_for_task_completion(task_id)
    
    return report_ids

def submit_monthly_analysis(employee_id, year, month):
    """Submit a monthly analysis task and return the task ID."""
    log_header(f"Submitting monthly analysis for {year}-{month}")
    
    response = requests.post(
        f"{API_BASE_URL}/analyses/monthly/analyze",
        params={"employee_id": employee_id, "year": year, "month": month}
    )
    
    if response.status_code != 200:
        log_error(f"Failed to submit monthly analysis: {response.text}")
        return None
    
    task_id = response.json().get("task_id")
    log_success(f"Submitted monthly analysis task: {task_id}")
    return task_id

def wait_for_task_completion(task_id):
    """Poll the task status until it completes or times out."""
    start_time = time.time()
    done = False
    
    while not done and (time.time() - start_time) < MAX_WAIT_TIME:
        response = requests.get(f"{API_BASE_URL}/tasks/{task_id}")
        
        if response.status_code != 200:
            log_error(f"Failed to get task status: {response.text}")
            return False
        
        status = response.json()
        if status.get("is_complete"):
            log_success(f"Task {task_id} completed with status: {status.get('status')}")
            done = True
            break
        
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(POLL_INTERVAL)
    
    if not done:
        log_error(f"Task {task_id} did not complete within {MAX_WAIT_TIME} seconds")
        return False
    
    return True

def get_task_result(task_id):
    """Get the result of a completed task."""
    response = requests.get(f"{API_BASE_URL}/tasks/{task_id}/result")
    
    if response.status_code != 200:
        log_error(f"Failed to get task result: {response.text}")
        return None
    
    return response.json().get("result")

def validate_monthly_analysis(analysis):
    """Validate that the monthly analysis contains all required fields."""
    required_fields = [
        "analysis_id", "employee_id", "employee_name", "year", "month",
        "period_start", "period_end", "progress_trends", "monthly_achievements",
        "recurring_challenges", "consistency_assessment", "growth_indicators",
        "focus_areas", "monthly_risk_assessment", "strategic_recommendations",
        "monthly_summary"
    ]
    
    for field in required_fields:
        if field not in analysis:
            log_error(f"Missing required field in analysis: {field}")
            return False
    
    # Check nested fields
    if "risk_explanation" not in analysis["monthly_risk_assessment"]:
        log_error("Missing risk_explanation in monthly_risk_assessment")
        return False
    
    log_success("Monthly analysis validation passed")
    return True

def test_monthly_analysis_endpoints(employee_id, analysis_id, year, month):
    """Test various monthly analysis endpoints."""
    log_header("Testing monthly analysis endpoints")
    
    # Test get by ID
    log_info(f"Testing GET /analyses/monthly/{analysis_id}")
    response = requests.get(f"{API_BASE_URL}/analyses/monthly/{analysis_id}")
    
    if response.status_code != 200:
        log_error(f"Failed to get monthly analysis by ID: {response.text}")
    else:
        analysis = response.json()
        if validate_monthly_analysis(analysis):
            log_success(f"Successfully retrieved monthly analysis by ID {analysis_id}")
    
    # Test get all for employee
    log_info(f"Testing GET /analyses/monthly/employee/{employee_id}")
    response = requests.get(f"{API_BASE_URL}/analyses/monthly/employee/{employee_id}")
    
    if response.status_code != 200:
        log_error(f"Failed to get employee monthly analyses: {response.text}")
    else:
        analyses = response.json()
        if not analyses:
            log_warning(f"No monthly analyses found for employee {employee_id}")
        else:
            log_success(f"Successfully retrieved {len(analyses)} monthly analyses for employee {employee_id}")
    
    # Test get by employee/year/month
    log_info(f"Testing GET /analyses/monthly/employee/{employee_id}/{year}/{month}")
    response = requests.get(f"{API_BASE_URL}/analyses/monthly/employee/{employee_id}/{year}/{month}")
    
    if response.status_code != 200:
        log_error(f"Failed to get monthly analysis by period: {response.text}")
    else:
        analysis = response.json()
        if validate_monthly_analysis(analysis):
            log_success(f"Successfully retrieved monthly analysis for {year}-{month}")

def cleanup_test_data(employee_id):
    """Clean up all test data."""
    log_header("Cleaning up test data")
    
    # Note: In a real application, you would implement delete endpoints
    # Since we don't have those in this example, we'll just log a message
    log_warning("Test data cleanup would delete:")
    log_warning(f"- Employee ID: {employee_id}")
    log_warning(f"- All reports for employee {employee_id}")
    log_warning(f"- All analyses for employee {employee_id}")
    log_warning(f"- All monthly analyses for employee {employee_id}")
    
    # If you implement delete endpoints, you would call them here:
    # requests.delete(f"{API_BASE_URL}/employees/{employee_id}")

def run_test():
    """Run the complete test workflow."""
    log_header("STARTING MONTHLY ANALYSIS TEST")
    
    # Create test employee
    employee = create_test_employee()
    employee_id = employee["id"]
    
    # Set up test period (use previous month to ensure complete data)
    today = date.today()
    if today.month == 1:
        test_year = today.year - 1
        test_month = 12
    else:
        test_year = today.year
        test_month = today.month - 1
    
    # Create test reports
    report_ids = create_test_reports(employee_id, test_year, test_month)
    
    if not report_ids:
        log_error("Failed to create test reports, aborting test")
        return
    
    log_success(f"Created {len(report_ids)} test reports")
    
    # Wait for reports to be processed (give vector store time to index)
    log_info("Waiting for reports to be processed...")
    time.sleep(5)
    
    # Submit monthly analysis
    task_id = submit_monthly_analysis(employee_id, test_year, test_month)
    
    if not task_id:
        log_error("Failed to submit monthly analysis, aborting test")
        return
    
    # Wait for task completion
    log_info(f"Waiting for monthly analysis task {task_id} to complete...")
    if not wait_for_task_completion(task_id):
        log_error("Monthly analysis task did not complete successfully, aborting test")
        return
    
    # Get task result
    result = get_task_result(task_id)
    
    if not result:
        log_error("Failed to get monthly analysis result, aborting test")
        return
    
    analysis_id = result.get("analysis_id")
    log_success(f"Monthly analysis completed successfully (ID: {analysis_id})")
    
    # Test endpoints
    test_monthly_analysis_endpoints(employee_id, analysis_id, test_year, test_month)
    
    # Cleanup
    cleanup_test_data(employee_id)
    
    log_header("TEST COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    run_test()
