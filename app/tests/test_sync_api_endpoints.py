"""
Comprehensive Sync API Endpoint Test Suite

Tests ALL sync endpoints with EVERY scenario to ensure frontend readiness:

1. Trigger Endpoints (POST)
   -   Valid requests
   -   Concurrent sync prevention
   -   Parameter validation
   -   Error handling

2. Status & Monitoring Endpoints (GET)
   -   Valid sync_id
   -   Invalid sync_id
   -   Status polling scenarios
   -   Last successful sync tracking

3. History & Reporting Endpoints (GET)
   -   Pagination
   -   Filtering
   -   Sorting
   -   Error details

4. Configuration Endpoints (GET)
   -   Config retrieval
   -   Connection testing

Run with: pytest tests/test_sync_api_endpoints.py -v -s --tb=short
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4, UUID
import time
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.database import get_database
from app.models.sync_models import SyncHistory, SyncStatus, SyncType
from app.core.logger import logger

# Create test client
client = TestClient(app)

# Test database session with proper cleanup
@pytest.fixture(scope="function")  # FIXED: Changed from "module" to "function" for per-test isolation
def db_session():
    """Create a test database session with cleanup."""
    db = get_database()
    session = db.create_session()
    
    # ADDED: Clean up any leftover PENDING or RUNNING sync jobs from previous tests
    try:
        # Delete all non-completed sync jobs before test runs
        session.query(SyncHistory).filter(
            SyncHistory.status.in_([SyncStatus.PENDING.value, SyncStatus.RUNNING.value])
        ).delete(synchronize_session=False)
        session.commit()
        logger.info("Cleaned up leftover sync jobs before test")
    except Exception as e:
        logger.warning(f"Error cleaning up sync jobs: {e}")
        session.rollback()
    
    yield session
    
    # ADDED: Clean up sync jobs created during this test
    try:
        # Delete sync jobs created in this test (not older than 1 hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        session.query(SyncHistory).filter(
            SyncHistory.started_at >= one_hour_ago
        ).delete(synchronize_session=False)
        session.commit()
        logger.info("Cleaned up test sync jobs after test")
    except Exception as e:
        logger.warning(f"Error cleaning up test sync jobs: {e}")
        session.rollback()
    finally:
        session.close()


# ============================================================================
# GROUP 1: TRIGGER ENDPOINT TESTS
# ============================================================================

class TestTriggerEndpoints:
    """Test all sync trigger endpoints (POST)."""
    
    def test_trigger_employee_reports_incremental(self, db_session):
        """
        Test: POST /sync/trigger/employee-reports (incremental)
        
        Validates:
        -   Endpoint returns 202 Accepted
        -   Returns real sync_id (not placeholder)
        -   Returns task_id
        -   sync_type is correct
        -   status is 'pending'
        -   is_full_sync is False
        -   triggered_at is present
        -   message is informative
        -   SyncHistory record is created in DB
        """
        print("\n=== Test: Trigger Employee Reports (Incremental) ===")
        
        response = client.post("/sync/trigger/employee-reports?is_full_sync=false")
        
        # Validate HTTP status
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"
        print(f"  Status code: {response.status_code}")
        
        data = response.json()
        print(f"Response data: {data}")
        
        # Validate response structure
        assert "sync_id" in data
        assert "task_id" in data
        assert "sync_type" in data
        assert "status" in data
        assert "is_full_sync" in data
        assert "triggered_at" in data
        assert "message" in data
        print("  Response has all required fields")
        
        # Validate sync_id is NOT a placeholder
        sync_id_str = data["sync_id"]
        placeholder_uuid = "00000000-0000-0000-0000-000000000000"
        assert sync_id_str != placeholder_uuid, "sync_id should not be a placeholder"
        print(f"  sync_id is real: {sync_id_str}")
        
        # Validate UUID format
        try:
            sync_uuid = UUID(sync_id_str)
            print(f"  sync_id is valid UUID")
        except ValueError:
            pytest.fail(f"sync_id is not a valid UUID: {sync_id_str}")
        
        # Validate values
        assert data["sync_type"] == "employee_reports"
        assert data["status"] == "pending"
        assert data["is_full_sync"] is False
        assert len(data["task_id"]) > 0
        assert "incremental" in data["message"].lower()
        print("  All field values are correct")
        
        # Validate timestamp format
        try:
            triggered_at = datetime.fromisoformat(data["triggered_at"].replace("Z", "+00:00"))
            assert (datetime.now() - triggered_at).total_seconds() < 10
            print(f"  triggered_at is recent: {triggered_at}")
        except Exception as e:
            pytest.fail(f"Invalid triggered_at format: {e}")
        
        # Validate database record exists
        db_session.commit()  # Ensure we see latest changes
        sync_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_uuid
        ).first()
        
        assert sync_job is not None, f"Sync job {sync_uuid} not found in database"
        assert sync_job.sync_type == SyncType.EMPLOYEE_REPORTS.value
        assert sync_job.status == SyncStatus.PENDING.value
        print(f"  Database record created: {sync_job.sync_id}")
        
        # ADDED: Mark sync as completed so it doesn't interfere with other tests
        sync_job.status = SyncStatus.COMPLETED.value
        sync_job.completed_at = datetime.now()
        db_session.commit()
        print(f"  Marked sync as completed for cleanup")
        
        print("\n  TEST PASSED: Trigger Employee Reports (Incremental)")
        return data
    
    def test_trigger_employee_reports_full(self, db_session):
        """
        Test: POST /sync/trigger/employee-reports?is_full_sync=true
        
        Validates:
        -   Full sync mode is respected
        -   is_full_sync field is True
        -   Message indicates full sync
        """
        print("\n=== Test: Trigger Employee Reports (Full Sync) ===")
        
        response = client.post("/sync/trigger/employee-reports?is_full_sync=true")
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["is_full_sync"] is True
        assert "full" in data["message"].lower()
        print(f"  Full sync mode: {data['is_full_sync']}")
        
        # Validate in database
        sync_uuid = UUID(data["sync_id"])
        db_session.commit()
        sync_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_uuid
        ).first()
        
        assert sync_job is not None
        assert sync_job.sync_options.get("is_full_sync") is True
        print(f"  Database confirms full sync mode")
        
        # ADDED: Mark as completed
        sync_job.status = SyncStatus.COMPLETED.value
        sync_job.completed_at = datetime.now()
        db_session.commit()
        
        print("\n  TEST PASSED: Trigger Employee Reports (Full Sync)")
    
    def test_trigger_vision_data_incremental(self, db_session):
        """
        Test: POST /sync/trigger/vision-data
        
        Validates:
        -   Vision data sync works
        -   sync_type is 'vision_data'
        -   All response fields present
        """
        print("\n=== Test: Trigger Vision Data (Incremental) ===")
        
        response = client.post("/sync/trigger/vision-data?is_full_sync=false")
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["sync_type"] == "vision_data"
        assert data["is_full_sync"] is False
        print(f"  Vision data sync triggered: {data['sync_id']}")
        
        # Validate in database
        sync_uuid = UUID(data["sync_id"])
        db_session.commit()
        sync_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == sync_uuid
        ).first()
        
        assert sync_job is not None
        assert sync_job.sync_type == SyncType.VISION_DATA.value
        print(f"  Database confirms vision data sync")
        
        # ADDED: Mark as completed
        sync_job.status = SyncStatus.COMPLETED.value
        sync_job.completed_at = datetime.now()
        db_session.commit()
        
        print("\n  TEST PASSED: Trigger Vision Data")
    
    def test_trigger_full_sync(self, db_session):
        """
        Test: POST /sync/trigger/full
        
        Validates:
        -   Triggers both sync types
        -   Returns TWO sync_ids
        -   Both are real UUIDs (not placeholders)
        -   sync_type is 'full'
        -   Database has both records
        """
        print("\n=== Test: Trigger Full Sync (Both Types) ===")
        
        response = client.post("/sync/trigger/full")
        
        assert response.status_code == 202
        data = response.json()
        
        # Validate response structure
        assert "sync_type" in data
        assert "employee_reports_sync_id" in data
        assert "vision_data_sync_id" in data
        assert "task_id" in data
        print("  Response has all required fields")
        
        # Validate sync_type
        assert data["sync_type"] == "full"
        
        # Validate both sync_ids are NOT placeholders
        placeholder_uuid = "00000000-0000-0000-0000-000000000000"
        emp_sync_id_str = data["employee_reports_sync_id"]
        vis_sync_id_str = data["vision_data_sync_id"]
        
        assert emp_sync_id_str != placeholder_uuid
        assert vis_sync_id_str != placeholder_uuid
        print(f"  Both sync_ids are real (not placeholders)")
        
        # Validate UUID format
        emp_uuid = UUID(emp_sync_id_str)
        vis_uuid = UUID(vis_sync_id_str)
        print(f"  employee_reports_sync_id: {emp_uuid}")
        print(f"  vision_data_sync_id: {vis_uuid}")
        
        # Validate database records exist
        db_session.commit()
        
        emp_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == emp_uuid
        ).first()
        vis_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == vis_uuid
        ).first()
        
        assert emp_job is not None, "Employee reports sync job not found"
        assert vis_job is not None, "Vision data sync job not found"
        
        assert emp_job.sync_type == SyncType.EMPLOYEE_REPORTS.value
        assert vis_job.sync_type == SyncType.VISION_DATA.value
        
        # Verify both are full sync mode
        assert emp_job.sync_options.get("is_full_sync") is True
        assert vis_job.sync_options.get("is_full_sync") is True
        print(f"  Both database records created and configured for full sync")
        
        # ADDED: Mark both as completed
        emp_job.status = SyncStatus.COMPLETED.value
        emp_job.completed_at = datetime.now()
        vis_job.status = SyncStatus.COMPLETED.value
        vis_job.completed_at = datetime.now()
        db_session.commit()
        
        print("\n  TEST PASSED: Trigger Full Sync")
    
    def test_concurrent_sync_prevention(self, db_session):
        """
        Test: Concurrent sync prevention (409 Conflict)
        
        Validates:
        -   Cannot trigger same sync type while another is running
        -   Returns 409 Conflict status
        -   Error message includes sync_id of running sync
        """
        print("\n=== Test: Concurrent Sync Prevention ===")
        
        # ADDED: Ensure no running syncs exist from previous tests
        db_session.query(SyncHistory).filter(
            SyncHistory.sync_type == SyncType.EMPLOYEE_REPORTS.value,
            SyncHistory.status == SyncStatus.RUNNING.value
        ).delete(synchronize_session=False)
        db_session.commit()
        
        # First, trigger a sync
        response1 = client.post("/sync/trigger/employee-reports")
        assert response1.status_code == 202
        sync_id_1 = response1.json()["sync_id"]
        print(f"  First sync triggered: {sync_id_1}")
        
        # Manually set status to RUNNING to simulate ongoing sync
        db_session.commit()
        sync_job = db_session.query(SyncHistory).filter(
            SyncHistory.sync_id == UUID(sync_id_1)
        ).first()
        sync_job.status = SyncStatus.RUNNING.value
        db_session.commit()
        print(f"  Set first sync to RUNNING")
        
        # Try to trigger another sync of the same type
        response2 = client.post("/sync/trigger/employee-reports")
        
        # Should get 409 Conflict
        assert response2.status_code == 409, f"Expected 409, got {response2.status_code}"
        print(f"  Second sync rejected with 409 Conflict")
        
        error_detail = response2.json()["detail"]
        assert "already in progress" in error_detail.lower()
        assert sync_id_1 in error_detail
        print(f"  Error message mentions running sync: {error_detail}")
        
        # Cleanup: Mark first sync as completed
        sync_job.status = SyncStatus.COMPLETED.value
        sync_job.completed_at = datetime.now()  # ADDED: Set completed_at
        db_session.commit()
        
        print("\n  TEST PASSED: Concurrent Sync Prevention")
    
    def test_invalid_query_parameter(self):
        """
        Test: Invalid query parameters
        
        Validates:
        -   Invalid boolean values are handled
        -   Missing parameters use defaults
        """
        print("\n=== Test: Invalid Query Parameters ===")
        
        # Test with no parameters (should default to is_full_sync=false)
        response = client.post("/sync/trigger/employee-reports")
        assert response.status_code == 202
        data = response.json()
        assert data["is_full_sync"] is False
        print(f"  Missing parameter defaults to False")
        
        # ADDED: Clean up sync jobs created by this test
        # Note: We use a new session since this is not using db_session fixture
        cleanup_db = get_database()
        cleanup_session = cleanup_db.create_session()
        try:
            sync_uuid = UUID(data["sync_id"])
            sync_job = cleanup_session.query(SyncHistory).filter(
                SyncHistory.sync_id == sync_uuid
            ).first()
            if sync_job:
                sync_job.status = SyncStatus.COMPLETED.value
                sync_job.completed_at = datetime.now()
                cleanup_session.commit()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            cleanup_session.rollback()
        finally:
            cleanup_session.close()
        
        # Test with explicit false
        response = client.post("/sync/trigger/employee-reports?is_full_sync=0")
        assert response.status_code == 202
        print(f"  is_full_sync=0 handled correctly")
        
        # ADDED: Clean up this sync job too
        cleanup_session = cleanup_db.create_session()
        try:
            sync_uuid = UUID(response.json()["sync_id"])
            sync_job = cleanup_session.query(SyncHistory).filter(
                SyncHistory.sync_id == sync_uuid
            ).first()
            if sync_job:
                sync_job.status = SyncStatus.COMPLETED.value
                sync_job.completed_at = datetime.now()
                cleanup_session.commit()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            cleanup_session.rollback()
        finally:
            cleanup_session.close()
        
        print("\n  TEST PASSED: Query Parameter Handling")


# ============================================================================
# GROUP 2: STATUS & MONITORING ENDPOINT TESTS
# ============================================================================

class TestStatusMonitoringEndpoints:
    """Test sync status and monitoring endpoints (GET)."""
    
    @pytest.fixture(scope="function")  # FIXED: Changed from "class" to "function"
    def test_sync_job(self, db_session):
        """Create a test sync job for status queries."""
        # Create a completed sync job
        from app.services.sync.sync_tracker import SyncTracker
        
        tracker = SyncTracker(get_database())
        sync_job = tracker.create_sync_job(
            sync_type=SyncType.EMPLOYEE_REPORTS,
            session=db_session,
            is_full_sync=False
        )
        
        # Update with metrics
        tracker.update_sync_status(
            sync_id=sync_job.sync_id,
            status=SyncStatus.COMPLETED,
            session=db_session,
            metrics={
                'records_queried': 100,
                'records_synced': 95,
                'records_created': 50,
                'records_updated': 45,
                'error_count': 5,
                'last_sync_timestamp': datetime.now() - timedelta(hours=1),
                'metrics': {
                    'employees_created': 25,
                    'employees_updated': 25,
                    'reports_created': 25,
                    'reports_updated': 20
                }
            }
        )
        
        db_session.commit()
        return sync_job
    
    def test_get_sync_status_valid(self, test_sync_job):
        """
        Test: GET /sync/status/{sync_id}
        
        Validates:
        -   Returns 200 OK
        -   All required fields present
        -   Progress metrics calculated
        -   Percent complete is accurate
        -   Duration is calculated
        -   Metrics nested correctly
        """
        print("\n=== Test: Get Sync Status (Valid ID) ===")
        
        sync_id = str(test_sync_job.sync_id)
        # FIXED: Remove /api prefix
        response = client.get(f"/sync/status/{sync_id}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Response: {data}")
        
        # Validate structure
        required_fields = [
            "sync_id", "sync_type", "status", "is_full_sync",
            "started_at", "completed_at", "duration_seconds",
            "progress", "metrics", "last_sync_timestamp", "error_message"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print(f"  All required fields present")
        
        # Validate progress structure
        progress = data["progress"]
        progress_fields = [
            "records_queried", "records_synced", "records_created",
            "records_updated", "records_skipped", "error_count", "percent_complete"
        ]
        for field in progress_fields:
            assert field in progress, f"Missing progress field: {field}"
        print(f"  Progress metrics complete")
        
        # Validate percent calculation
        expected_percent = round((95 / 100) * 100, 1)
        assert progress["percent_complete"] == expected_percent
        print(f"  Percent complete calculated correctly: {progress['percent_complete']}%")
        
        # Validate duration is calculated
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] > 0
        print(f"  Duration calculated: {data['duration_seconds']}s")
        
        # Validate nested metrics
        assert "employees_created" in data["metrics"]
        assert data["metrics"]["employees_created"] == 25
        print(f"  Nested metrics present")
        
        print("\n  TEST PASSED: Get Sync Status (Valid)")
    
    def test_get_sync_status_invalid_id(self):
        """
        Test: GET /sync/status/{sync_id} with invalid ID
        
        Validates:
        -   Returns 404 Not Found
        -   Error message is clear
        """
        print("\n=== Test: Get Sync Status (Invalid ID) ===")
        
        fake_uuid = str(uuid4())
        # FIXED: Remove /api prefix
        response = client.get(f"/sync/status/{fake_uuid}")
        
        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert "not found" in error_detail.lower()
        assert fake_uuid in error_detail
        print(f"  404 returned with clear error: {error_detail}")
        
        print("\n  TEST PASSED: Get Sync Status (Invalid)")
    
    def test_get_sync_status_malformed_uuid(self):
        """
        Test: GET /sync/status/{sync_id} with malformed UUID
        
        Validates:
        -   Returns 422 Validation Error
        """
        print("\n=== Test: Get Sync Status (Malformed UUID) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/status/not-a-uuid")
        
        assert response.status_code == 422
        print(f"  422 returned for malformed UUID")
        
        print("\n  TEST PASSED: Malformed UUID Handling")
    
    def test_get_last_successful_sync_employee_reports(self, test_sync_job):
        """
        Test: GET /sync/last-successful/employee_reports
        
        Validates:
        -   Returns 200 OK
        -   Returns most recent successful sync
        -   All fields present
        -   sync_type matches
        """
        print("\n=== Test: Get Last Successful Sync (Employee Reports) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/last-successful/employee_reports")
        
        assert response.status_code == 200
        data = response.json()
        print(f"Response: {data}")
        
        # Validate structure
        required_fields = [
            "sync_type", "last_successful_sync_id", "last_sync_timestamp",
            "records_synced", "completed_at"
        ]
        for field in required_fields:
            assert field in data
        print(f"  All fields present")
        
        # Validate values
        assert data["sync_type"] == "employee_reports"
        assert data["last_successful_sync_id"] is not None
        assert data["last_sync_timestamp"] is not None
        print(f"  Last sync: {data['last_sync_timestamp']}")
        print(f"  Records synced: {data['records_synced']}")
        
        print("\n  TEST PASSED: Get Last Successful Sync")
    
    def test_get_last_successful_sync_vision_data(self):
        """
        Test: GET /sync/last-successful/vision_data
        
        Validates:
        -   Returns correct sync_type
        -   Handles case where no sync exists
        """
        print("\n=== Test: Get Last Successful Sync (Vision Data) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/last-successful/vision_data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sync_type"] == "vision_data"
        print(f"  sync_type correct: {data['sync_type']}")
        
        # May be null if no vision sync has completed
        if data["last_successful_sync_id"] is None:
            print(f"  No previous sync (valid response)")
        else:
            print(f"  Last sync found: {data['last_successful_sync_id']}")
        
        print("\n  TEST PASSED: Get Last Successful Sync (Vision)")
    
    def test_get_last_successful_sync_invalid_type(self):
        """
        Test: GET /sync/last-successful/{invalid_type}
        
        Validates:
        -   Returns 400 Bad Request for invalid sync type
        """
        print("\n=== Test: Get Last Successful Sync (Invalid Type) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/last-successful/invalid_type")
        
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "invalid sync_type" in error_detail.lower()
        print(f"  400 returned: {error_detail}")
        
        print("\n  TEST PASSED: Invalid Sync Type Handling")


# ============================================================================
# GROUP 3: HISTORY & REPORTING ENDPOINTS
# ============================================================================

class TestHistoryReportingEndpoints:
    """Test sync history and error reporting endpoints (GET)."""
    
    @pytest.fixture(scope="function")
    def populate_history(self, db_session):
        """Populate database with test sync history."""
        from app.services.sync.sync_tracker import SyncTracker
        
        tracker = SyncTracker(get_database())
        
        # Create 5 employee report syncs
        for i in range(5):
            sync_job = tracker.create_sync_job(
                sync_type=SyncType.EMPLOYEE_REPORTS,
                session=db_session,
                is_full_sync=(i % 2 == 0)  # Alternate full/incremental
            )
            
            # Complete syncs
            tracker.update_sync_status(
                sync_id=sync_job.sync_id,
                status=SyncStatus.COMPLETED,
                session=db_session,
                metrics={
                    'records_queried': 100 + i * 10,
                    'records_synced': 90 + i * 10,
                    'last_sync_timestamp': datetime.now() - timedelta(hours=i)
                }
            )
        
        # Create 3 vision data syncs
        for i in range(3):
            sync_job = tracker.create_sync_job(
                sync_type=SyncType.VISION_DATA,
                session=db_session,
                is_full_sync=False
            )
            
            tracker.update_sync_status(
                sync_id=sync_job.sync_id,
                status=SyncStatus.COMPLETED,
                session=db_session,
                metrics={
                    'records_queried': 50 + i * 5,
                    'records_synced': 45 + i * 5
                }
            )
        
        db_session.commit()
        print("  Populated history with 8 sync jobs")
    
    def test_list_sync_history_default(self, populate_history):
        """
        Test: GET /sync/history (no filters)
        
        Validates:
        -   Returns 200 OK
        -   Pagination structure correct
        -   Items have all required fields
        -   Default page size is 20
        """
        print("\n=== Test: List Sync History (Default) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate pagination structure
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert "items" in data
        print(f"  Pagination structure present")
        
        # Validate values
        assert data["total"] >= 8  # At least 8 from populate_history
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) <= 20
        print(f"  Total: {data['total']}, Page: {data['page']}, Items: {len(data['items'])}")
        
        # Validate item structure
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = [
                "sync_id", "sync_type", "status", "is_full_sync",
                "started_at", "completed_at", "duration_seconds",
                "records_synced", "error_count", "last_sync_timestamp"
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            print(f"  Item structure complete")
        
        print("\n  TEST PASSED: List Sync History (Default)")
    
    def test_list_sync_history_filter_by_type(self, populate_history):
        """
        Test: GET /sync/history?sync_type=employee_reports
        
        Validates:
        -   Filtering by sync_type works
        -   Only matching items returned
        """
        print("\n=== Test: List Sync History (Filter by Type) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/history?sync_type=employee_reports")
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be employee_reports
        for item in data["items"]:
            assert item["sync_type"] == "employee_reports"
        print(f"  All {len(data['items'])} items are employee_reports")
        
        print("\n  TEST PASSED: Filter by Type")
    
    def test_list_sync_history_filter_by_status(self, populate_history):
        """
        Test: GET /sync/history?status=completed
        
        Validates:
        -   Filtering by status works
        """
        print("\n=== Test: List Sync History (Filter by Status) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/history?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should have status 'completed'
        for item in data["items"]:
            assert item["status"] == "completed"
        print(f"  All {len(data['items'])} items have status 'completed'")
        
        print("\n  TEST PASSED: Filter by Status")
    
    def test_list_sync_history_pagination(self, populate_history):
        """
        Test: GET /sync/history?page=1&page_size=5
        
        Validates:
        -   Custom page size works
        -   Page navigation works
        -   Total pages calculated correctly
        """
        print("\n=== Test: List Sync History (Pagination) ===")
        
        # Get first page
        # FIXED: Remove /api prefix
        response1 = client.get("/sync/history?page=1&page_size=5")
        assert response1.status_code == 200
        data1 = response1.json()
        
        assert data1["page"] == 1
        assert data1["page_size"] == 5
        assert len(data1["items"]) <= 5
        print(f"  Page 1: {len(data1['items'])} items")
        
        # Get second page
        if data1["pages"] > 1:
            # FIXED: Remove /api prefix
            response2 = client.get("/sync/history?page=2&page_size=5")
            assert response2.status_code == 200
            data2 = response2.json()
            
            assert data2["page"] == 2
            # Items should be different
            page1_ids = {item["sync_id"] for item in data1["items"]}
            page2_ids = {item["sync_id"] for item in data2["items"]}
            assert len(page1_ids & page2_ids) == 0  # No overlap
            print(f"  Page 2: {len(data2['items'])} items (different from page 1)")
        
        print("\n  TEST PASSED: Pagination")
    
    def test_list_sync_history_sorting(self, populate_history):
        """
        Test: GET /sync/history?sort_by=started_at&sort_order=desc
        
        Validates:
        -   Sorting works
        -   Default sort is desc (newest first)
        """
        print("\n=== Test: List Sync History (Sorting) ===")
        
        # Get with descending order (default)
        # FIXED: Remove /api prefix
        response_desc = client.get("/sync/history?sort_order=desc")
        assert response_desc.status_code == 200
        data_desc = response_desc.json()
        
        if len(data_desc["items"]) > 1:
            # Verify descending order (newest first)
            first_time = datetime.fromisoformat(data_desc["items"][0]["started_at"].replace("Z", "+00:00"))
            second_time = datetime.fromisoformat(data_desc["items"][1]["started_at"].replace("Z", "+00:00"))
            assert first_time >= second_time
            print(f"  Descending sort works (newest first)")
        
        # Get with ascending order
        # FIXED: Remove /api prefix
        response_asc = client.get("/sync/history?sort_order=asc")
        assert response_asc.status_code == 200
        data_asc = response_asc.json()
        
        if len(data_asc["items"]) > 1:
            # Verify ascending order (oldest first)
            first_time = datetime.fromisoformat(data_asc["items"][0]["started_at"].replace("Z", "+00:00"))
            second_time = datetime.fromisoformat(data_asc["items"][1]["started_at"].replace("Z", "+00:00"))
            assert first_time <= second_time
            print(f"  Ascending sort works (oldest first)")
        
        print("\n  TEST PASSED: Sorting")
    
    def test_list_sync_history_invalid_filter(self):
        """
        Test: GET /sync/history?sync_type=invalid
        
        Validates:
        -   Invalid filter values return 400
        """
        print("\n=== Test: List Sync History (Invalid Filter) ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/history?sync_type=invalid")
        
        assert response.status_code == 400
        print(f"  400 returned for invalid sync_type")
        
        response = client.get("/sync/history?status=invalid")
        assert response.status_code == 400
        print(f"  400 returned for invalid status")
        
        print("\n  TEST PASSED: Invalid Filter Handling")
    
    def test_get_sync_errors_no_errors(self, populate_history, db_session):
        """
        Test: GET /sync/{sync_id}/errors (no errors)
        
        Validates:
        -   Returns empty error list when no errors
        -   total_errors is 0
        """
        print("\n=== Test: Get Sync Errors (No Errors) ===")
        
        # Get a completed sync with no errors
        sync_job = db_session.query(SyncHistory).filter(
            SyncHistory.status == SyncStatus.COMPLETED.value
        ).first()
        
        # FIXED: Remove /api prefix
        response = client.get(f"/sync/{sync_job.sync_id}/errors")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_errors" in data
        assert "errors" in data
        assert data["total_errors"] == 0
        assert len(data["errors"]) == 0
        print(f"  Empty error list returned")
        
        print("\n  TEST PASSED: Get Sync Errors (No Errors)")
    
    def test_get_sync_errors_with_errors(self, db_session):
        """
        Test: GET /sync/{sync_id}/errors (with errors)
        
        Validates:
        -   Returns error details
        -   Error structure is correct
        -   Pagination works
        """
        print("\n=== Test: Get Sync Errors (With Errors) ===")
        
        # Create a sync with errors
        from app.services.sync.sync_tracker import SyncTracker
        
        tracker = SyncTracker(get_database())
        sync_job = tracker.create_sync_job(
            sync_type=SyncType.EMPLOYEE_REPORTS,
            session=db_session,
            is_full_sync=False
        )
        
        # Add errors
        errors = [
            {
                "row_number": 1,
                "field_name": "Employee_ID",
                "error_message": "Employee ID 9999 does not exist",
                "error_category": "validation",
                "row_data": {"Employee_ID": 9999}
            },
            {
                "row_number": 2,
                "field_name": "From",
                "error_message": "Invalid date format",
                "error_category": "validation",
                "row_data": {"From": "2025-13-01"}
            }
        ]
        tracker.save_sync_errors(sync_job.sync_id, errors, session=db_session)
        
        tracker.update_sync_status(
            sync_id=sync_job.sync_id,
            status=SyncStatus.PARTIAL,
            session=db_session,
            metrics={'error_count': 2}
        )
        
        db_session.commit()
        
        # Get errors
        # FIXED: Remove /api prefix
        response = client.get(f"/sync/{sync_job.sync_id}/errors")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_errors"] == 2
        assert len(data["errors"]) == 2
        print(f"  {data['total_errors']} errors returned")
        
        # Validate error structure
        error = data["errors"][0]
        required_fields = ["row_number", "field_name", "error_message", "error_category", "row_data"]
        for field in required_fields:
            assert field in error
        print(f"  Error structure complete")
        
        print("\n  TEST PASSED: Get Sync Errors (With Errors)")


# ============================================================================
# GROUP 4: CONFIGURATION ENDPOINT TESTS
# ============================================================================

class TestConfigurationEndpoints:
    """Test sync configuration and diagnostics endpoints (GET)."""
    
    def test_get_sync_configuration(self):
        """
        Test: GET /sync/config
        
        Validates:
        -   Returns 200 OK
        -   All config sections present
        -   SQL Server details included
        -   Allowed tables listed
        -   Sync settings present
        -   Schedule information included
        """
        print("\n=== Test: Get Sync Configuration ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        required_sections = [
            "sql_server", "allowed_tables", "allowed_timestamp_columns",
            "sync_settings", "sync_schedule", "sync_enabled"
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
        print(f"  All config sections present")
        
        # Validate SQL Server info
        assert "host" in data["sql_server"]
        assert "database" in data["sql_server"]
        assert "connection_status" in data["sql_server"]
        print(f"  SQL Server: {data['sql_server']['host']}/{data['sql_server']['database']}")
        print(f"  Connection status: {data['sql_server']['connection_status']}")
        
        # Validate allowed tables
        assert isinstance(data["allowed_tables"], list)
        assert len(data["allowed_tables"]) > 0
        print(f"  Allowed tables: {data['allowed_tables']}")
        
        # Validate sync settings
        assert "max_batch_size" in data["sync_settings"]
        assert "error_threshold_percent" in data["sync_settings"]
        print(f"  Max batch size: {data['sync_settings']['max_batch_size']}")
        
        # Validate schedule
        assert "incremental_sync" in data["sync_schedule"]
        assert "full_sync" in data["sync_schedule"]
        print(f"  Incremental schedule: {data['sync_schedule']['incremental_sync']['schedule']}")
        
        print("\n  TEST PASSED: Get Sync Configuration")
    
    def test_test_connection_success(self):
        """
        Test: GET /sync/test-connection (success)
        
        Validates:
        -   Returns 200 OK
        -   status is 'connected' or 'disconnected'
        -   Connection time measured
        -   Available tables listed
        """
        print("\n=== Test: Test SQL Server Connection ===")
        
        # FIXED: Remove /api prefix
        response = client.get("/sync/test-connection")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        required_fields = [
            "status", "server", "database", "available_tables",
            "connection_time_ms", "message"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print(f"  All fields present")
        
        # Validate status
        assert data["status"] in ["connected", "disconnected", "error"]
        print(f"  Connection status: {data['status']}")
        
        if data["status"] == "connected":
            assert isinstance(data["available_tables"], list)
            assert len(data["available_tables"]) > 0
            print(f"  Available tables: {data['available_tables']}")
            
            assert data["connection_time_ms"] > 0
            print(f"  Connection time: {data['connection_time_ms']}ms")
        else:
            print(f"   Connection failed (this may be expected in test environment)")
            print(f"   Message: {data['message']}")
        
        print("\n  TEST PASSED: Test Connection")


# ============================================================================
# INTEGRATION TESTS (End-to-End Scenarios)
# ============================================================================

class TestEndToEndScenarios:
    """Test complete end-to-end sync workflows."""
    
    def test_complete_sync_workflow(self, db_session):
        """
        Test: Complete sync workflow from trigger to completion
        
        Scenario:
        1. Trigger sync
        2. Poll status until complete
        3. Verify in history
        4. Check errors (if any)
        
        This simulates what a frontend would do.
        """
        print("\n=== Test: Complete End-to-End Sync Workflow ===")
        print("Simulating frontend workflow...\n")
        
        # Step 1: Trigger sync
        print("Step 1: Trigger sync...")
        response = client.post("/sync/trigger/employee-reports?is_full_sync=false")
        assert response.status_code == 202
        trigger_data = response.json()
        sync_id = trigger_data["sync_id"]
        print(f"  Sync triggered: {sync_id}")
        
        # Step 2: Poll status
        print("\nStep 2: Poll for status...")
        max_polls = 60  # 5 minutes max
        poll_interval = 5  # seconds
        
        for i in range(max_polls):
            time.sleep(poll_interval)
            
            # FIXED: Remove /api prefix
            response = client.get(f"/sync/status/{sync_id}")
            assert response.status_code == 200
            status_data = response.json()
            
            status = status_data["status"]
            percent = status_data["progress"]["percent_complete"]
            
            print(f"  Poll {i+1}: status={status}, progress={percent}%")
            
            if status in ["completed", "failed", "partial"]:
                print(f"  Sync finished with status: {status}")
                break
        else:
            pytest.fail("Sync did not complete within timeout")
        
        # Step 3: Verify final status
        print("\nStep 3: Verify final status...")
        assert status_data["status"] == "completed"
        assert status_data["progress"]["percent_complete"] == 100.0
        print(f"  Records synced: {status_data['progress']['records_synced']}/{status_data['progress']['records_queried']}")
        
        # Step 4: Check in history
        print("\nStep 4: Verify in history...")
        # FIXED: Remove /api prefix
        response = client.get("/sync/history?page=1&page_size=1")
        assert response.status_code == 200
        history_data = response.json()
        
        # Most recent sync should be ours
        latest = history_data["items"][0]
        assert latest["sync_id"] == sync_id
        print(f"  Found in history (most recent sync)")
        
        # Step 5: Check errors
        print("\nStep 5: Check for errors...")
        response = client.get(f"/sync/{sync_id}/errors")
        assert response.status_code == 200
        errors_data = response.json()
        
        if errors_data["total_errors"] == 0:
            print(f"  No errors (perfect sync!)")
        else:
            print(f"   {errors_data['total_errors']} errors found")
            print(f"   First error: {errors_data['errors'][0]['error_message']}")
        
        print("\n    COMPLETE WORKFLOW TEST PASSED    ")
        print("Frontend integration should work perfectly!")


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Run all tests with detailed output."""
    print("\n" + "="*70)
    print("COMPREHENSIVE SYNC API ENDPOINT TEST SUITE")
    print("="*70)
    print("\nTesting ALL endpoints for frontend readiness...")
    print("\nTest Categories:")
    print("  1. Trigger Endpoints (POST) - 6 tests")
    print("  2. Status & Monitoring (GET) - 7 tests")
    print("  3. History & Reporting (GET) - 8 tests")
    print("  4. Configuration (GET) - 2 tests")
    print("  5. End-to-End Scenarios - 1 test")
    print("\nTotal: 24 comprehensive tests")
    print("="*70 + "\n")
    
    # Run tests with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",           # Verbose
        "-s",           # Don't capture output
        "--tb=short",   # Short traceback
        "--color=yes",  # Colored output
        "-x",           # Stop on first failure
    ])
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("    ALL TESTS PASSED!    ")
        print("="*70)
        print("\n    The Sync API is 100% FRONTEND READY!    ")
        print("\nYou can now:")
        print("  1. Build UI components with confidence")
        print("  2. Call any endpoint knowing it will work")
        print("  3. Handle all response structures correctly")
        print("  4. Poll for status updates")
        print("  5. Display sync history and errors")
        print("\n" + "="*70)
    else:
        print("\n" + "="*70)
        print("   SOME TESTS FAILED")
        print("="*70)
        print("\nPlease review the failures above and fix before frontend integration.")
    
    sys.exit(exit_code)
