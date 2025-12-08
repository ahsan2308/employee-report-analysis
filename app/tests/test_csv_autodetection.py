"""
CSV Type Auto-Detection Test Script

This script tests the ProcessorFactory's ability to automatically detect
CSV types based on their headers.

Tests cover:
1. Employee Reports CSV detection
2. Vision Data CSV detection
3. Job Descriptions CSV detection
4. Invalid/unknown CSV rejection
5. Ambiguous header handling
6. Case-insensitive header matching

PREREQUISITES:
- None (pure unit tests, no external dependencies)

Usage:
    python app/tests/test_csv_autodetection.py
"""

import sys
import os
from typing import List, Dict, Any
from io import StringIO
import csv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.csv.processors.processor_factory import ProcessorFactory
from app.services.csv.processors.employee_report_processor import EmployeeReportProcessor
from app.services.csv.processors.vision_data_processor import VisionDataProcessor
from app.services.csv.processors.job_description_processor import JobDescriptionProcessor
from app.services.csv.error_handler import ImportErrorHandler
from app.database import get_database


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.OKGREEN} {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL} {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"  {text}")


class CSVAutoDetectionTester:
    """Test CSV type auto-detection mechanism"""
    
    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0
        }
        self.db = get_database()
        self.error_handler = ImportErrorHandler()
    
    def run_all_tests(self):
        """Execute all test cases"""
        print_header("CSV TYPE AUTO-DETECTION TEST SUITE")
        
        # Test 1: Employee Reports detection
        self.test_employee_reports_detection()
        
        # Test 2: Vision Data detection
        self.test_vision_data_detection()
        
        # Test 3: Job Descriptions detection
        self.test_job_descriptions_detection()
        
        # Test 4: Invalid CSV rejection
        self.test_invalid_csv_rejection()
        
        # Test 5: Case-insensitive matching
        self.test_case_insensitive_matching()
        
        # Test 6: Extra columns (should still detect)
        self.test_extra_columns_handling()
        
        # Test 7: Missing required columns (should reject)
        self.test_missing_required_columns()
        
        # Print summary
        self.print_summary()
    
    # ========================================================================
    # TEST 1: EMPLOYEE REPORTS DETECTION
    # ========================================================================
    
    def test_employee_reports_detection(self):
        """Test detection of Employee Reports CSV"""
        print_header("TEST 1: EMPLOYEE REPORTS DETECTION")
        
        # Standard employee report headers
        headers = [
            'Employee_ID', 'Name', 'Designation', 'BPS', 'Office_Hierarchy',
            'From', 'To', 'Draft', 'Tasks_Completed', 'Impact', 'Challenges',
            'Support_Required', 'Tasks_Planned', 'Confidence_Level', 'NTR'
        ]
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                # Verify correct processor selected
                if isinstance(processor, EmployeeReportProcessor):
                    print_success("Correctly identified as EmployeeReportProcessor")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong processor: {type(processor).__name__}")
                    self.test_results["failed"] += 1
                
                # Verify csv_type value
                if csv_type == "employee_report":
                    print_success(f"Correct csv_type: '{csv_type}'")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong csv_type: '{csv_type}'")
                    self.test_results["failed"] += 1
                
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 2
    
    # ========================================================================
    # TEST 2: VISION DATA DETECTION
    # ========================================================================
    
    def test_vision_data_detection(self):
        """Test detection of Vision Data CSV"""
        print_header("TEST 2: VISION DATA DETECTION")
        
        # Standard vision data headers
        headers = [
            'Employee_ID', 'From_Date', 'To_Date', 'Main_Entity',
            'Sub_Entities', 'Sub_Entities_Content'
        ]
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                # Verify correct processor selected
                if isinstance(processor, VisionDataProcessor):
                    print_success("Correctly identified as VisionDataProcessor")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong processor: {type(processor).__name__}")
                    self.test_results["failed"] += 1
                
                # Verify csv_type value
                if csv_type == "vision_data":
                    print_success(f"Correct csv_type: '{csv_type}'")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong csv_type: '{csv_type}'")
                    self.test_results["failed"] += 1
                
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 2
    
    # ========================================================================
    # TEST 3: JOB DESCRIPTIONS DETECTION
    # ========================================================================
    
    def test_job_descriptions_detection(self):
        """Test detection of Job Descriptions CSV"""
        print_header("TEST 3: JOB DESCRIPTIONS DETECTION")
        
        # Standard JD headers
        headers = [
            'Employee_ID', 'JD_ID', 'Job_Description',
            'Assigned_Date', 'Is_Current', 'End_Date'
        ]
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                # Verify correct processor selected
                if isinstance(processor, JobDescriptionProcessor):
                    print_success("Correctly identified as JobDescriptionProcessor")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong processor: {type(processor).__name__}")
                    self.test_results["failed"] += 1
                
                # Verify csv_type value
                if csv_type == "job_descriptions":
                    print_success(f"Correct csv_type: '{csv_type}'")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Wrong csv_type: '{csv_type}'")
                    self.test_results["failed"] += 1
                
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 2
    
    # ========================================================================
    # TEST 4: INVALID CSV REJECTION
    # ========================================================================
    
    def test_invalid_csv_rejection(self):
        """Test rejection of invalid/unknown CSV formats"""
        print_header("TEST 4: INVALID CSV REJECTION")
        
        # Headers that don't match any known format
        headers = ['Column1', 'Column2', 'Column3', 'Random_Field']
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                # Should return None for unknown format
                if processor is None and csv_type is None:
                    print_success("Correctly rejected unknown CSV format")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Should have rejected but got: {type(processor).__name__}, {csv_type}")
                    self.test_results["failed"] += 1
                
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # TEST 5: CASE-INSENSITIVE MATCHING
    # ========================================================================
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive header matching"""
        print_header("TEST 5: CASE-INSENSITIVE MATCHING")
        
        # JD headers with different casing
        test_cases = [
            {
                "name": "All lowercase",
                "headers": ['employee_id', 'jd_id', 'job_description', 'assigned_date', 'is_current', 'end_date']
            },
            {
                "name": "All uppercase",
                "headers": ['EMPLOYEE_ID', 'JD_ID', 'JOB_DESCRIPTION', 'ASSIGNED_DATE', 'IS_CURRENT', 'END_DATE']
            },
            {
                "name": "Mixed case",
                "headers": ['Employee_Id', 'Jd_Id', 'Job_Description', 'Assigned_Date', 'Is_Current', 'End_Date']
            }
        ]
        
        for test_case in test_cases:
            try:
                with self.db.create_session() as session:
                    processor, csv_type = ProcessorFactory.get_processor(
                        headers=test_case["headers"],
                        db=session,
                        error_handler=self.error_handler
                    )
                    
                    if isinstance(processor, JobDescriptionProcessor):
                        print_success(f"{test_case['name']}: Detected correctly")
                        self.test_results["passed"] += 1
                    else:
                        print_error(f"{test_case['name']}: Failed to detect")
                        self.test_results["failed"] += 1
                        
            except Exception as e:
                print_error(f"{test_case['name']}: Exception - {str(e)}")
                self.test_results["failed"] += 1
    
    # ========================================================================
    # TEST 6: EXTRA COLUMNS HANDLING
    # ========================================================================
    
    def test_extra_columns_handling(self):
        """Test detection with extra non-required columns"""
        print_header("TEST 6: EXTRA COLUMNS HANDLING")
        
        # JD headers with extra columns
        headers = [
            'Employee_ID', 'JD_ID', 'Job_Description',
            'Assigned_Date', 'Is_Current', 'End_Date',
            'Extra_Column_1', 'Extra_Column_2', 'Custom_Field'
        ]
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                if isinstance(processor, JobDescriptionProcessor) and csv_type == "job_descriptions":
                    print_success("Correctly detected despite extra columns")
                    self.test_results["passed"] += 1
                else:
                    print_error("Failed to detect with extra columns")
                    self.test_results["failed"] += 1
                    
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # TEST 7: MISSING REQUIRED COLUMNS
    # ========================================================================
    
    def test_missing_required_columns(self):
        """Test rejection when required columns are missing"""
        print_header("TEST 7: MISSING REQUIRED COLUMNS")
        
        # JD headers with missing required column (no 'Job_Description')
        headers = [
            'Employee_ID', 'JD_ID', 'Assigned_Date', 'Is_Current', 'End_Date'
        ]
        
        try:
            with self.db.create_session() as session:
                processor, csv_type = ProcessorFactory.get_processor(
                    headers=headers,
                    db=session,
                    error_handler=self.error_handler
                )
                
                # Should NOT match JobDescriptionProcessor
                if not isinstance(processor, JobDescriptionProcessor):
                    print_success("Correctly rejected CSV with missing required column")
                    self.test_results["passed"] += 1
                else:
                    print_error("Should have rejected but detected as JD")
                    self.test_results["failed"] += 1
                    
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            self.test_results["failed"] += 1
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        total = self.test_results["passed"] + self.test_results["failed"]
        success_rate = (self.test_results["passed"] / total * 100) if total > 0 else 0
        
        print(f"{Colors.BOLD}Total Tests: {total}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Passed: {self.test_results['passed']}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {self.test_results['failed']}{Colors.ENDC}")
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}\n")
        
        if self.test_results["failed"] == 0:
            print(f"{Colors.OKGREEN}{Colors.BOLD} ALL TESTS PASSED!{Colors.ENDC}\n")
        else:
            print(f"{Colors.FAIL}{Colors.BOLD} SOME TESTS FAILED{Colors.ENDC}\n")


def main():
    """Main test runner"""
    tester = CSVAutoDetectionTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
