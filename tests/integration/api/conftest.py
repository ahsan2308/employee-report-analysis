"""Fixtures for the HTTP API characterization tests.

Every external side effect is replaced here so no test can reach Redis,
Qdrant, Ollama or SQL Server:

* Celery dispatch is patched where each router/service looks it up and every
  call is recorded, in order, in ``dispatch.calls``.
* ``add_report_to_vector_store`` is patched in ``app.services.report_service``.
* The visualization service's in-process cache is cleared around each test.
"""
from types import SimpleNamespace
from unittest import mock

import pytest

from tests.support.scrub import scrub


class DispatchRecorder:
    """Collects Celery dispatches (``.delay`` / ``send_task``) in call order."""

    def __init__(self):
        self.calls = []

    def _plain(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {key: self._plain(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._plain(val) for val in value]
        return value

    def delay_for(self, name):
        def _delay(*args, **kwargs):
            self.calls.append({"call": f"{name}.delay", "args": self._plain(list(args)), "kwargs": self._plain(kwargs)})
            return SimpleNamespace(id=f"celery-{name}-{len(self.calls)}")

        return _delay

    def send_task(self, name, args=None, kwargs=None, **options):
        self.calls.append({
            "call": "celery_app.send_task",
            "name": name,
            "args": self._plain(list(args or [])),
            "kwargs": self._plain(kwargs or {}),
            "options": self._plain(options),
        })
        return SimpleNamespace(id=f"celery-send-task-{len(self.calls)}")


@pytest.fixture(autouse=True)
def dispatch():
    """Patch every Celery entry point used by the routers and the task service."""
    recorder = DispatchRecorder()
    patches = []
    for target, name in [
        ("app.tasks.dispatch.analyze_report_task", "analyze_report_task"),
        ("app.tasks.dispatch.analyze_monthly_reports_task", "analyze_monthly_reports_task"),
        ("app.tasks.dispatch.analyze_quarterly_reports_task", "analyze_quarterly_reports_task"),
        ("app.tasks.dispatch.process_csv_import", "process_csv_import"),
    ]:
        fake = mock.MagicMock(name=name)
        fake.delay.side_effect = recorder.delay_for(name)
        fake.apply_async.side_effect = AssertionError(f"unexpected {name}.apply_async")
        patches.append(mock.patch(target, fake))

    fake_celery_app = mock.MagicMock(name="celery_app")
    fake_celery_app.send_task.side_effect = recorder.send_task
    patches.append(mock.patch("app.tasks.dispatch.celery_app", fake_celery_app))

    for patcher in patches:
        patcher.start()
    try:
        yield recorder
    finally:
        for patcher in reversed(patches):
            patcher.stop()


@pytest.fixture(autouse=True)
def vector_store():
    """Record add_report_to_vector_store calls made by the reports router."""
    calls = []

    def _record(**kwargs):
        calls.append(kwargs)

    with mock.patch("app.services.report_service.add_report_to_vector_store", side_effect=_record) as patched:
        patched.calls = calls
        yield patched


@pytest.fixture(autouse=True)
def _clear_visualization_cache():
    from app.services import visualization_service

    visualization_service.clear_cache()
    yield
    visualization_service.clear_cache()


@pytest.fixture
def api(clean_db):
    """TestClient over the real app that returns 500s instead of raising them.

    Unhandled exceptions (e.g. response-model validation errors) are part of
    the HTTP contract we are characterizing, so they must surface as responses.
    """
    from fastapi.testclient import TestClient

    from app.api.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _canonical_order(path, body):
    """Sentiment trends and heatmaps have no ORDER BY, so Postgres may return periods
    and cells in any order. Sort them, keeping each label paired with its values."""
    if not isinstance(body, dict):
        return body
    if path.endswith("/sentiment-trends") and isinstance(body.get("labels"), list):
        order = sorted(range(len(body["labels"])), key=lambda i: body["labels"][i])
        body["labels"] = [body["labels"][i] for i in order]
        for dataset in body.get("datasets") or []:
            if isinstance(dataset.get("data"), list) and len(dataset["data"]) == len(order):
                dataset["data"] = [dataset["data"][i] for i in order]
    if path.endswith("-heatmap") and isinstance(body.get("cells"), list):
        body["cells"] = sorted(body["cells"], key=lambda cell: (cell.get("x"), cell.get("y")))
    return body


def body_of(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text
    return _canonical_order(resp.request.url.path, body)


def response_snapshot(resp):
    return {"status": resp.status_code, "body": body_of(resp)}


@pytest.fixture
def snap(snapshot):
    """snap(name, resp, **extra): scrub status/body plus extra state together.

    Scrubbing everything in one pass keeps <uuid:N> numbering consistent
    between the response body, DB rows and captured dispatches.
    """

    def _snap(name, resp, **extra):
        payload = response_snapshot(resp)
        payload.update(extra)
        snapshot(name, scrub(payload))

    return _snap


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Some code paths write debug files (e.g. generated prompts) into the CWD;
    keep them out of the repository."""
    monkeypatch.chdir(tmp_path)
