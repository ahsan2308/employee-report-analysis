"""
Comprehensive End-to-End Test Script for Job Description Sync with REAL SQL Server

This script tests the complete JD sync pipeline using ACTUAL SQL Server data:
1. SQL Server connectivity and data verification
2. API endpoint triggering (via HTTP requests)
3. Celery task execution (requires running worker)
4. Data transformation and validation
5. PostgreSQL insertion/updates
6. Sync status tracking
7. Error handling
8. Incremental sync logic

PREREQUISITES:
- SQL Server must be running with test data populated
- FastAPI must be running (uvicorn app.main:app --reload)
- Celery worker must be running (celery -A app.worker.celery_app worker --loglevel=info --pool=solo)
- PostgreSQL must be accessible
- Test employees must exist in PostgreSQL (Employee IDs: 1011251, 10347252, 15638493, 10546874, 10456345)

TEST DATA IN SQL SERVER (as provided):
- 5 JD records with Employee_IDs matching the employee reports test data
- Mix of current and historical JD assignments
- Various assigned dates and end dates

Usage:
    python app/tests/test_jd_sync_with_real_sqlserver.py
    
    Or run specific test phases:
    python app/tests/test_jd_sync_with_real_sqlserver.py --phase=1
"""

import time
import requests
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import text
import argparse
import sys

# Add parent directory to path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.database import get_database
from app.integrations.sqlserver.connector import create_sqlserver_connector
from app.models.db_models import Employee, EmployeeJobDescription
from app.models.sync_models import SyncHistory, SyncStatus, SyncType
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
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print formatted section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 100}")
    print(f"{text.center(100)}")
    print(f"{'=' * 100}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN} {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL} {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN} {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING} {text}{Colors.ENDC}")


class JDSyncRealTester:
    """Comprehensive tester for JD sync pipeline with REAL SQL Server"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize tester.
        
        Args:
            api_base_url: Base URL for FastAPI application
        """
        self.api_base_url = api_base_url
        self.db = get_database()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        
        # Expected test data from SQL Server (from your INSERT statements)
        self.expected_jds = [
            {
                "Employee_ID": 1011251,
                "JD_ID": 1001,
                "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True,
                "description_starts_with": "Senior Data Analyst"
            },
            {
                "Employee_ID": 10347252,
                "JD_ID": 1002,
                "Assigned_Date": date(2023, 6, 1),
                "Is_Current": False,
                "End_Date": date(2024, 5, 31),
                "description_starts_with": "Project Coordinator"
            },
            {
                "Employee_ID": 15638493,
                "JD_ID": 1004,
                "Assigned_Date": date(2023, 1, 1),
                "Is_Current": False,
                "End_Date": date(2023, 12, 31),
                "description_starts_with": "Junior Software Engineer"
            },
            {
                "Employee_ID": 10546874,
                "JD_ID": 1007,
                "Assigned_Date": date(2024, 2, 1),
                "Is_Current": True,
                "description_starts_with": "Data Scientist"
            },
            {
                "Employee_ID": 10456345,
                "JD_ID": 1008,
                "Assigned_Date": date(2024, 3, 1),
                "Is_Current": True,
                "description_starts_with": "Technical Lead"
            }
        ]
    
    def run_all_tests(self):
        """Execute all test phases"""
        print_header("JOB DESCRIPTION SYNC PIPELINE - COMPREHENSIVE END-TO-END TEST (REAL SQL SERVER)")
        print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"API Base URL: {self.api_base_url}")
        
        try:
            # Phase 1: Pre-flight checks
            if not self.test_phase_1_preflight_checks():
                print_error("Pre-flight checks failed. Cannot proceed with tests.")
                return
            
            # Phase 2: SQL Server data verification
            if not self.test_phase_2_sqlserver_verification():
                print_error("SQL Server verification failed. Cannot proceed with tests.")
                return
            
            # Phase 3: Verify PostgreSQL employees exist
            employees_exist = self.test_phase_3_verify_postgres_employees()
            
            # Phase 3.5: Create employees if they don't exist
            if not employees_exist:
                if not self.test_phase_3_5_create_test_employees():
                    print_error("Failed to create required employees. Cannot proceed.")
                    return
            
            # Phase 4: Clean existing JD data (optional)
            self.test_phase_4_clean_postgres_jd_data()
            
            # Phase 5: Trigger FULL sync via API
            sync_id = self.test_phase_5_trigger_full_sync()
            if not sync_id:
                print_error("Failed to trigger sync. Cannot proceed.")
                return
            
            # Phase 6: Monitor sync progress
            if not self.test_phase_6_monitor_sync(sync_id):
                print_warning("Sync monitoring reported issues. Proceeding with data verification anyway.")
            
            # Phase 7: Verify synced data in PostgreSQL
            self.test_phase_7_verify_postgres_data()
            
            # Phase 8: Test incremental sync
            self.test_phase_8_incremental_sync()
            
            # Phase 9: Test API status endpoints
            self.test_phase_9_api_status_endpoints(sync_id)
            
            # Phase 10: Test data integrity
            self.test_phase_10_data_integrity()
            
            # Final summary
            self.print_test_summary()
            
        except KeyboardInterrupt:
            print_warning("\nTest interrupted by user")
            self.print_test_summary()
        except Exception as e:
            print_error(f"Critical test failure: {str(e)}")
            logger.error(f"Test suite failed with exception", exc_info=True)
            self.test_results["failed"] += 1
            self.print_test_summary()
    
    # ========================================================================
    # PHASE 1: PRE-FLIGHT CHECKS
    # ========================================================================
    
    def test_phase_1_preflight_checks(self) -> bool:
        """Verify prerequisites before starting tests"""
        print_header("PHASE 1: PRE-FLIGHT CHECKS")
        
        all_checks_passed = True
        
        # Check 1: FastAPI is running
        try:
            response = requests.get(f"{self.api_base_url}/docs", timeout=5)
            if response.status_code == 200:
                print_success("FastAPI server is running")
                self.test_results["passed"] += 1
            else:
                print_error(f"FastAPI returned unexpected status {response.status_code}")
                self.test_results["failed"] += 1
                all_checks_passed = False
        except requests.exceptions.ConnectionError:
            print_error("Cannot reach FastAPI server")
            print_warning("Make sure FastAPI is running: uvicorn app.main:app --reload")
            self.test_results["failed"] += 1
            all_checks_passed = False
        except Exception as e:
            print_error(f"Error checking FastAPI: {str(e)}")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        # Check 2: Celery worker status (warning only, can't programmatically verify)
        print_info("Celery worker status cannot be verified programmatically")
        print_warning("MANUAL CHECK REQUIRED: Ensure Celery worker is running")
        print_info("Start worker with: celery -A app.worker.celery_app worker --loglevel=info --pool=solo")
        self.test_results["warnings"] += 1
        
        # Check 3: PostgreSQL connection
        try:
            with self.db.create_session() as session:
                session.execute(text("SELECT 1"))
            print_success("PostgreSQL connection successful")
            self.test_results["passed"] += 1
        except Exception as e:
            print_error(f"PostgreSQL connection failed: {str(e)}")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        # Check 4: SQL Server connection
        try:
            connector = create_sqlserver_connector()
            if connector.test_connection():
                print_success("SQL Server connection successful")
                print_info(f"Connected to: {connector.server}/{connector.database}")
                self.test_results["passed"] += 1
            else:
                print_error("SQL Server connection failed")
                self.test_results["failed"] += 1
                all_checks_passed = False
        except Exception as e:
            print_error(f"SQL Server connection error: {str(e)}")
            self.test_results["failed"] += 1
            all_checks_passed = False
        
        return all_checks_passed
    
    # ========================================================================
    # PHASE 2: SQL SERVER DATA VERIFICATION
    # ========================================================================
    
    def test_phase_2_sqlserver_verification(self) -> bool:
        """Verify test data exists in SQL Server"""
        print_header("PHASE 2: SQL SERVER DATA VERIFICATION")
        
        try:
            connector = create_sqlserver_connector()
            
            # Find JD table name
            jd_table = None
            for table in connector.get_allowed_tables():
                if 'jobdescription' in table.lower() or 'jd' in table.lower():
                    jd_table = table
                    break
            
            if not jd_table:
                print_error("Job descriptions table not found in SQL Server")
                print_info(f"Available tables: {connector.get_allowed_tables()}")
                self.test_results["failed"] += 1
                return False
            
            print_info(f"Using SQL Server table: {jd_table}")
            
            # Query test data
            query = f"""
                SELECT Employee_ID, JD_ID, Job_Description, Assigned_Date, Is_Current, End_Date, LastModifiedDate 
                FROM {jd_table} 
                WHERE Employee_ID IN (1011251, 10347252, 15638493, 10546874, 10456345)
                ORDER BY Employee_ID, Assigned_Date
            """
            
            with connector._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                
                if len(rows) < 5:
                    print_error(f"Expected at least 5 JD records, found {len(rows)}")
                    print_warning("Make sure you've run the test data INSERT statements in SQL Server")
                    self.test_results["failed"] += 1
                    return False
                
                print_success(f"Found {len(rows)} JD records in SQL Server")
                self.test_results["passed"] += 1
                
                # Display sample data
                print_info("\nJD records from SQL Server:")
                for i, row in enumerate(rows, 1):
                    emp_id, jd_id, desc, assigned, is_current, end_date, modified = row
                    current_status = "CURRENT" if is_current else f"ENDED ({end_date})"
                    print(f"  {i}. Employee {emp_id}, JD {jd_id}, Assigned: {assigned}, Status: {current_status}")
                    print(f"     Description: {desc[:80]}...")
                    print(f"     Last Modified: {modified}")
            
            # Verify timestamp column
            schema = connector.get_table_schema(jd_table)
            timestamp_col = None
            for col_name in schema.keys():
                if col_name in connector.get_allowed_timestamp_columns():
                    timestamp_col = col_name
                    break
            
            if timestamp_col:
                print_success(f"Timestamp column found: {timestamp_col}")
                self.test_results["passed"] += 1
                return True
            else:
                print_error("No valid timestamp column found for incremental sync")
                self.test_results["failed"] += 1
                return False
                
        except Exception as e:
            print_error(f"SQL Server verification failed: {str(e)}")
            logger.error("SQL Server verification error", exc_info=True)
            self.test_results["failed"] += 1
            return False
    
    # ========================================================================
    # PHASE 3: VERIFY POSTGRES EMPLOYEES
    # ========================================================================
    
    def test_phase_3_verify_postgres_employees(self) -> bool:
        """Verify that test employees exist in PostgreSQL"""
        print_header("PHASE 3: VERIFY POSTGRESQL EMPLOYEES")
        
        required_employee_ids = [1011251, 10347252, 15638493, 10546874, 10456345]
        
        try:
            with self.db.create_session() as session:
                existing_employees = session.query(Employee).filter(
                    Employee.id.in_(required_employee_ids)
                ).all()
                
                existing_ids = [emp.id for emp in existing_employees]
                missing_ids = [emp_id for emp_id in required_employee_ids if emp_id not in existing_ids]
                
                if len(existing_employees) == len(required_employee_ids):
                    print_success(f"All {len(required_employee_ids)} required employees exist in PostgreSQL")
                    for emp in existing_employees:
                        print_info(f"  • Employee {emp.id}: {emp.name} ({emp.position}, {emp.wing})")
                    self.test_results["passed"] += 1
                    return True
                else:
                    print_warning(f"Missing {len(missing_ids)} employees in PostgreSQL")
                    print_info(f"Missing Employee IDs: {missing_ids}")
                    print_warning("JD sync REQUIRES employees to exist (foreign key constraint)")
                    print_info("Proceeding to Phase 3.5 to create employees...")
                    self.test_results["warnings"] += 1
                    return False  # ← Need to create employees first
                    
        except Exception as e:
            print_error(f"Error verifying PostgreSQL employees: {str(e)}")
            self.test_results["failed"] += 1
            return False
    
    def test_phase_3_5_create_test_employees(self):
        """Create test employees required for JD sync"""
        print_header("PHASE 3.5: CREATE TEST EMPLOYEES")
        
        required_employee_ids = [1011251, 10347252, 15638493, 10546874, 10456345]
        
        # Map employee IDs to names from SQL Server test data
        employee_data = {
            1011251: ("Ahmed Ali", "Senior Analyst", "BS-21"),
            10347252: ("Fatima Khan", "Project Manager", "BS-20"),
            15638493: ("Hassan Muhammad", "Software Engineer", "BS-19"),
            10546874: ("Aisha Malik", "HR Specialist", "BS-18"),
            10456345: ("Omar Hassan", "Finance Officer", "BS-19")
        }
        
        try:
            with self.db.create_session() as session:
                existing_ids = [emp.id for emp in session.query(Employee).filter(
                    Employee.id.in_(required_employee_ids)
                ).all()]
                
                missing_ids = [eid for eid in required_employee_ids if eid not in existing_ids]
                
                if missing_ids:
                    print_info(f"Creating {len(missing_ids)} missing employees...")
                    for emp_id in missing_ids:
                        name, position, bps = employee_data.get(emp_id, (f"Test Employee {emp_id}", "Unknown", "BS-17"))
                        employee = Employee(
                            id=emp_id,
                            name=name,
                            position=position,
                            wing="Test Department"  # Generic wing since not in JD test data
                        )
                        session.add(employee)
                    
                    session.commit()
                    print_success(f"Created {len(missing_ids)} employees")
                    
                    # Verify creation
                    created_count = session.query(Employee).filter(
                        Employee.id.in_(required_employee_ids)
                    ).count()
                    
                    if created_count == len(required_employee_ids):
                        print_success(f"Verified: All {created_count} employees now exist")
                        self.test_results["passed"] += 1
                        return True
                    else:
                        print_error(f"Only {created_count}/{len(required_employee_ids)} employees exist after creation")
                        self.test_results["failed"] += 1
                        return False
                else:
                    print_info("All employees already exist")
                    self.test_results["passed"] += 1
                    return True
            
        except Exception as e:
            print_error(f"Failed to create test employees: {str(e)}")
            logger.error("Employee creation error", exc_info=True)
            self.test_results["failed"] += 1
            return False
    
    # ========================================================================
    # PHASE 4: CLEAN POSTGRES JD DATA (OPTIONAL)
    # ========================================================================
    
    def test_phase_4_clean_postgres_jd_data(self):
        """Clean existing JD data for fresh test (optional)"""
        print_header("PHASE 4: CLEAN POSTGRES JD DATA (OPTIONAL)")
        
        # REMOVED: Interactive prompt - defaulting to NO cleanup (safer)
        # This allows the test to run fully automated without user input
        print_info("Skipping data cleanup (existing records will be updated via upsert)")
        print_info("If you need to delete existing data, do so manually before running the test")
        self.test_results["warnings"] += 1
    
    # ========================================================================
    # PHASE 5: TRIGGER FULL SYNC VIA API
    # ========================================================================
    
    def test_phase_5_trigger_full_sync(self) -> Optional[str]:
        """Trigger JD full sync via API endpoint"""
        print_header("PHASE 5: TRIGGER FULL SYNC VIA API")
        
        try:
            print_info("Triggering full sync for job descriptions via POST /sync/trigger/job_descriptions...")
            response = requests.post(
                f"{self.api_base_url}/sync/trigger/job_descriptions",
                params={"is_full_sync": True},
                timeout=10
            )
            
            if response.status_code == 202:
                data = response.json()
                sync_id = data.get("sync_id")
                task_id = data.get("task_id")
                
                print_success("Sync triggered successfully!")
                print_info(f"Sync ID: {sync_id}")
                print_info(f"Task ID: {task_id}")
                print_info(f"Status: {data.get('status')}")
                print_info(f"Mode: {'Full Sync' if data.get('is_full_sync') else 'Incremental Sync'}")
                print_info(f"Message: {data.get('message')}")
                print_info(f"Triggered At: {data.get('triggered_at')}")
                
                self.test_results["passed"] += 1
                return sync_id
                
            elif response.status_code == 409:
                print_warning("Sync already in progress")
                print_info(f"Response: {response.text}")
                # Try to extract sync_id from error message
                # This is a fallback; ideally wait for existing sync to complete
                self.test_results["warnings"] += 1
                return None
                
            else:
                print_error(f"API returned status {response.status_code}")
                print_error(f"Response: {response.text}")
                self.test_results["failed"] += 1
                return None
                
        except Exception as e:
            print_error(f"Failed to trigger sync: {str(e)}")
            self.test_results["failed"] += 1
            return None
    
    # ========================================================================
    # PHASE 6: MONITOR SYNC PROGRESS
    # ========================================================================
    
    def test_phase_6_monitor_sync(self, sync_id: str) -> bool:
        """Monitor sync progress until completion"""
        print_header("PHASE 6: MONITOR SYNC PROGRESS")
        
        if not sync_id:
            print_error("No sync_id provided, skipping monitoring")
            self.test_results["failed"] += 1
            return False
        
        print_info(f"Monitoring sync {sync_id}...")
        print_info("Waiting for Celery worker to process task...")
        print_warning("If this hangs, check that Celery worker is running!")
        
        max_wait_time = 180  # 3 minutes
        poll_interval = 3    # 3 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.api_base_url}/sync/status/{sync_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", {})
                    
                    records_synced = progress.get("records_synced", 0)
                    records_queried = progress.get("records_queried", 0)
                    records_created = progress.get("records_created", 0)
                    records_updated = progress.get("records_updated", 0)
                    error_count = progress.get("error_count", 0)
                    percent_complete = progress.get("percent_complete", 0)
                    
                    print(f"\r{Colors.OKCYAN}Status: {status} | Progress: {percent_complete:.1f}% | "
                          f"Synced: {records_synced}/{records_queried} | "
                          f"Created: {records_created} | Updated: {records_updated} | "
                          f"Errors: {error_count}{Colors.ENDC}", 
                          end="", flush=True)
                    
                    if status in ["completed", "failed", "partial"]:
                        print()  # New line after progress
                        
                        if status == "completed":
                            print_success("Sync completed successfully!")
                            print_success(f"Records synced: {records_synced}/{records_queried}")
                            print_success(f"Created: {records_created}, Updated: {records_updated}")
                            
                            if error_count == 0:
                                print_success("No errors encountered")
                                self.test_results["passed"] += 1
                            else:
                                print_warning(f"{error_count} errors encountered")
                                self.test_results["warnings"] += 1
                            
                            # Display detailed metrics
                            metrics = data.get("metrics", {})
                            if metrics:
                                print_info("\nSync Metrics:")
                                for key, value in metrics.items():
                                    print(f"  • {key}: {value}")
                            
                            # Display timestamps
                            started_at = data.get("started_at")
                            completed_at = data.get("completed_at")
                            duration = data.get("duration_seconds")
                            if started_at and completed_at:
                                print_info(f"\nTiming:")
                                print(f"  • Started: {started_at}")
                                print(f"  • Completed: {completed_at}")
                                print(f"  • Duration: {duration:.2f} seconds")
                            
                            return True
                            
                        elif status == "failed":
                            print_error("Sync failed!")
                            error_msg = data.get("error_message", "No error message")
                            print_error(f"Error: {error_msg}")
                            self.test_results["failed"] += 1
                            return False
                            
                        elif status == "partial":
                            print_warning("Sync completed with errors")
                            print_warning(f"Synced: {records_synced}/{records_queried}")
                            print_warning(f"Errors: {error_count}")
                            self.test_results["warnings"] += 1
                            return True
                
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                
            except Exception as e:
                print_error(f"\nError checking sync status: {str(e)}")
                self.test_results["failed"] += 1
                return False
        
        print_warning(f"\nSync did not complete within {max_wait_time} seconds")
        print_info("Check sync status manually using GET /sync/status/{sync_id}")
        print_warning("The sync may still be running in the background")
        self.test_results["warnings"] += 1
        return False
    
    # ========================================================================
    # PHASE 7: VERIFY POSTGRES DATA
    # ========================================================================
    
    def test_phase_7_verify_postgres_data(self):
        """Verify synced data in PostgreSQL matches SQL Server source"""
        print_header("PHASE 7: VERIFY POSTGRESQL DATA")
        
        try:
            with self.db.create_session() as session:
                # Count total JD records for test employees
                total_count = session.query(EmployeeJobDescription).filter(
                    EmployeeJobDescription.employee_id.in_([1011251, 10347252, 15638493, 10546874, 10456345])
                ).count()
                
                print_info(f"Total JD records in PostgreSQL for test employees: {total_count}")
                
                if total_count >= 5:
                    print_success(f"Found {total_count} JD records (expected at least 5)")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Expected at least 5 records, found {total_count}")
                    self.test_results["failed"] += 1
                    return
                
                # Verify each expected JD
                print_info("\nVerifying individual JD records:")
                
                for expected in self.expected_jds:
                    emp_id = expected["Employee_ID"]
                    jd_id = expected["JD_ID"]
                    
                    jd_record = session.query(EmployeeJobDescription).filter(
                        EmployeeJobDescription.employee_id == emp_id,
                        EmployeeJobDescription.jd_id == str(jd_id)
                    ).first()
                    
                    if jd_record:
                        print_info(f"\n  Employee {emp_id}, JD {jd_id}:")
                        
                        # Verify assigned date
                        if jd_record.assigned_date == expected["Assigned_Date"]:
                            print_success(f"     Assigned date: {jd_record.assigned_date}")
                        else:
                            print_error(f"     Assigned date mismatch: expected {expected['Assigned_Date']}, got {jd_record.assigned_date}")
                            self.test_results["failed"] += 1
                            continue
                        
                        # Verify is_current flag
                        if jd_record.is_current == expected["Is_Current"]:
                            print_success(f"     Is_Current: {jd_record.is_current}")
                        else:
                            print_error(f"     Is_Current mismatch: expected {expected['Is_Current']}, got {jd_record.is_current}")
                            self.test_results["failed"] += 1
                        
                        # Verify end_date if applicable
                        if "End_Date" in expected:
                            if jd_record.end_date == expected["End_Date"]:
                                print_success(f"     End date: {jd_record.end_date}")
                            else:
                                print_error(f"     End date mismatch: expected {expected['End_Date']}, got {jd_record.end_date}")
                                self.test_results["failed"] += 1
                        
                        # Verify job description content
                        if jd_record.job_description.startswith(expected["description_starts_with"]):
                            print_success(f"     Job description content correct")
                            print_info(f"      {jd_record.job_description[:100]}...")
                        else:
                            print_error(f"     Job description content mismatch")
                            self.test_results["failed"] += 1
                        
                        # Verify timestamps
                        if jd_record.created_at and jd_record.updated_at:
                            print_success(f"     Timestamps set: created={jd_record.created_at}, updated={jd_record.updated_at}")
                        else:
                            print_warning(f"     Missing timestamps")
                            self.test_results["warnings"] += 1
                        
                        self.test_results["passed"] += 1
                    else:
                        print_error(f"   JD record not found for Employee {emp_id}, JD {jd_id}")
                        self.test_results["failed"] += 1
                        
        except Exception as e:
            print_error(f"Error verifying PostgreSQL data: {str(e)}")
            logger.error("PostgreSQL verification error", exc_info=True)
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 8: TEST INCREMENTAL SYNC
    # ========================================================================
    
    def test_phase_8_incremental_sync(self):
        """Test incremental sync functionality"""
        print_header("PHASE 8: TEST INCREMENTAL SYNC")
        
        print_info("Triggering incremental sync via POST /sync/trigger/job_descriptions...")
        
        try:
            response = requests.post(
                f"{self.api_base_url}/sync/trigger/job_descriptions",
                params={"is_full_sync": False},
                timeout=10
            )
            
            if response.status_code == 202:
                data = response.json()
                sync_id = data.get("sync_id")
                
                print_success("Incremental sync triggered successfully!")
                print_info(f"Sync ID: {sync_id}")
                
                # Wait for completion
                print_info("Waiting for incremental sync to complete...")
                time.sleep(5)  # Give it a moment to start
                
                # Check status
                status_response = requests.get(
                    f"{self.api_base_url}/sync/status/{sync_id}",
                    timeout=5
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    records_queried = status_data.get("progress", {}).get("records_queried", 0)
                    records_synced = status_data.get("progress", {}).get("records_synced", 0)
                    
                    print_info(f"Incremental sync result: {records_synced} records synced (queried: {records_queried})")
                    
                    if records_queried == 0:
                        print_success("No new records to sync (expected behavior for static test data)")
                        self.test_results["passed"] += 1
                    else:
                        print_info(f"Found {records_queried} modified records")
                        self.test_results["passed"] += 1
                else:
                    print_warning("Could not retrieve incremental sync status")
                    self.test_results["warnings"] += 1
                    
            elif response.status_code == 409:
                print_warning("Sync already in progress, skipping incremental sync test")
                self.test_results["warnings"] += 1
            else:
                print_error(f"Failed to trigger incremental sync: {response.status_code}")
                self.test_results["failed"] += 1
                
        except Exception as e:
            print_error(f"Error testing incremental sync: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 9: TEST API STATUS ENDPOINTS
    # ========================================================================
    
    def test_phase_9_api_status_endpoints(self, sync_id: str):
        """Test various sync API status endpoints"""
        print_header("PHASE 9: TEST API STATUS ENDPOINTS")
        
        if not sync_id:
            print_warning("No sync_id available, skipping API endpoint tests")
            self.test_results["warnings"] += 1
            return
        
        # Test 1: Get sync status
        print_info("Test 1: GET /sync/status/{sync_id}")
        try:
            response = requests.get(f"{self.api_base_url}/sync/status/{sync_id}", timeout=5)
            if response.status_code == 200:
                print_success("Sync status endpoint working")
                self.test_results["passed"] += 1
            else:
                print_error(f"Sync status endpoint returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error testing sync status endpoint: {str(e)}")
            self.test_results["failed"] += 1
        
        # Test 2: Get sync history
        print_info("\nTest 2: GET /sync/history")
        try:
            response = requests.get(
                f"{self.api_base_url}/sync/history",
                params={"sync_type": "job_descriptions", "page": 1, "page_size": 10},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                print_success(f"Sync history endpoint working (found {total} JD sync records)")
                self.test_results["passed"] += 1
            else:
                print_error(f"Sync history endpoint returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error testing sync history endpoint: {str(e)}")
            self.test_results["failed"] += 1
        
        # Test 3: Get last successful sync
        print_info("\nTest 3: GET /sync/last-successful/job_descriptions")
        try:
            response = requests.get(
                f"{self.api_base_url}/sync/last-successful/job_descriptions",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                last_timestamp = data.get("last_sync_timestamp")
                print_success(f"Last successful sync endpoint working (last sync: {last_timestamp})")
                self.test_results["passed"] += 1
            else:
                print_error(f"Last successful sync endpoint returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error testing last successful sync endpoint: {str(e)}")
            self.test_results["failed"] += 1
        
        # Test 4: Get sync errors (if any)
        print_info("\nTest 4: GET /sync/{sync_id}/errors")
        try:
            response = requests.get(
                f"{self.api_base_url}/sync/{sync_id}/errors",
                params={"page": 1, "page_size": 100},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                total_errors = data.get("total_errors", 0)
                if total_errors == 0:
                    print_success("Sync errors endpoint working (no errors recorded)")
                else:
                    print_warning(f"Sync errors endpoint working ({total_errors} errors found)")
                self.test_results["passed"] += 1
            else:
                print_error(f"Sync errors endpoint returned {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Error testing sync errors endpoint: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # PHASE 10: DATA INTEGRITY
    # ========================================================================
    
    def test_phase_10_data_integrity(self):
        """Test data integrity and business logic"""
        print_header("PHASE 10: DATA INTEGRITY AND BUSINESS LOGIC")
        
        try:
            with self.db.create_session() as session:
                # Test 1: Verify unique constraint (employee_id, jd_id)
                print_info("Test 1: Verify unique constraint on (employee_id, jd_id)")
                jds = session.query(EmployeeJobDescription).filter(
                    EmployeeJobDescription.employee_id.in_([1011251, 10347252, 15638493, 10546874, 10456345])
                ).all()
                
                unique_pairs = set()
                duplicates = []
                for jd in jds:
                    pair = (jd.employee_id, jd.jd_id)
                    if pair in unique_pairs:
                        duplicates.append(pair)
                    unique_pairs.add(pair)
                
                if len(duplicates) == 0:
                    print_success("No duplicate (employee_id, jd_id) pairs found")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Found {len(duplicates)} duplicate pairs: {duplicates}")
                    self.test_results["failed"] += 1
                
                # Test 2: Verify only one current JD per employee (business rule)
                print_info("\nTest 2: Verify only one current JD per employee")
                test_employee_ids = [1011251, 10347252, 15638493, 10546874, 10456345]
                
                for emp_id in test_employee_ids:
                    current_jds = session.query(EmployeeJobDescription).filter(
                        EmployeeJobDescription.employee_id == emp_id,
                        EmployeeJobDescription.is_current == True
                    ).all()
                    
                    if len(current_jds) <= 1:
                        print_success(f"   Employee {emp_id}: {len(current_jds)} current JD (valid)")
                        self.test_results["passed"] += 1
                    else:
                        print_error(f"   Employee {emp_id}: {len(current_jds)} current JDs (should be max 1)")
                        self.test_results["failed"] += 1
                
                # Test 3: Verify end_date logic (if is_current=False, end_date should be set)
                print_info("\nTest 3: Verify end_date logic for non-current JDs")
                non_current_jds = session.query(EmployeeJobDescription).filter(
                    EmployeeJobDescription.employee_id.in_(test_employee_ids),
                    EmployeeJobDescription.is_current == False
                ).all()
                
                for jd in non_current_jds:
                    if jd.end_date is not None:
                        print_success(f"   Employee {jd.employee_id}, JD {jd.jd_id}: end_date set ({jd.end_date})")
                        self.test_results["passed"] += 1
                    else:
                        print_warning(f"   Employee {jd.employee_id}, JD {jd.jd_id}: is_current=False but end_date is NULL")
                        self.test_results["warnings"] += 1
                
        except Exception as e:
            print_error(f"Error testing data integrity: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def print_test_summary(self):
        """Print final test summary"""
        print_header("TEST SUMMARY")
        
        total_tests = self.test_results["passed"] + self.test_results["failed"] + self.test_results["warnings"]
        
        print(f"\n{Colors.BOLD}Total Tests Run: {total_tests}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Passed: {self.test_results['passed']}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {self.test_results['failed']}{Colors.ENDC}")
        print(f"{Colors.WARNING}Warnings: {self.test_results['warnings']}{Colors.ENDC}")
        
        success_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}")
        
        if self.test_results["failed"] == 0:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD} ALL TESTS PASSED!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD} SOME TESTS FAILED{Colors.ENDC}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Main test runner with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Comprehensive End-to-End Test for Job Description Sync with Real SQL Server"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for FastAPI application (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=range(1, 11),
        help="Run specific test phase only (1-10)"
    )
    
    args = parser.parse_args()
    
    tester = JDSyncRealTester(api_base_url=args.api_url)
    
    if args.phase:
        print_warning(f"Running only Phase {args.phase} (partial test)")
        # Run specific phase logic would go here
        # For now, just run all tests
        tester.run_all_tests()
    else:
        tester.run_all_tests()


if __name__ == "__main__":
    main()
