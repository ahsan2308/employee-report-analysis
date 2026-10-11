"""Characterization of app/services/task_service.py (real Postgres, Celery dispatch mocked)."""
from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from app.models.db_models import Employee, Report
from app.models.task_models import BackgroundTask
from app.api.serializers import task_result_response
from app.services import task_service
from tests.integration.services.seed import (
    dump_rows,
    make_analysis,
    make_employee,
    make_monthly,
    make_quarterly,
    make_report,
    make_task,
    normalize,
    row_dict,
    uid,
)


@pytest.fixture
def dispatch():
    """Capture Celery .delay calls for the three analysis tasks, keyed by task name."""
    calls = []

    def recorder(name):
        fake = mock.MagicMock(name=name)
        fake.delay.side_effect = lambda *args, **kwargs: calls.append(
            {"task": name, "args": list(args), "kwargs": kwargs})
        return fake

    with mock.patch.object(task_service, "analyze_report_task", recorder("analyze_report_task")), \
         mock.patch("app.tasks.analysis_tasks.analyze_monthly_reports_task",
                    recorder("analyze_monthly_reports_task")), \
         mock.patch("app.tasks.analysis_tasks.analyze_quarterly_reports_task",
                    recorder("analyze_quarterly_reports_task")):
        yield calls


@pytest.fixture(autouse=True)
def clock():
    """Pin the service's clock 30 minutes after the seeded tasks were created, so they are in flight."""
    with mock.patch.object(task_service, "_now", return_value=CLOCK):
        yield


CLOCK = datetime(2025, 1, 1, 9, 30, 0)
STALE = datetime(2025, 1, 1, 7, 0, 0)  # longer ago than any run may take


@pytest.fixture
def seeded(db_session):
    make_employee(db_session, 1, "Alice", "Engineering", "Dev")
    make_employee(db_session, 2, "Bob", "Finance", "Analyst")
    make_report(db_session, 1, 1, date(2025, 1, 6))
    make_report(db_session, 2, 1, date(2025, 1, 13))
    db_session.commit()
    return db_session


def _tasks(database):
    return dump_rows(database, BackgroundTask, order_by=[BackgroundTask.created_at, BackgroundTask.task_id])


def _task_view(task):
    return None if task is None else row_dict(task)


# ------------------------------------------------------------ report analysis

def test_create_task_for_analysis_new_task_dispatches(seeded, database, dispatch, snapshot):
    employee = seeded.get(Employee, 1)
    task = task_service.create_task_for_analysis(seeded, uid(1), employee)
    assert dispatch == [{"task": "analyze_report_task", "args": [str(task.task_id)], "kwargs": {}}]
    snapshot("create_task_for_analysis_new", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_create_task_for_analysis_with_existing_analysis(seeded, database, dispatch, snapshot):
    analysis = make_analysis(seeded, seeded.get(Report, uid(1)))
    seeded.commit()
    employee = seeded.get(Employee, 1)
    task = task_service.create_task_for_analysis(seeded, uid(1), employee, existing_analysis=analysis)
    snapshot("create_task_for_analysis_existing", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_create_task_for_analysis_reuses_active_task_when_analysis_exists(seeded, database, dispatch, snapshot):
    report = seeded.get(Report, uid(1))
    make_analysis(seeded, report)
    make_task(seeded, 50, report_id=uid(1), status="running", task_type="REPORT_ANALYSIS")
    seeded.commit()
    task = task_service.create_task_for_analysis(seeded, uid(1), seeded.get(Employee, 1))
    assert task.task_id == uid(50)
    snapshot("create_task_for_analysis_reuse_active", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_create_task_for_analysis_reuses_in_flight_task(seeded, database, dispatch, snapshot):
    """A queued task is returned instead of creating and dispatching a duplicate (B1 fixed)."""
    make_task(seeded, 51, report_id=uid(1), status="pending", task_type="REPORT_ANALYSIS")
    seeded.commit()
    task = task_service.create_task_for_analysis(seeded, uid(1), seeded.get(Employee, 1))
    assert task.task_id == uid(51)
    assert dispatch == []
    snapshot("create_task_for_analysis_reuse_in_flight", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_create_task_for_analysis_replaces_stale_task(seeded, database, dispatch, snapshot):
    """A task active for longer than any run can take is marked FAILED and a new one is dispatched."""
    make_task(seeded, 52, report_id=uid(1), status="running", task_type="REPORT_ANALYSIS",
              created_at=STALE, started_at=STALE)
    seeded.commit()
    task = task_service.create_task_for_analysis(seeded, uid(1), seeded.get(Employee, 1))
    assert task.task_id != uid(52)
    assert seeded.get(BackgroundTask, uid(52)).status == "failed"
    snapshot("create_task_for_analysis_replace_stale", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_find_active_task_functions(seeded, database, snapshot):
    """In-flight tasks are returned; stale ones are marked FAILED; COMPLETED tasks and other scopes are untouched."""
    s = seeded
    make_task(s, 60, report_id=uid(1), status="pending", task_type="REPORT_ANALYSIS",
              created_at=datetime(2025, 1, 1, 9, 0, 1))
    make_task(s, 61, report_id=uid(2), status="completed", task_type="REPORT_ANALYSIS",
              created_at=datetime(2025, 1, 1, 9, 0, 2))
    make_task(s, 62, employee_id=1, year=2025, month=1, status="running", task_type="MONTHLY_ANALYSIS",
              created_at=datetime(2025, 1, 1, 9, 0, 3))
    make_task(s, 63, employee_id=1, year=2025, month=2, status="pending", task_type="MONTHLY_ANALYSIS",
              created_at=datetime(2025, 1, 1, 9, 0, 4))
    make_task(s, 64, employee_id=1, year=2025, quarter=1, status="pending", task_type="QUARTERLY_ANALYSIS",
              created_at=datetime(2025, 1, 1, 9, 0, 5))
    # month=1 but typed QUARTERLY -> not matched by the monthly finder
    make_task(s, 65, employee_id=1, year=2025, month=1, quarter=2, status="pending",
              task_type="QUARTERLY_ANALYSIS", created_at=datetime(2025, 1, 1, 9, 0, 6))
    # Created long ago, but started recently: still in flight.
    make_task(s, 66, employee_id=2, year=2025, month=1, status="running", task_type="MONTHLY_ANALYSIS",
              created_at=STALE, started_at=datetime(2025, 1, 1, 9, 10, 0))
    make_task(s, 67, employee_id=1, year=2025, month=3, status="running", task_type="MONTHLY_ANALYSIS",
              created_at=STALE, started_at=STALE)
    make_task(s, 68, employee_id=1, year=2025, quarter=4, status="pending", task_type="QUARTERLY_ANALYSIS",
              created_at=STALE)
    make_monthly(s, 1, 2025, 2)
    s.commit()

    results = {
        "report_1_pending": _task_view(task_service.find_active_task_for_report(s, uid(1))),
        "report_2_only_completed": _task_view(task_service.find_active_task_for_report(s, uid(2))),
        "report_unknown": _task_view(task_service.find_active_task_for_report(s, uid(999))),
        "monthly_2025_1_running": _task_view(
            task_service.find_active_task_for_monthly_analysis(s, 1, 2025, 1)),
        "monthly_2025_2_has_analysis": _task_view(
            task_service.find_active_task_for_monthly_analysis(s, 1, 2025, 2)),
        "monthly_2025_3_stale": _task_view(
            task_service.find_active_task_for_monthly_analysis(s, 1, 2025, 3)),
        "monthly_employee_2_started_recently": _task_view(
            task_service.find_active_task_for_monthly_analysis(s, 2, 2025, 1)),
        "quarterly_2025_1_pending": _task_view(
            task_service.find_active_task_for_quarterly_analysis(s, 1, 2025, 1)),
        "quarterly_2025_3_none": _task_view(
            task_service.find_active_task_for_quarterly_analysis(s, 1, 2025, 3)),
        "quarterly_2025_4_stale": _task_view(
            task_service.find_active_task_for_quarterly_analysis(s, 1, 2025, 4)),
    }
    snapshot("find_active_tasks", normalize({"results": results, "rows": _tasks(database)}))


# ------------------------------------------------------------ monthly / quarterly

def test_create_task_for_monthly_analysis(seeded, database, dispatch, snapshot):
    s = seeded
    new = task_service.create_task_for_monthly_analysis(s, 1, 2025, 3)
    existing = task_service.create_task_for_monthly_analysis(
        s, 2, 2025, 3, existing_analysis=SimpleNamespace(analysis_id=42))
    with pytest.raises(ValueError) as exc:
        task_service.create_task_for_monthly_analysis(s, 99, 2025, 3)
    # A second call while the first is PENDING returns it.
    again = task_service.create_task_for_monthly_analysis(s, 1, 2025, 3)
    snapshot("create_task_for_monthly_analysis", normalize({
        "new": _task_view(new),
        "existing": _task_view(existing),
        "unknown_employee_error": str(exc.value),
        "again_reuses_first": again.task_id == new.task_id,
        "dispatch": dispatch,
        "rows": _tasks(database),
    }))


def test_create_task_for_monthly_analysis_reuses_active_when_analysis_exists(seeded, database, dispatch, snapshot):
    make_monthly(seeded, 1, 2025, 4)
    make_task(seeded, 70, employee_id=1, year=2025, month=4, status="running", task_type="MONTHLY_ANALYSIS")
    seeded.commit()
    task = task_service.create_task_for_monthly_analysis(seeded, 1, 2025, 4)
    assert task.task_id == uid(70)
    snapshot("create_task_for_monthly_analysis_reuse", normalize({
        "returned": _task_view(task), "dispatch": dispatch, "rows": _tasks(database)}))


def test_create_task_for_quarterly_analysis(seeded, database, dispatch, snapshot):
    s = seeded
    new = task_service.create_task_for_quarterly_analysis(s, 1, 2025, 1)
    existing = task_service.create_task_for_quarterly_analysis(
        s, 2, 2025, 1, existing_analysis=SimpleNamespace(analysis_id=7))
    with pytest.raises(ValueError) as exc:
        task_service.create_task_for_quarterly_analysis(s, 99, 2025, 1)
    make_quarterly(s, 1, 2025, 1)
    s.commit()
    reused = task_service.create_task_for_quarterly_analysis(s, 1, 2025, 1)
    # Quarter is not validated.
    odd = task_service.create_task_for_quarterly_analysis(s, 2, 2025, 9)
    snapshot("create_task_for_quarterly_analysis", normalize({
        "new": _task_view(new),
        "existing": _task_view(existing),
        "unknown_employee_error": str(exc.value),
        "reused_same_task": reused.task_id == new.task_id,
        "odd_quarter": _task_view(odd),
        "dispatch": dispatch,
        "rows": _tasks(database),
    }))


# ------------------------------------------------------------ status / result

def test_get_task_status(seeded, snapshot):
    make_task(seeded, 80, report_id=uid(1), status="running", task_type="REPORT_ANALYSIS",
              started_at=datetime(2025, 1, 1, 9, 0, 0), completed_at=datetime(2025, 1, 1, 9, 0, 30))
    seeded.commit()
    task = task_service.get_task_status(seeded, uid(80))
    snapshot("get_task_status", normalize({
        "found": _task_view(task),
        "properties": {"duration": task.duration, "is_complete": task.is_complete, "is_active": task.is_active},
        "missing": _task_view(task_service.get_task_status(seeded, uid(81))),
    }))


@pytest.fixture
def result_seed(seeded):
    s = seeded
    report = s.get(Report, uid(1))
    bare = make_analysis(s, report, sentiment_score=0.3, risk_level="medium")
    full = make_analysis(
        s, s.get(Report, uid(2)), sentiment_score=0.8, risk_level="low",
        risk_explanation="r", achievements_json=[{"a": 1}], challenges_json=[{"c": 1}],
        topics=["t"], action_items=["x"], credibility_rating="high", credibility_explanation="ce",
        exaggeration_flags=["e"], consistency_score="high", performance_rating="high",
        performance_summary="ps", performance_strengths=["s"], performance_improvement_areas=["i"])
    make_monthly(s, 1, 2025, 1, significant_risks=None, escalating_risks=["esc"],
                 consistency_notable_strengths=["str"], focus_areas=[{"p": 1}])
    make_quarterly(s, 1, 2025, 1, monthly_analysis_ids=[1], stakeholder_count=2,
                   strategic_alignment_json={"s": 1}, forward_planning_json={"f": 1})

    def t(n, **kw):
        return make_task(s, n, created_at=datetime(2025, 1, 1, 9, 0, n % 60), **kw)

    t(1, report_id=uid(1), status="completed", task_type="REPORT_ANALYSIS",
      result_data={"analysis_id": bare.analysis_id, "report_id": str(uid(1))})
    t(2, report_id=uid(2), status="completed", task_type="REPORT_ANALYSIS",
      result_data={"analysis_id": full.analysis_id})
    t(3, report_id=uid(1), status="completed", task_type="REPORT_ANALYSIS",
      result_data={"analysis_id": bare.analysis_id, "report_id": "x", "extra": 1})  # >2 keys: passthrough
    t(4, report_id=uid(1), status="completed", task_type="REPORT_ANALYSIS",
      result_data={"analysis_id": 9999})  # reference to missing analysis
    t(5, report_id=uid(1), status="completed", task_type="REPORT_ANALYSIS", result_data=None)
    t(6, report_id=uid(1), status="failed", task_type="REPORT_ANALYSIS", error_message="boom",
      result_data={"ignored": True})
    t(7, employee_id=1, year=2025, month=1, status="completed", task_type="MONTHLY_ANALYSIS",
      result_data={"analysis_id": 12345})  # id ignored; looked up by (employee, year, month)
    t(8, employee_id=1, year=2025, month=2, status="completed", task_type="MONTHLY_ANALYSIS",
      result_data={"analysis_id": 1, "cached": "kept because no analysis for month 2"})
    t(9, employee_id=1, year=2025, quarter=1, status="completed", task_type="QUARTERLY_ANALYSIS",
      result_data={"analysis_id": 1})
    t(10, employee_id=1, year=2025, quarter=2, status="completed", task_type="QUARTERLY_ANALYSIS",
      result_data={"analysis_id": 1})
    t(11, employee_id=1, year=2025, month=1, status="completed", task_type="MONTHLY_ANALYSIS",
      result_data={"no_analysis_id": True})
    t(12, status="completed", task_type="SOMETHING_ELSE", result_data={"x": 1})
    t(13, report_id=uid(1), status="pending", task_type="REPORT_ANALYSIS")
    t(14, report_id=uid(1), status="running", task_type="REPORT_ANALYSIS")
    s.commit()
    return s


def test_get_task_result(result_seed, snapshot):
    results = {}
    for n in range(1, 13):
        # Shaped as GET /tasks/{id}/result returns it
        results[f"task_{n}"] = task_result_response(uid(n), task_service.get_task_result(result_seed, uid(n)))
    errors = {}
    for n in (13, 14, 99):
        with pytest.raises(ValueError) as exc:
            task_service.get_task_result(result_seed, uid(n))
        errors[f"task_{n}"] = str(exc.value)
    snapshot("get_task_result", normalize({"results": results, "errors": errors}))
