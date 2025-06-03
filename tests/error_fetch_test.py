"""
Test script to verify if import errors are being fetched correctly from the database.
This script runs automatically without requiring user input.
"""
import sys
import os
import json
import uuid
from datetime import datetime
import requests

# Add parent directory to path so we can import our application modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database
from app.models.import_models import CSVImportJob, ImportError, ImportStatus
from app.services.csv_import_service import get_csv_import_service
from app.core.logger import logger

def test_direct_db_query(job_id, page=1, page_size=100):
    """Test fetching errors directly from the database."""
    logger.info(f"Testing direct DB query for job_id: {job_id}")
    
    db = get_database().create_session()
    try:
        # Verify the job exists
        job = db.query(CSVImportJob).filter(CSVImportJob.job_id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database!")
            return False, None
        
        logger.info(f"Found job: {job.filename} (status: {job.status}, error count: {job.error_count})")
        
        # Get total error count
        total_errors = db.query(ImportError).filter(ImportError.job_id == job_id).count()
        logger.info(f"Total errors in database for job {job_id}: {total_errors}")
        
        # Get paginated errors
        offset = (page - 1) * page_size
        errors = db.query(ImportError).filter(
            ImportError.job_id == job_id
        ).order_by(
            ImportError.row_number
        ).offset(offset).limit(page_size).all()
        
        logger.info(f"Retrieved {len(errors)} errors from database (page {page}, page_size {page_size})")
        
        # Print some sample errors if available
        for i, error in enumerate(errors[:5]):  # Show first 5 errors
            logger.info(f"Error {i+1}: Row {error.row_number}, Field: {error.field_name}, Message: {error.error_message}")
        
        return True, {"total": total_errors, "errors": errors}
    
    except Exception as e:
        logger.error(f"Error querying database: {str(e)}")
        return False, None
    finally:
        db.close()

def test_service_error_fetch(job_id, page=1, page_size=100):
    """Test fetching errors via the CSVImportService."""
    logger.info(f"Testing service error fetch for job_id: {job_id}")
    
    try:
        import_service = get_csv_import_service()
        
        # First check if job exists
        job = import_service.get_import_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found via import service!")
            return False, None
        
        logger.info(f"Found job via service: {job['filename']} (status: {job['status']}, error count: {job['error_count']})")
        
        # Get errors via service
        total, errors = import_service.get_job_errors(job_id, page, page_size)
        
        logger.info(f"Retrieved {len(errors)} errors via service (total: {total})")
        
        # Print some sample errors if available
        for i, error in enumerate(errors[:5]):  # Show first 5 errors
            logger.info(f"Error {i+1}: Row {error['row_number']}, Field: {error['field_name']}, Message: {error['error_message']}")
        
        return True, {"total": total, "errors": errors}
    
    except Exception as e:
        logger.error(f"Error using import service: {str(e)}")
        return False, None

def test_api_error_fetch(job_id, base_url="http://localhost:8000", page=1, page_size=100):
    """Test fetching errors via the API endpoint."""
    logger.info(f"Testing API error fetch for job_id: {job_id}")
    
    try:
        # First check if job exists via API
        job_response = requests.get(f"{base_url}/imports/{job_id}")
        
        if job_response.status_code != 200:
            logger.error(f"Job {job_id} not found via API! Status: {job_response.status_code}")
            return False, None
        
        job_data = job_response.json()
        logger.info(f"Found job via API: {job_data['filename']} (status: {job_data['status']}, error count: {job_data['error_count']})")
        
        # Get errors via API
        errors_response = requests.get(f"{base_url}/imports/{job_id}/errors?page={page}&page_size={page_size}")
        
        if errors_response.status_code != 200:
            logger.error(f"Failed to get errors via API! Status: {errors_response.status_code}")
            return False, None
        
        errors_data = errors_response.json()
        logger.info(f"Retrieved {len(errors_data['errors'])} errors via API (total: {errors_data['total']})")
        
        # Print some sample errors if available
        for i, error in enumerate(errors_data['errors'][:5]):  # Show first 5 errors
            logger.info(f"Error {i+1}: Row {error['row_number']}, Field: {error['field_name']}, Message: {error['error_message']}")
        
        return True, errors_data
    
    except Exception as e:
        logger.error(f"Error using API: {str(e)}")
        return False, None

def find_job_with_errors():
    """Find a recent job with errors to test."""
    logger.info("Looking for a job with errors to test...")
    
    db = get_database().create_session()
    try:
        # Find jobs with errors, ordered by most recent first
        jobs_with_errors = db.query(CSVImportJob).filter(
            CSVImportJob.error_count > 0
        ).order_by(
            CSVImportJob.submitted_at.desc()
        ).limit(5).all()
        
        if not jobs_with_errors:
            logger.info("No jobs with errors found.")
            # Fall back to any recent job
            return find_any_recent_job()
        
        # Return the most recent job with errors
        job = jobs_with_errors[0]
        logger.info(f"Found job with errors: {job.job_id} - {job.filename} (error count: {job.error_count})")
        return str(job.job_id)
        
    except Exception as e:
        logger.error(f"Error finding job with errors: {str(e)}")
        return None
    finally:
        db.close()

def find_any_recent_job():
    """Find any recent job if no jobs with errors are found."""
    logger.info("Looking for any recent job...")
    
    db = get_database().create_session()
    try:
        # Get the most recent job
        job = db.query(CSVImportJob).order_by(
            CSVImportJob.submitted_at.desc()
        ).first()
        
        if not job:
            logger.error("No import jobs found in database.")
            return None
        
        logger.info(f"Found recent job: {job.job_id} - {job.filename}")
        return str(job.job_id)
        
    except Exception as e:
        logger.error(f"Error finding recent job: {str(e)}")
        return None
    finally:
        db.close()

def check_error_table():
    """Check if the import_errors table has any data."""
    logger.info("Checking if there are any errors in the database...")
    
    db = get_database().create_session()
    try:
        # Count errors in the table
        error_count = db.query(ImportError).count()
        logger.info(f"Total errors in database: {error_count}")
        
        if error_count > 0:
            # Get a sample error to verify the structure
            sample_error = db.query(ImportError).first()
            logger.info(f"Sample error from database:")
            logger.info(f"  ID: {sample_error.error_id}")
            logger.info(f"  Job ID: {sample_error.job_id}")
            logger.info(f"  Row: {sample_error.row_number}")
            logger.info(f"  Field: {sample_error.field_name}")
            logger.info(f"  Message: {sample_error.error_message}")
            
            # Get job associated with this error
            job = db.query(CSVImportJob).filter(
                CSVImportJob.job_id == sample_error.job_id
            ).first()
            
            if job:
                logger.info(f"  From job: {job.filename} (status: {job.status})")
            else:
                logger.info("  No associated job found (orphaned error)")
        
        return error_count
        
    except Exception as e:
        logger.error(f"Error checking error table: {str(e)}")
        return 0
    finally:
        db.close()

def run_automatic_tests():
    """Run all tests automatically."""
    logger.info("Starting automatic error fetch tests")
    
    # First check if there are any errors in the database
    error_count = check_error_table()
    
    if error_count == 0:
        logger.warning("No errors found in database. Tests may not be meaningful.")
    
    # Find a job to test
    job_id = find_job_with_errors()
    
    if not job_id:
        logger.error("Could not find a job to test. Exiting.")
        return
    
    logger.info(f"Running tests for job ID: {job_id}")
    
    # Run database direct query test
    db_success, db_data = test_direct_db_query(job_id)
    
    # Run service test
    service_success, service_data = test_service_error_fetch(job_id)
    
    # Try to run API test if server might be running
    api_url = "http://localhost:8000"  # Default URL, adjust if needed
    try:
        requests.get(f"{api_url}/health", timeout=1)  # Quick check if API is available
        api_success, api_data = test_api_error_fetch(job_id, api_url)
    except requests.RequestException:
        logger.warning(f"API server not available at {api_url}. Skipping API test.")
        api_success, api_data = False, None
    
    # Print summary of test results
    logger.info("\n" + "="*50)
    logger.info("ERROR FETCH TEST RESULTS")
    logger.info("="*50)
    
    if db_success:
        db_count = db_data["total"]
        logger.info(f"Database Test: PASSED - Found {db_count} errors")
    else:
        logger.info("Database Test: FAILED - Could not retrieve errors")
    
    if service_success:
        service_count = service_data["total"]
        logger.info(f"Service Test: PASSED - Found {service_count} errors")
    else:
        logger.info("Service Test: FAILED - Could not retrieve errors")
    
    if api_success:
        api_count = api_data["total"]
        logger.info(f"API Test: PASSED - Found {api_count} errors")
    else:
        logger.info("API Test: SKIPPED or FAILED - API might not be running")
    
    # Compare results
    if db_success and service_success:
        db_count = db_data["total"]
        service_count = service_data["total"]
        
        if db_count == service_count:
            logger.info(f"MATCH: Database and service report same error count: {db_count}")
        else:
            logger.error(f"MISMATCH: Database reports {db_count} errors, service reports {service_count} errors")
    
    if api_success and db_success:
        api_count = api_data["total"]
        db_count = db_data["total"]
        
        if api_count == db_count:
            logger.info(f"MATCH: API and database report same error count: {db_count}")
        else:
            logger.error(f"MISMATCH: API reports {api_count} errors, database reports {db_count} errors")
    
    # Show detailed comparison of first error if available
    if db_success and service_success and db_data["total"] > 0 and service_data["total"] > 0:
        logger.info("\nComparing first error from DB and service:")
        db_error = db_data["errors"][0]
        service_error = service_data["errors"][0]
        
        logger.info(f"DB error: Row {db_error.row_number}, Message: {db_error.error_message}")
        logger.info(f"Service error: Row {service_error['row_number']}, Message: {service_error['error_message']}")
        
        # Check if the errors match by row number
        if db_error.row_number == service_error['row_number']:
            logger.info("First error row numbers match")
        else:
            logger.error("First error row numbers do not match")
            
        # Check if fields match
        if db_error.field_name == service_error['field_name']:
            logger.info("First error field names match")
        else:
            if db_error.field_name is None and service_error['field_name'] is None:
                logger.info("First error field names both null")
            else:
                logger.error(f"First error field names do not match: DB={db_error.field_name}, Service={service_error['field_name']}")
        
        # Check if messages match
        if db_error.error_message == service_error['error_message']:
            logger.info("First error messages match")
        else:
            logger.error("First error messages do not match")
            logger.error(f"DB: {db_error.error_message}")
            logger.error(f"Service: {service_error['error_message']}")

if __name__ == "__main__":
    print("CSV Import Error Fetch Tester - Automatic Mode")
    print("============================================")
    
    # Run all tests automatically
    run_automatic_tests()
