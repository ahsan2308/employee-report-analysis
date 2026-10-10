"""Characterization of app/services/sync/sync_tracker.py (+ the stale-sync sweep in sync_routes)."""
import math
from datetime import datetime, timedelta

import pytest

from app.models.sync_models import SyncHistory, SyncStatus, SyncType
from app.services.sync.sync_tracker import SyncTracker
from tests.integration.services.seed import dump_rows, fmt_dt, make_sync, normalize, uid

T0 = datetime(2025, 3, 1, 10, 0, 0)


def _rows(database):
    rows = dump_rows(database, SyncHistory, order_by=[SyncHistory.sync_id])
    # Keep seeded fixed datetimes readable; scrub only the ones the code generated.
    for row in rows:
        for key in ("started_at", "completed_at", "last_sync_timestamp"):
            value = row[key]
            if value is not None and value.year == 2025:
                row[key] = fmt_dt(value)
    return rows


@pytest.fixture
def tracker(database):
    return SyncTracker(database)


def test_create_sync_job(tracker, db_session, database, snapshot):
    full = tracker.create_sync_job(SyncType.VISION_DATA, db_session, is_full_sync=True)
    incremental = tracker.create_sync_job(SyncType.EMPLOYEE_REPORTS, session=db_session)
    snapshot("sync_create_job", normalize({
        "returned_types": [type(full).__name__, full.status, incremental.status],
        "to_dict": [full.to_dict(), incremental.to_dict()],
        "row_count": len(dump_rows(database, SyncHistory)),
    }))


def test_get_last_successful_sync(tracker, db_session, snapshot):
    s = db_session
    rt = SyncType.EMPLOYEE_REPORTS.value
    make_sync(s, 1, rt, "completed", T0, T0 + timedelta(days=1))
    make_sync(s, 2, rt, "partial", T0, T0 + timedelta(days=3))
    make_sync(s, 3, rt, "failed", T0, T0 + timedelta(days=9))
    make_sync(s, 4, rt, "running", T0, T0 + timedelta(days=8))
    make_sync(s, 5, rt, "completed", T0 + timedelta(days=20), None)   # newest but no timestamp
    make_sync(s, 6, SyncType.VISION_DATA.value, "completed", T0, T0 + timedelta(days=30))
    s.commit()
    out = {t.value: fmt_dt(tracker.get_last_successful_sync(t, s)) for t in SyncType}
    snapshot("sync_last_successful", out)


def test_update_sync_status_transitions(tracker, db_session, database, snapshot):
    s = db_session
    rt = SyncType.EMPLOYEE_REPORTS.value
    make_sync(s, 1, rt, "pending", T0, records_synced=3)
    make_sync(s, 2, rt, "running", T0)
    make_sync(s, 3, rt, "running", T0)
    make_sync(s, 4, rt, "running", T0, T0)
    make_sync(s, 5, rt, "running", T0)
    s.commit()
    stages = {}

    # RUNNING never moves started_at (it is always set at insert time).
    tracker.update_sync_status(uid(1), SyncStatus.RUNNING, s)
    stages["uncommitted_view"] = _rows(database)[0]["status"]
    s.commit()
    stages["after_running"] = _rows(database)[0]

    tracker.update_sync_status(uid(2), SyncStatus.COMPLETED, s, metrics={
        "records_queried": 10, "records_synced": 8, "records_created": 5, "records_updated": 3,
        "records_skipped": 2, "error_count": 0,
        "last_sync_timestamp": T0 + timedelta(hours=5),
        "metrics": {"employees_created": 1},
    })
    # FAILED: metrics applied but last_sync_timestamp ignored.
    tracker.update_sync_status(uid(3), SyncStatus.FAILED, s, metrics={
        "records_synced": 1, "last_sync_timestamp": T0 + timedelta(hours=6)})
    # PARTIAL with falsy timestamp and explicit None metric.
    tracker.update_sync_status(uid(4), SyncStatus.PARTIAL, s, metrics={
        "last_sync_timestamp": None, "records_synced": None, "error_count": 4})
    # Empty metrics dict is falsy -> no metric changes.
    tracker.update_sync_status(uid(5), SyncStatus.COMPLETED, s, metrics={})
    # Unknown id is a no-op.
    tracker.update_sync_status(uid(99), SyncStatus.COMPLETED, s)
    s.commit()
    stages["final"] = _rows(database)
    snapshot("sync_update_status", normalize(stages))


def test_mark_sync_failed_and_save_errors(tracker, db_session, database, snapshot):
    s = db_session
    make_sync(s, 1, SyncType.VISION_DATA.value, "running", T0)
    make_sync(s, 2, SyncType.VISION_DATA.value, "running", T0, error_count=7)
    s.commit()
    tracker.mark_sync_failed(uid(1), "connection lost", s)
    tracker.mark_sync_failed(uid(99), "ignored", s)
    errors = [
        {"row_number": 1, "field_name": "x", "error_message": "bad", "row_data": {"a": float("nan"), "b": 1.5}},
        {"row_number": 2, "error_message": "inf", "row_data": {"nested": [float("inf"), {"c": -math.inf}]}},
        {"row_number": 3, "error_message": "dt", "row_data": {"when": datetime(2025, 1, 1)}},  # not JSON-able
        {"error_message": "no row number", "row_data": {"s": {1, 2}}},
        {"row_number": 5},
    ]
    tracker.save_sync_errors(uid(2), errors, s)
    tracker.save_sync_errors(uid(99), errors, s)
    s.commit()
    snapshot("sync_failed_and_errors", normalize({
        "rows": _rows(database),
        "empty_errors": tracker._sanitize_errors_for_json([]),
    }))


def test_check_and_clear_stale_syncs(db_session, database, snapshot):
    from app.api.sync_routes import _check_and_clear_stale_syncs

    s = db_session
    now = datetime.now()
    rt, vt = SyncType.EMPLOYEE_REPORTS.value, SyncType.VISION_DATA.value
    make_sync(s, 1, rt, "running", now - timedelta(minutes=61))
    make_sync(s, 2, rt, "pending", now - timedelta(minutes=120))
    make_sync(s, 3, rt, "running", now - timedelta(minutes=59))
    make_sync(s, 4, rt, "completed", now - timedelta(minutes=300))
    make_sync(s, 5, rt, "partial", now - timedelta(minutes=300))
    make_sync(s, 6, vt, "running", now - timedelta(minutes=300))
    s.commit()
    _check_and_clear_stale_syncs(s, rt, timeout_minutes=60)
    after_60 = [(r["sync_id"], r["status"], r["error_message"], r["completed_at"] is not None)
                for r in dump_rows(database, SyncHistory)]
    _check_and_clear_stale_syncs(s, vt, timeout_minutes=5)
    _check_and_clear_stale_syncs(s, rt, timeout_minutes=0)
    final = [(r["sync_id"], r["status"], r["error_message"], r["completed_at"] is not None)
             for r in dump_rows(database, SyncHistory)]
    snapshot("sync_stale_sweep", normalize({"after_60": after_60, "final": final}))
