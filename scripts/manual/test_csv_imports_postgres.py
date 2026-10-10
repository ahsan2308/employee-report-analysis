"""
Test script for CSV import functionality with PostgreSQL.

This script tests the CSV import functionality for both employee reports and vision data
using the actual PostgreSQL database, then cleans up the data afterward.
"""
import os
import sys
import uuid
import tempfile
import pandas as pd
from datetime import datetime, date, timedelta
import json
import unittest
import time

# Add parent directory to path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database
from app.models.db_models import Employee, Report
from app.models.vision_data_models import EmployeeVisionData
from app.models.import_models import CSVImportJob, ImportStatus, CSVImportType
from app.services.csv_import_service import CSVImportService, get_csv_import_service
from app.schemas.csv_import_schema import CSVImportOptions


class TestCSVImportsPostgres:
    """
    Test class for CSV import functionality using real PostgreSQL database.
    
    This will test both the employee report CSV format and the vision data CSV format.
    It will clean up all test data after running.
    """
    
    def __init__(self):
        """Initialize the test class with database connection."""
        self.db_instance = get_database()
        self.session = self.db_instance.create_session()
        self.import_service = get_csv_import_service()
        self.test_employee_ids = []
    
    def setup(self):
        """Set up test data."""
        print("Setting up test data...")
        
        try:
            # Create test employees
            for i in range(1, 4):
                # Generate a unique ID for test employees (large numbers unlikely to conflict)
                test_id = 900000 + i
                
                # Check if employee already exists
                existing = self.session.query(Employee).filter(Employee.id == test_id).first()
                if not existing:
                    employee = Employee(
                        id=test_id,
                        name=f"Test Employee {i}",
                        position=f"Test Position {i}",
                        wing="Test Department"
                    )
                    self.session.add(employee)
                
                self.test_employee_ids.append(test_id)
            
            self.session.commit()
            print(f"Created test employees with IDs: {self.test_employee_ids}")
            
        except Exception as e:
            self.session.rollback()
            print(f"Error setting up test data: {str(e)}")
            raise
    
    def cleanup(self):
        """Clean up all test data."""
        print("\nCleaning up test data...")
        
        try:
            # Delete test reports
            for emp_id in self.test_employee_ids:
                # Delete reports for test employees
                reports = self.session.query(Report).filter(Report.employee_id == emp_id).all()
                for report in reports:
                    self.session.delete(report)
                
                # Delete vision data for test employees
                vision_data = self.session.query(EmployeeVisionData).filter(
                    EmployeeVisionData.employee_id == emp_id
                ).all()
                for record in vision_data:
                    self.session.delete(record)
            
            # Delete test employees
            for emp_id in self.test_employee_ids:
                employee = self.session.query(Employee).filter(Employee.id == emp_id).first()
                if employee:
                    self.session.delete(employee)
            
            # Delete test import jobs
            jobs = self.session.query(CSVImportJob).filter(
                CSVImportJob.filename.like('test_%')
            ).all()
            for job in jobs:
                self.session.delete(job)
                
            self.session.commit()
            print("Test data cleanup complete")
            
        except Exception as e:
            self.session.rollback()
            print(f"Error cleaning up test data: {str(e)}")
        finally:
            self.session.close()
    
    def create_employee_report_csv(self):
        """Create a test CSV file for employee reports."""
        # Create a temporary CSV file
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        
        # Sample data for employee reports
        data = {
            'Employee_ID': self.test_employee_ids,
            'Name': [f"Test Employee {i}" for i in range(1, 4)],
            'Designation': [f"Test Position {i}" for i in range(1, 4)],
            'From': [(date.today() - timedelta(days=7)).strftime('%Y-%m-%d') for _ in range(3)],
            'To': [date.today().strftime('%Y-%m-%d') for _ in range(3)],
            'Tasks_Completed': [
                "Completed feature X and fixed 3 bugs",
                "Conducted team meeting and finalized Q3 roadmap",
                "Analyzed financial reports and created summary"
            ],
            'Impact': [
                "Feature X improves user experience by 20%",
                "Team has clear direction for Q3",
                "Management has financial data for decision making"
            ],
            'Challenges': [
                "Integration issues with service Y",
                "Team members on vacation",
                "Data inconsistencies in source systems"
            ],
            'Support_Required': [
                "Need access to service Y documentation",
                "Additional resources for Q3 implementation",
                "Better data quality controls"
            ],
            'Tasks_Planned': [
                "Implement feature Z",
                "Start recruitment for new position",
                "Create financial projections for Q4"
            ],
            'Confidence_Level': [4, 5, 3]
        }
        
        # Create a DataFrame and save to CSV
        df = pd.DataFrame(data)
        df.to_csv(path, index=False)
        
        return path
    
    def create_vision_data_csv(self):
        """Create a test CSV file for vision data."""
        # Create a temporary CSV file
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)

        # Sample data for vision data
        data = {
            'Employee_ID': self.test_employee_ids,
            'From_Date': [(date.today() - timedelta(days=30)).strftime('%Y-%m-%d') for _ in range(3)],
            'To_Date': [date.today().strftime('%Y-%m-%d') for _ in range(3)],
            'Main_Entity': ["Tasks", "Persons", "Organizations"],
            'Sub_Entities': [
                json.dumps({"Task1": 5, "Task2": 3, "Task3": 2}),
                json.dumps({"Person1": 10, "Person2": 7, "Person3": 4}),
                json.dumps({"Org1": 2, "Org2": 3, "Org3": 1})
            ],
            'Sub_Entities_Content': [
                json.dumps({"Task1": [{"id": 1, "desc": "A"}], "Task2": [], "Task3": []}),
                json.dumps({"Person1": [], "Person2": [{"id": 2, "desc": "B"}], "Person3": []}),
                json.dumps({"Org1": [], "Org2": [], "Org3": [{"id": 3, "desc": "C"}]})
            ]
        }

        # Create a DataFrame and save to CSV
        df = pd.DataFrame(data)
        df.to_csv(path, index=False)

        return path
    
    def test_employee_report_import(self):
        """Test importing employee report CSV."""
        print("\n=== Testing Employee Report CSV Import ===")
        
        # Create test CSV file
        csv_path = self.create_employee_report_csv()
        
        try:
            # Create an import job
            job_id = str(uuid.uuid4())
            
            # Create job record
            job = CSVImportJob(
                job_id=job_id,
                filename="test_employee_report.csv",
                status=ImportStatus.PENDING.value,
                csv_type=CSVImportType.EMPLOYEE_REPORT.value
            )
            self.session.add(job)
            self.session.commit()
            
            # Process the file
            options = CSVImportOptions(
                chunk_size=10,
                processing_mode="bulk"
            )
            
            start_time = time.time()
            result = self.import_service.process_csv_file(
                job_id=job_id,
                file_path=csv_path,
                options=options
            )
            elapsed = time.time() - start_time
            
            # Verify the job status
            self.session.refresh(job)
            print(f"Job status: {job.status}")
            print(f"Elapsed time: {elapsed:.2f} seconds")
            
            # Verify that reports were created
            for emp_id in self.test_employee_ids:
                reports = self.session.query(Report).filter(Report.employee_id == emp_id).all()
                print(f"Employee {emp_id} has {len(reports)} reports")
                for report in reports:
                    print(f"  Report date: {report.report_date}, content length: {len(report.report_text)} chars")
            
            # Verify metrics
            metrics = result.get('metrics', {})
            print(f"CSV Type: {result.get('csv_type')}")
            print(f"Metrics: {json.dumps(metrics, indent=2)}")
            
            assert job.status == ImportStatus.COMPLETED.value, "Job should be completed"
            assert result.get('successful_rows') == 3, "Should have 3 successful rows"
            
        finally:
            # Clean up the test file
            os.remove(csv_path)
    
    def test_vision_data_import(self):
        """Test importing vision data CSV."""
        print("\n=== Testing Vision Data CSV Import ===")
        
        # Create test CSV file
        csv_path = self.create_vision_data_csv()
        
        try:
            # Create an import job
            job_id = str(uuid.uuid4())
            
            # Create job record
            job = CSVImportJob(
                job_id=job_id,
                filename="test_vision_data.csv",
                status=ImportStatus.PENDING.value,
                csv_type=CSVImportType.VISION_DATA.value
            )
            self.session.add(job)
            self.session.commit()
            
            # Process the file
            options = CSVImportOptions(
                chunk_size=10,
                processing_mode="bulk"
            )
            
            start_time = time.time()
            result = self.import_service.process_csv_file(
                job_id=job_id,
                file_path=csv_path,
                options=options
            )
            elapsed = time.time() - start_time
            
            # Verify the job status
            self.session.refresh(job)
            print(f"Job status: {job.status}")
            print(f"Elapsed time: {elapsed:.2f} seconds")
            
            # Verify that vision data was created
            for emp_id in self.test_employee_ids:
                vision_data = self.session.query(EmployeeVisionData).filter(
                    EmployeeVisionData.employee_id == emp_id
                ).all()
                print(f"Employee {emp_id} has {len(vision_data)} vision data records")
                for record in vision_data:
                    print(f"  Entity: {record.main_entity}, sub-entities: {record.sub_entities}, sub-entities-content: {record.sub_entities_content}")

            # Verify metrics
            metrics = result.get('metrics', {})
            print(f"CSV Type: {result.get('csv_type')}")
            print(f"Metrics: {json.dumps(metrics, indent=2)}")
            
            assert job.status == ImportStatus.COMPLETED.value, "Job should be completed"
            assert result.get('successful_rows') == 3, "Should have 3 successful rows"
            
        finally:
            # Clean up the test file
            os.remove(csv_path)
    
    def run_tests(self):
        """Run all tests."""
        try:
            self.setup()
            self.test_employee_report_import()
            self.test_vision_data_import()
            print("\n✅ All tests completed successfully!")
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
        finally:
            self.cleanup()


if __name__ == "__main__":
    print("Starting CSV import tests with PostgreSQL...")
    tester = TestCSVImportsPostgres()
    tester.run_tests()
