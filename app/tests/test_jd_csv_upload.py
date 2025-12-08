"""
Comprehensive End-to-End Test Script for Job Description CSV Upload
"""

import time
import requests
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import csv
import io
import tempfile
import os
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import get_database
from app.models.db_models import Employee, EmployeeJobDescription
from app.models.import_models import CSVImportJob, ImportStatus
from app.core.logger import logger


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 100}")
    print(f"{text.center(100)}")
    print(f"{'=' * 100}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message (Windows-safe)"""
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message (Windows-safe)"""
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message (Windows-safe)"""
    print(f"{Colors.OKCYAN}[INFO] {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message (Windows-safe)"""
    print(f"{Colors.WARNING}[WARN] {text}{Colors.ENDC}")


class JDCSVUploadTester:
    """Comprehensive tester for JD CSV upload pipeline"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.db = get_database()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        
        # Test data matching SQL Server test data
        self.test_jd_data = [
            {
                "Employee_ID": 1011251,
                "JD_ID": "1001",
                "Job_Description": "Senior Data Analyst responsible for analyzing employee performance metrics, generating actionable insights, and creating comprehensive reports. Requires proficiency in SQL, Python, Tableau, and statistical analysis. Collaborates with HR team to identify trends, conduct root cause analysis, and recommend strategic improvements to HR processes and employee development programs. Reports to HR Manager.",
                "Assigned_Date": "2024-01-15",
                "Is_Current": True,
                "End_Date": None
            },
            {
                "Employee_ID": 10347252,
                "JD_ID": "1002",
                "Job_Description": "Project Coordinator responsible for timeline management, resource allocation, stakeholder communication, and deliverable tracking. Supports senior project managers with administrative tasks, maintains project documentation, and coordinates meetings between technical and business teams. Ensures timely completion of assigned tasks and helps resolve interdepartmental conflicts.",
                "Assigned_Date": "2023-06-01",
                "Is_Current": False,
                "End_Date": "2024-05-31"
            },
            {
                "Employee_ID": 15638493,
                "JD_ID": "1004",
                "Job_Description": "Junior Software Engineer responsible for developing and maintaining backend services using Python and PostgreSQL. Participates in code reviews, writes unit tests, documents code, and collaborates with senior engineers on feature implementation and bug fixes. Follows established coding standards and best practices. Assists with database schema design and optimization.",
                "Assigned_Date": "2023-01-01",
                "Is_Current": False,
                "End_Date": "2023-12-31"
            },
            {
                "Employee_ID": 10546874,
                "JD_ID": "1007",
                "Job_Description": "Data Scientist responsible for building predictive models, conducting statistical analysis, and generating insights from large datasets. Expertise required in machine learning algorithms, Python, R programming, data visualization, and business analytics. Conducts hypothesis testing, develops forecasting models, and presents findings to business stakeholders for strategic decision-making.",
                "Assigned_Date": "2024-02-01",
                "Is_Current": True,
                "End_Date": None
            },
            {
                "Employee_ID": 10456345,
                "JD_ID": "1008",
                "Job_Description": "Technical Lead responsible for architecture decisions, code reviews, and development best practices implementation. Coordinates with product management and other stakeholders, provides technical mentorship to engineering team, and ensures system reliability and performance. Drives adoption of new technologies and tools. Reports to Chief Technology Officer.",
                "Assigned_Date": "2024-03-01",
                "Is_Current": True,
                "End_Date": None
            }
        ]
    
    def run_all_tests(self):
        """Execute all test phases"""
        print_header("JOB DESCRIPTION CSV UPLOAD - COMPREHENSIVE END-TO-END TEST")
        print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API Base URL: {self.api_base_url}")
        
        try:
            # Phase 1: Pre-flight checks
            if not self.test_phase_1_preflight_checks():
                print_error("Pre-flight checks failed. Cannot proceed.")
                return
            
            # Phase 2: Verify/create test employees
            if not self.test_phase_2_verify_create_employees():
                print_error("Employee setup failed. Cannot proceed.")
                return
            
            # Phase 3: Generate CSV file
            csv_file_path = self.test_phase_3_generate_csv()
            if not csv_file_path:
                print_error("CSV generation failed. Cannot proceed.")
                return
            
            # Phase 4: Upload CSV file
            job_id = self.test_phase_4_upload_csv(csv_file_path)
            if not job_id:
                print_error("CSV upload failed. Cannot proceed.")
                return
            
            # Phase 5: Monitor import progress
            if not self.test_phase_5_monitor_import(job_id):
                print_warning("Import monitoring reported issues. Proceeding with verification anyway.")
            
            # Phase 6: Verify imported data
            self.test_phase_6_verify_postgres_data()
            
            # Phase 7: Test data integrity
            self.test_phase_7_data_integrity()
            
            # Phase 8: Test API endpoints
            self.test_phase_8_api_endpoints(job_id)
            
            # Phase 9: Test incremental update
            self.test_phase_9_incremental_update()
            
            # Cleanup
            if csv_file_path and os.path.exists(csv_file_path):
                os.remove(csv_file_path)
                print_info(f"Cleaned up temporary CSV file")
            
            # Final summary
            self.print_test_summary()
            
        except KeyboardInterrupt:
            print_warning("\nTest interrupted by user")
            self.print_test_summary()
        except Exception as e:
            print_error(f"Critical test failure: {str(e)}")
            logger.error("Test suite failed with exception", exc_info=True)
            self.test_results["failed"] += 1
            self.print_test_summary()
    
    # ========================================================================
    # PHASE 1: PRE-FLIGHT CHECKS
    # ========================================================================
    
    def test_phase_1_preflight_checks(self) -> bool:
        """Verify prerequisites"""
        print_header("PHASE 1: PRE-FLIGHT CHECKS")
        
        all_checks_passed = True
        
        # Check FastAPI
        try:
            response = requests.get(f"{self.api_base_url}/docs", timeout=5)
            if response.status_code == 200:
                print_success("FastAPI server is running")
                self.test_results["passed"] += 1
            else:
                print_error(f"FastAPI returned status {response.status_code}")
                self.test_results["failed"] += 1
                all_checks_passed = False
        except requests.exceptions.ConnectionError:
            print_error("Cannot reach FastAPI server")
            print_warning("Start with: uvicorn app.main:app --reload")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        # Check Celery worker (IMPROVED - Fixed import)
        print_info("Checking Celery worker...")
        try:
            from app.worker.celery_app import celery_app
            
            # Inspect active workers using the imported celery_app
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_names = list(active_workers.keys())
                print_success(f"Celery worker running: {worker_names[0]}")
                self.test_results["passed"] += 1
            else:
                print_error("No Celery workers detected!")
                print_warning("Start worker: celery -A app.worker.celery_app worker --loglevel=info --pool=solo")
                self.test_results["failed"] += 1
                all_checks_passed = False
                
        except Exception as e:
            print_error(f"Cannot connect to Celery: {str(e)}")
            print_warning("Ensure Redis is running: redis-server")
            print_warning("Start worker: celery -A app.worker.celery_app worker --loglevel=info --pool=solo")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        # Check PostgreSQL
        try:
            with self.db.create_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            print_success("PostgreSQL connection successful")
            self.test_results["passed"] += 1
        except Exception as e:
            print_error(f"PostgreSQL connection failed: {str(e)}")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        return all_checks_passed
    
    # ========================================================================
    # PHASE 2: VERIFY/CREATE TEST EMPLOYEES
    # ========================================================================
    
    def test_phase_2_verify_create_employees(self) -> bool:
        """Verify test employees exist, create if missing"""
        print_header("PHASE 2: VERIFY/CREATE TEST EMPLOYEES")
        
        required_ids = [1011251, 10347252, 15638493, 10546874, 10456345]
        employee_data = {
            1011251: ("Ahmed Ali", "Senior Analyst", "Technical"),
            10347252: ("Fatima Khan", "Project Manager", "Operations"),
            15638493: ("Hassan Muhammad", "Software Engineer", "Technical"),
            10546874: ("Aisha Malik", "HR Specialist", "Human Resources"),
            10456345: ("Omar Hassan", "Finance Officer", "Finance")
        }
        
        try:
            with self.db.create_session() as session:
                existing = session.query(Employee).filter(
                    Employee.id.in_(required_ids)
                ).all()
                existing_ids = [e.id for e in existing]
                missing_ids = [eid for eid in required_ids if eid not in existing_ids]
                
                if len(existing) == len(required_ids):
                    print_success(f"All {len(required_ids)} employees exist")
                    for emp in existing:
                        print_info(f"  • {emp.id}: {emp.name} ({emp.position})")
                    self.test_results["passed"] += 1
                    return True
                
                # Create missing employees
                print_info(f"Creating {len(missing_ids)} missing employees...")
                for emp_id in missing_ids:
                    name, position, wing = employee_data[emp_id]
                    employee = Employee(
                        id=emp_id,
                        name=name,
                        position=position,
                        wing=wing
                    )
                    session.add(employee)
                
                session.commit()
                print_success(f"Created {len(missing_ids)} employees")
                self.test_results["passed"] += 1
                return True
                
        except Exception as e:
            print_error(f"Employee setup failed: {str(e)}")
            self.test_results["failed"] += 1
            return False
    
    # ========================================================================
    # PHASE 3: GENERATE CSV FILE
    # ========================================================================
    
    def test_phase_3_generate_csv(self) -> Optional[str]:
        """Generate CSV file from test data"""
        print_header("PHASE 3: GENERATE CSV FILE")
        
        try:
            # Create temporary CSV file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.csv',
                newline='',
                encoding='utf-8'
            )
            
            csv_writer = csv.DictWriter(
                temp_file,
                fieldnames=['Employee_ID', 'JD_ID', 'Job_Description', 'Assigned_Date', 'Is_Current', 'End_Date']
            )
            
            csv_writer.writeheader()
            csv_writer.writerows(self.test_jd_data)
            
            temp_file.close()
            
            # Verify file
            with open(temp_file.name, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print_success(f"CSV file generated: {temp_file.name}")
                print_info(f"File size: {os.path.getsize(temp_file.name)} bytes")
                print_info(f"Rows: {len(lines) - 1} data rows + 1 header")
                print_info(f"\nFirst 3 rows:")
                for i, line in enumerate(lines[:3]):
                    print(f"  {i+1}. {line.strip()[:100]}...")
                
                self.test_results["passed"] += 1
                return temp_file.name
                
        except Exception as e:
            print_error(f"CSV generation failed: {str(e)}")
            self.test_results["failed"] += 1
            return None
    
    # ========================================================================
    # PHASE 4: UPLOAD CSV FILE
    # ========================================================================
    
    def test_phase_4_upload_csv(self, csv_file_path: str) -> Optional[str]:
        """Upload CSV file via /imports/upload endpoint"""
        print_header("PHASE 4: UPLOAD CSV FILE")
        
        try:
            print_info(f"Uploading: {csv_file_path}")
            
            with open(csv_file_path, 'rb') as f:
                files = {'file': ('job_descriptions.csv', f, 'text/csv')}
                data = {
                    'csv_type': 'job_descriptions',  # Explicit type
                    'processing_mode': 'bulk',
                    'stop_on_error': 'false',
                    'error_threshold_percent': '10.0'
                }
                
                # INCREASED TIMEOUT for Windows (file upload can be slower)
                response = requests.post(
                    f"{self.api_base_url}/imports/upload",
                    files=files,
                    data=data,
                    timeout=60  # Increased from 30 to 60 seconds
                )
            
            if response.status_code in (200, 201, 202):
                job_data = response.json()
                job_id = job_data.get('job_id')
                
                print_success("CSV uploaded successfully!")
                print_info(f"Job ID: {job_id}")
                print_info(f"Filename: {job_data.get('filename')}")
                print_info(f"Status: {job_data.get('status')}")
                print_info(f"CSV Type: {job_data.get('csv_type')}")
                
                self.test_results["passed"] += 1
                return job_id
            else:
                print_error(f"Upload failed with status {response.status_code}")
                print_error(f"Response: {response.text}")
                self.test_results["failed"] += 1
                return None
                
        except requests.exceptions.ConnectionError as e:
            # IMPROVED ERROR HANDLING for connection issues
            print_error(f"Connection error during upload: {str(e)}")
            print_warning("This might indicate:")
            print_warning("1. FastAPI server crashed or restarted during upload")
            print_warning("2. Network timeout - try increasing timeout value")
            print_warning("3. Check FastAPI logs for errors")
            self.test_results["failed"] += 1
            return None
        except requests.exceptions.Timeout as e:
            print_error(f"Upload timeout: {str(e)}")
            print_warning("The server took too long to respond")
            self.test_results["failed"] += 1
            return None
        except Exception as e:
            print_error(f"Upload error: {str(e)}")
            self.test_results["failed"] += 1
            return None
    
    # ========================================================================
    # PHASE 5: MONITOR IMPORT PROGRESS
    # ========================================================================
    
    def test_phase_5_monitor_import(self, job_id: str) -> bool:
        """Monitor import job progress"""
        print_header("PHASE 5: MONITOR IMPORT PROGRESS")
        
        if not job_id:
            print_error("No job_id provided")
            self.test_results["failed"] += 1
            return False
        
        print_info(f"Monitoring job {job_id}...")
        print_warning("Waiting for Celery worker to process...")
        
        max_wait = 120
        poll_interval = 2
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                response = requests.get(
                    f"{self.api_base_url}/imports/{job_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    total = data.get('total_rows', 0)
                    processed = data.get('processed_rows', 0)
                    successful = data.get('successful_rows', 0)
                    errors = data.get('error_count', 0)
                    percent = data.get('percent_complete', 0)
                    
                    print(f"\r{Colors.OKCYAN}Status: {status} | {percent:.1f}% | "
                          f"Processed: {processed}/{total} | Success: {successful} | "
                          f"Errors: {errors}{Colors.ENDC}",
                          end="", flush=True)
                    
                    if status in ['completed', 'failed']:
                        print()  # New line
                        
                        if status == 'completed':
                            print_success("Import completed!")
                            print_success(f"Successful: {successful}/{total}")
                            
                            # Display metrics
                            metrics = data.get('metrics', {})
                            if metrics:
                                jd_created = metrics.get('jd_records_created', 0)
                                jd_updated = metrics.get('jd_records_updated', 0)
                                print_info(f"Created: {jd_created}, Updated: {jd_updated}")
                            
                            if errors == 0:
                                print_success("No errors")
                                self.test_results["passed"] += 1
                            else:
                                print_warning(f"{errors} errors encountered")
                                self.test_results["warnings"] += 1
                            
                            return True
                        else:
                            print_error("Import failed!")
                            self.test_results["failed"] += 1
                            return False
                
                time.sleep(poll_interval)
                elapsed += poll_interval
                
            except Exception as e:
                print_error(f"\nMonitoring error: {str(e)}")
                self.test_results["failed"] += 1
                return False
        
        print_warning(f"\nImport did not complete in {max_wait}s")
        self.test_results["warnings"] += 1
        return False
    
    # ========================================================================
    # PHASE 6: VERIFY POSTGRES DATA
    # ========================================================================
    
    def test_phase_6_verify_postgres_data(self):
        """Verify imported data matches expectations"""
        print_header("PHASE 6: VERIFY IMPORTED DATA")
        
        try:
            with self.db.create_session() as session:
                # Count records
                total = session.query(EmployeeJobDescription).filter(
                    EmployeeJobDescription.employee_id.in_([1011251, 10347252, 15638493, 10546874, 10456345])
                ).count()
                
                print_info(f"Total JD records: {total}")
                
                if total >= 5:
                    print_success(f"Found {total} records (expected 5)")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Expected 5 records, found {total}")
                    self.test_results["failed"] += 1
                    return
                
                # Verify each record
                print_info("\nVerifying individual records:")
                
                for expected in self.test_jd_data:
                    emp_id = expected['Employee_ID']
                    jd_id = expected['JD_ID']
                    
                    jd = session.query(EmployeeJobDescription).filter(
                        EmployeeJobDescription.employee_id == emp_id,
                        EmployeeJobDescription.jd_id == jd_id
                    ).first()
                    
                    if jd:
                        print_info(f"\n  Employee {emp_id}, JD {jd_id}:")
                        
                        # Verify assigned_date
                        expected_date = datetime.strptime(expected['Assigned_Date'], '%Y-%m-%d').date()
                        if jd.assigned_date == expected_date:
                            print_success(f"     Assigned: {jd.assigned_date}")
                        else:
                            print_error(f"     Date mismatch: {jd.assigned_date} != {expected_date}")
                            self.test_results["failed"] += 1
                            continue
                        
                        # Verify is_current
                        if jd.is_current == expected['Is_Current']:
                            print_success(f"     Current: {jd.is_current}")
                        else:
                            print_error(f"     Current mismatch: {jd.is_current} != {expected['Is_Current']}")
                            self.test_results["failed"] += 1
                        
                        # Verify end_date
                        expected_end = datetime.strptime(expected['End_Date'], '%Y-%m-%d').date() if expected['End_Date'] else None
                        if jd.end_date == expected_end:
                            print_success(f"     End Date: {jd.end_date}")
                        else:
                            print_error(f"     End Date mismatch: {jd.end_date} != {expected_end}")
                            self.test_results["failed"] += 1
                        
                        # Verify description
                        if len(jd.job_description) >= 50:
                            print_success(f"     Description length: {len(jd.job_description)} chars")
                        else:
                            print_error(f"     Description too short: {len(jd.job_description)} chars")
                            self.test_results["failed"] += 1
                        
                        self.test_results["passed"] += 1
                    else:
                        print_error(f"   Record not found: Employee {emp_id}, JD {jd_id}")
                        self.test_results["failed"] += 1
                        
        except Exception as e:
            print_error(f"Verification failed: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 7: DATA INTEGRITY
    # ========================================================================
    
    def test_phase_7_data_integrity(self):
        """Test data integrity and business logic"""
        print_header("PHASE 7: DATA INTEGRITY")
        
        try:
            with self.db.create_session() as session:
                # Test unique constraint
                print_info("Test 1: Unique (employee_id, jd_id) pairs")
                jds = session.query(EmployeeJobDescription).filter(
                    EmployeeJobDescription.employee_id.in_([1011251, 10347252, 15638493, 10546874, 10456345])
                ).all()
                
                unique_pairs = set()
                for jd in jds:
                    pair = (jd.employee_id, jd.jd_id)
                    if pair in unique_pairs:
                        print_error(f"Duplicate pair found: {pair}")
                        self.test_results["failed"] += 1
                        return
                    unique_pairs.add(pair)
                
                print_success("No duplicates found")
                self.test_results["passed"] += 1
                
                # Test current JD limit
                print_info("\nTest 2: One current JD per employee")
                for emp_id in [1011251, 10347252, 15638493, 10546874, 10456345]:
                    current = session.query(EmployeeJobDescription).filter(
                        EmployeeJobDescription.employee_id == emp_id,
                        EmployeeJobDescription.is_current == True
                    ).count()
                    
                    if current <= 1:
                        print_success(f"   Employee {emp_id}: {current} current JD")
                        self.test_results["passed"] += 1
                    else:
                        print_error(f"   Employee {emp_id}: {current} current JDs (should be ≤1)")
                        self.test_results["failed"] += 1
                        
        except Exception as e:
            print_error(f"Integrity test failed: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 8: API ENDPOINTS
    # ========================================================================
    
    def test_phase_8_api_endpoints(self, job_id: str):
        """Test import API endpoints"""
        print_header("PHASE 8: TEST API ENDPOINTS")
        
        # Test job status
        print_info("Test 1: GET /imports/{job_id}")
        try:
            response = requests.get(f"{self.api_base_url}/imports/{job_id}", timeout=5)
            if response.status_code == 200:
                print_success("Job status endpoint working")
                self.test_results["passed"] += 1
            else:
                print_error(f"Returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results["failed"] += 1
        
        # Test error list
        print_info("\nTest 2: GET /imports/{job_id}/errors")
        try:
            response = requests.get(
                f"{self.api_base_url}/imports/{job_id}/errors",
                params={'page': 1, 'page_size': 10},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                print_success(f"Errors endpoint working ({data.get('total')} errors)")
                self.test_results["passed"] += 1
            else:
                print_error(f"Returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results["failed"] += 1
        
        # Test job list
        print_info("\nTest 3: GET /imports/")
        try:
            response = requests.get(
                f"{self.api_base_url}/imports/",
                params={'csv_type': 'job_descriptions', 'limit': 10},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                print_success(f"Job list endpoint working (found {len(data)} jobs)")
                self.test_results["passed"] += 1
            else:
                print_error(f"Returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 9: INCREMENTAL UPDATE
    # ========================================================================
    
    def test_phase_9_incremental_update(self):
        """Test incremental update (re-upload same data)"""
        print_header("PHASE 9: INCREMENTAL UPDATE TEST")
        
        print_info("Re-uploading same CSV to test upsert logic...")
        
        # Modify one record
        modified_data = self.test_jd_data.copy()
        modified_data[0]['Job_Description'] = modified_data[0]['Job_Description'] + " [UPDATED IN TEST]"
        
        try:
            # Generate updated CSV
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                suffix='.csv',
                newline='',
                encoding='utf-8'
            )
            
            csv_writer = csv.DictWriter(
                temp_file,
                fieldnames=['Employee_ID', 'JD_ID', 'Job_Description', 'Assigned_Date', 'Is_Current', 'End_Date']
            )
            csv_writer.writeheader()
            csv_writer.writerows(modified_data)
            temp_file.close()
            
            # Upload
            with open(temp_file.name, 'rb') as f:
                files = {'file': ('job_descriptions_updated.csv', f, 'text/csv')}
                data = {'csv_type': 'job_descriptions', 'processing_mode': 'bulk'}
                
                response = requests.post(
                    f"{self.api_base_url}/imports/upload",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code in (200, 201, 202):
                job_data = response.json()
                job_id = job_data.get('job_id')
                print_success(f"Re-upload successful (Job {job_id})")
                
                # Wait for completion
                time.sleep(5)
                
                # Verify updated record
                with self.db.create_session() as session:
                    jd = session.query(EmployeeJobDescription).filter(
                        EmployeeJobDescription.employee_id == 1011251,
                        EmployeeJobDescription.jd_id == "1001"
                    ).first()
                    
                    if jd and "[UPDATED IN TEST]" in jd.job_description:
                        print_success("Record updated successfully")
                        self.test_results["passed"] += 1
                    else:
                        print_error("Record not updated")
                        self.test_results["failed"] += 1
            else:
                print_error(f"Re-upload failed: {response.status_code}")
                self.test_results["failed"] += 1
            
            # Cleanup
            os.remove(temp_file.name)
            
        except Exception as e:
            print_error(f"Incremental update test failed: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    def print_test_summary(self):
        """Print final summary"""
        print_header("TEST SUMMARY")
        
        total = self.test_results["passed"] + self.test_results["failed"] + self.test_results["warnings"]
        
        print(f"\n{Colors.BOLD}Total Tests: {total}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Passed: {self.test_results['passed']}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {self.test_results['failed']}{Colors.ENDC}")
        print(f"{Colors.WARNING}Warnings: {self.test_results['warnings']}{Colors.ENDC}")
        
        success_rate = (self.test_results["passed"] / total * 100) if total > 0 else 0
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}")
        
        if self.test_results["failed"] == 0:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD} ALL TESTS PASSED!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD} SOME TESTS FAILED{Colors.ENDC}")


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test JD CSV Upload Pipeline")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    
    tester = JDCSVUploadTester(api_base_url=args.api_url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
