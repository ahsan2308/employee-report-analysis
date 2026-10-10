"""
Test script for CSV import API endpoints.

This script creates a temporary CSV file and tests the import endpoints with
detailed debugging information.
"""
import requests
import json
import time
import os
import sys
import tempfile
from datetime import date, timedelta
import csv
import uuid

# Add project root to path to allow imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# API configuration
BASE_URL = "http://127.0.0.1:8000"
IMPORTS_ENDPOINT = f"{BASE_URL}/imports"
UPLOAD_ENDPOINT = f"{IMPORTS_ENDPOINT}/upload"

# Test configuration
POLL_INTERVAL = 1.0  # seconds between status checks
MAX_POLLS = 60  # maximum number of status checks

def create_test_csv(include_errors=True):
    """
    Create a temporary CSV file for testing.
    
    Args:
        include_errors: Whether to include invalid rows for error testing
        
    Returns:
        Path to the temporary CSV file
    """
    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.csv')
    
    try:
        with os.fdopen(fd, 'w', newline='') as temp_file:
            writer = csv.writer(temp_file)
            
            # Write header row
            writer.writerow([
                'Employee_ID', 'Name', 'Designation', 'BPS', 'Office_Hierarchy',
                'From', 'To', 'Tasks_Completed', 'Impact', 'Challenges', 
                'Support_Required', 'Tasks_Planned', 'Confidence_Level', 'NTR'
            ])
            
            # Generate dynamic dates - ALWAYS use past dates
            today = date.today()
            one_week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            # Write valid rows as a list of lists for clarity
            valid_rows = [
                # Row 1: Complete data
                [
                    '101', 'John Doe', 'Software Engineer', 'BS-17', 'Technology>Development',
                    two_weeks_ago.isoformat(), one_week_ago.isoformat(),  # Note past dates
                    'Completed API documentation', 'Improved developer onboarding',
                    'Integration issues with legacy systems', 'More testing resources',
                    'Start on new authentication module', '4', ''
                ],
                
                # Row 2: Minimal required data
                [
                    '102', 'Jane Smith', 'Project Manager', '', 'Management',
                    one_week_ago.isoformat(), today.isoformat(),  # Note past dates
                    'Finalized project timeline', 'Project now on schedule',
                    '', '', 'Begin resource allocation', '', ''
                ],
                
                # Row 3: "Nothing to report"
                [
                    '103', 'Robert Brown', 'System Analyst', 'BS-16', 'Technology>Analysis',
                    one_week_ago.isoformat(), today.isoformat(),  # Note past dates
                    '', '', '', '', '', '', 'On leave'
                ]
            ]
            
            # Write all valid rows
            writer.writerows(valid_rows)
            
            # Add error rows if requested
            if include_errors:
                error_rows = [
                    # Row 4: Error - missing required Name field
                    [
                        '104', '', 'Quality Assurance', 'BS-15', 'QA Team',
                        one_week_ago.isoformat(), today.isoformat(),
                        'Completed test cases', 'Found 5 critical bugs',
                        '', '', '', '', ''
                    ],
                    
                    # Row 5: Error - invalid date format
                    [
                        '105', 'Sarah Connor', 'Security Specialist', 'BS-18', 'Security',
                        'invalid-date', today.isoformat(),  # Note the invalid date format
                        'Security audit', 'Identified vulnerabilities',
                        '', '', '', '', ''
                    ],
                    
                    # Row 6: Error - missing both tasks and NTR
                    [
                        '106', 'Tom Wilson', 'Database Admin', 'BS-17', 'Infrastructure',
                        one_week_ago.isoformat(), today.isoformat(),
                        '', '', '', '', '', '', ''  # No tasks and no NTR
                    ]
                ]
                writer.writerows(error_rows)
        
        print(f"Created test CSV file at {temp_path}")
        
        # Display file contents for debugging
        with open(temp_path, 'r') as f:
            content = f.read()
            print("\nCSV file contents:")
            print(content)
            
        return temp_path
    
    except Exception as e:
        print(f"Error creating test CSV: {str(e)}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

def print_response(response, label="Response"):
    """Print formatted response data."""
    print(f"\n--- {label} ---")
    print(f"Status Code: {response.status_code}")
    
    try:
        data = response.json()
        print("Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length', 'server', 'date']:
                print(f"  {key}: {value}")
        print("\nData:")
        print(json.dumps(data, indent=2))
        return data
    except ValueError:
        print("Not a JSON response:")
        print(response.text)
        return None

def upload_csv_file(file_path, options=None):
    """
    Upload a CSV file to the import endpoint.
    
    Args:
        file_path: Path to the CSV file
        options: Dictionary of form options (defaults provided if None)
        
    Returns:
        Job data if successful, None otherwise
    """
    if options is None:
        options = {
            'dry_run': False,
            'stop_on_error': False,
            'error_threshold_percent': 20.0,
            'chunk_size': 1000,
            'processing_mode': 'bulk'
        }
    
    print(f"\nUploading file {file_path} with options:")
    print(json.dumps(options, indent=2))
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                data=options
            )
        
        data = print_response(response, "Upload Response")
        
        if response.status_code == 200:
            print("\n✓ File uploaded successfully!")
            return data
        else:
            print("\n✗ Upload failed")
            return None
            
    except Exception as e:
        print(f"\n✗ Upload error: {str(e)}")
        return None

def get_job_status(job_id):
    """
    Get the status of an import job.
    
    Args:
        job_id: The ID of the import job
        
    Returns:
        Job data if successful, None otherwise
    """
    try:
        response = requests.get(f"{IMPORTS_ENDPOINT}/{job_id}")
        data = print_response(response, f"Job Status ({job_id})")
        
        if response.status_code == 200:
            return data
        else:
            print(f"\n✗ Failed to get job status")
            return None
            
    except Exception as e:
        print(f"\n✗ Error getting job status: {str(e)}")
        return None

def get_job_errors(job_id, page=1, page_size=100):
    """
    Get errors for an import job.
    
    Args:
        job_id: The ID of the import job
        page: Page number (default: 1)
        page_size: Number of errors per page (default: 100)
        
    Returns:
        Error data if successful, None otherwise
    """
    try:
        response = requests.get(
            f"{IMPORTS_ENDPOINT}/{job_id}/errors",
            params={'page': page, 'page_size': page_size}
        )
        
        data = print_response(response, f"Job Errors ({job_id})")
        
        if response.status_code == 200:
            return data
        else:
            print(f"\n✗ Failed to get job errors")
            return None
            
    except Exception as e:
        print(f"\n✗ Error getting job errors: {str(e)}")
        return None

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """
    Print a progress bar in the console.
    
    Args:
        iteration: Current iteration
        total: Total iterations
        prefix: Prefix string
        suffix: Suffix string
        length: Bar length
        fill: Fill character
    """
    percent = 100 * (iteration / float(total))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent:.1f}% {suffix}', end='\r')
    # Print newline on completion
    if iteration == total:
        print()

def monitor_job(job_id, timeout_seconds=60):
    """
    Monitor an import job until it completes, fails, or times out.
    
    Args:
        job_id: The ID of the import job
        timeout_seconds: Maximum time to wait for completion
        
    Returns:
        Final job data or None if timed out
    """
    print(f"\nMonitoring import job {job_id}...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout_seconds:
        job_data = get_job_status(job_id)
        if not job_data:
            print(f"Failed to get job data. Retrying...")
            time.sleep(POLL_INTERVAL)
            continue
            
        status = job_data.get('status')
        
        # Skip updating if status hasn't changed
        if status == last_status:
            time.sleep(POLL_INTERVAL)
            continue
            
        last_status = status
        
        # Check if job has completed or failed
        if status in ['completed', 'failed']:
            print(f"\nJob {status}!")
            return job_data
            
        # Update progress
        total = job_data.get('total_rows', 0)
        processed = job_data.get('processed_rows', 0)
        
        if total > 0:
            print_progress_bar(
                processed, total, 
                prefix=f'Processing {processed}/{total}:', 
                suffix=f'Status: {status} ({job_data.get("percent_complete")}%)'
            )
            
        time.sleep(POLL_INTERVAL)
    
    # If we get here, we've timed out
    print(f"\n⚠ Timeout reached after {timeout_seconds} seconds. Job may still be processing.")
    return get_job_status(job_id)  # Return final status

def test_csv_import():
    """Run the full CSV import test."""
    print("\n===== CSV Import API Test =====")
    
    try:
        # Create test CSV file
        csv_path = create_test_csv(include_errors=True)
        
        # Upload file
        job_data = upload_csv_file(csv_path)
        
        if not job_data:
            print("❌ Test failed: Couldn't upload file")
            return False
            
        # Get job ID
        job_id = job_data.get('job_id')
        
        if not job_id:
            print("❌ Test failed: No job ID in response")
            return False
            
        # Monitor job until completion
        final_job = monitor_job(job_id)
        
        if not final_job:
            print("❌ Test failed: Couldn't monitor job")
            return False
            
        # Check if we have errors
        if final_job.get('error_count', 0) > 0:
            print(f"\nJob completed with {final_job['error_count']} errors. Retrieving error details...")
            error_data = get_job_errors(job_id)
            
            if error_data and 'errors' in error_data:
                print("\n--- Error Details ---")
                for i, error in enumerate(error_data['errors']):
                    print(f"\nError {i+1}:")
                    print(f"  Row: {error['row_number']}")
                    print(f"  Field: {error['field_name'] or 'N/A'}")
                    print(f"  Message: {error['error_message']}")
                    
                    if error.get('row_data'):
                        print("  Row data:")
                        for key, value in error['row_data'].items():
                            print(f"    {key}: {value}")
        
        # Print final summary
        print("\n--- Import Summary ---")
        print(f"Total rows: {final_job.get('total_rows', 0)}")
        print(f"Successful rows: {final_job.get('successful_rows', 0)}")
        print(f"Failed rows: {final_job.get('error_count', 0)}")
        print(f"Employees created: {final_job.get('employees_created', 0)}")
        print(f"Employees updated: {final_job.get('employees_updated', 0)}")
        print(f"Reports created: {final_job.get('reports_created', 0)}")
        print(f"Reports updated: {final_job.get('reports_updated', 0)}")
        print(f"Percent complete: {final_job.get('percent_complete', 0)}%")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'csv_path' in locals() and os.path.exists(csv_path):
            try:
                os.unlink(csv_path)
                print(f"\nDeleted temporary file: {csv_path}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {str(e)}")

def test_dry_run():
    """Test CSV import with dry run option enabled."""
    print("\n===== CSV Import Dry Run Test =====")
    
    try:
        # Create test CSV file with no errors for cleaner test
        csv_path = create_test_csv(include_errors=False)
        
        # Upload file with dry run option
        job_data = upload_csv_file(csv_path, {'dry_run': True})
        
        if not job_data:
            print("❌ Test failed: Couldn't upload file")
            return False
            
        # Get job ID
        job_id = job_data.get('job_id')
        
        # Monitor job
        final_job = monitor_job(job_id)
        
        # Print summary - note for dry run we expect 'completed' status
        print("\n--- Dry Run Import Summary ---")
        print(f"Status: {final_job.get('status', 'unknown')}")
        print(f"Total rows: {final_job.get('total_rows', 0)}")
        print(f"Successful rows: {final_job.get('successful_rows', 0)}")
        print(f"Failed rows: {final_job.get('error_count', 0)}")
        
        # In dry run mode, we expect status to be 'completed' and no database changes
        if final_job.get('status') != 'completed':
            print(f"❌ Dry run test failed: Expected status 'completed' but got '{final_job.get('status')}'")
            return False
            
        if any([
            final_job.get('employees_created', 0) > 0,
            final_job.get('employees_updated', 0) > 0,
            final_job.get('reports_created', 0) > 0,
            final_job.get('reports_updated', 0) > 0
        ]):
            print("❌ Dry run test failed: Database was modified in dry run mode")
            return False
            
        print("\n✅ Dry run test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'csv_path' in locals() and os.path.exists(csv_path):
            try:
                os.unlink(csv_path)
                print(f"\nDeleted temporary file: {csv_path}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {str(e)}")

def test_stop_on_error():
    """Test CSV import with stop_on_error option enabled."""
    print("\n===== CSV Import Stop On Error Test =====")
    
    try:
        # Create test CSV file with errors
        csv_path = create_test_csv(include_errors=True)
        
        # Upload file with stop_on_error option
        job_data = upload_csv_file(csv_path, {'stop_on_error': True})
        
        if not job_data:
            print("❌ Test failed: Couldn't upload file")
            return False
            
        # Get job ID
        job_id = job_data.get('job_id')
        
        # Monitor job - should stop on first error
        final_job = monitor_job(job_id)
        
        # Check if job status is 'failed'
        if final_job.get('status') != 'failed':
            print(f"❌ Stop-on-error test failed: Expected status 'failed' but got '{final_job.get('status')}'")
            return False
            
        # Get errors - should have at least one
        error_data = get_job_errors(job_id)
        if not error_data or not error_data.get('errors'):
            print("❌ Stop-on-error test failed: No errors found")
            return False
            
        print("\n✅ Stop on error test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'csv_path' in locals() and os.path.exists(csv_path):
            try:
                os.unlink(csv_path)
                print(f"\nDeleted temporary file: {csv_path}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test CSV import API')
    parser.add_argument('--dry-run', action='store_true', help='Test with dry run mode enabled')
    parser.add_argument('--stop-on-error', action='store_true', help='Test with stop on error mode enabled')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    args = parser.parse_args()
    
    success = True
    
    if args.all:
        # Run all tests
        print("\n🔍 Running all tests...")
        success = test_csv_import() and success
        success = test_dry_run() and success
        success = test_stop_on_error() and success
        
        if success:
            print("\n✅ All tests passed successfully!")
        else:
            print("\n❌ One or more tests failed!")
    elif args.dry_run:
        success = test_dry_run()
    elif args.stop_on_error:
        success = test_stop_on_error()
    else:
        success = test_csv_import()
    
    sys.exit(0 if success else 1)
