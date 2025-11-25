"""
Celery task package for employee report analysis system.

This package contains all background tasks that can be executed asynchronously
using Celery workers.
"""
from app.worker.celery_app import celery_app
from app.tasks.analysis_tasks import analyze_report_task, analyze_monthly_reports_task
from app.tasks.sync_tasks import *
from app.tasks import import_tasks

__all__ = ['analysis_tasks', 'import_tasks', 'sync_tasks']