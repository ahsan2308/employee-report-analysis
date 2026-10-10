"""The Celery contract: task names are what producers and queued messages refer to.

The three analysis tasks have names derived from their module path, so moving
app/tasks/analysis_tasks.py without pinning ``name=`` would orphan queued work
and break the ``app.tasks.analysis_tasks.*`` route.
"""
import inspect
import sys

import pytest


@pytest.fixture(scope="module")
def celery_app():
    import app.worker.worker  # noqa: F401  (worker entry point imports every task module)

    return sys.modules["app.worker.celery_app"].celery_app


def test_registered_tasks(celery_app, snapshot):
    tasks = {}
    for name, task in sorted(celery_app.tasks.items()):
        if name.startswith("celery."):
            continue
        run = task.run
        tasks[name] = {
            "implementation": f"{run.__module__}.{run.__qualname__}",
            "signature": str(inspect.signature(run)),
            "base": next((cls.__name__ for cls in type(task).__mro__[1:] if cls.__module__.startswith("app.")), "Task"),
            "max_retries": task.max_retries,
            "acks_late": task.acks_late,
        }
    snapshot("registered_tasks", tasks)


def test_routing_and_schedule(celery_app, snapshot):
    conf = celery_app.conf
    snapshot("routing_and_schedule", {
        "task_routes": conf.task_routes,
        "beat_schedule": {key: {k: str(v) for k, v in entry.items()} for key, entry in conf.beat_schedule.items()},
        "main": celery_app.main,
    })


def test_route_resolution_per_task(celery_app, snapshot):
    router = celery_app.amqp.router
    snapshot("route_resolution", {
        name: router.route({}, name).get("queue").name if router.route({}, name).get("queue") else None
        for name in sorted(celery_app.tasks) if not name.startswith("celery.")
    })


def test_worker_entry_point_registers_every_task(run_probe, snapshot):
    """`celery -A app.worker.celery_app worker` must register all tasks without app.worker.worker."""
    snapshot("worker_entry_point_tasks", run_probe("worker_tasks", {}))
