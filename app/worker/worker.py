"""
Celery worker entry point that ensures all tasks are properly registered.

This file explicitly imports all task modules to ensure they're 
registered with Celery before the worker starts processing messages.
"""
from app.worker.celery_app import celery_app

# Explicitly import all task modules
import app.tasks.import_tasks
import app.tasks.analysis_tasks
import app.tasks.sync_tasks

# This ensures both csv_import.process and any other tasks are properly registered

if __name__ == '__main__':
    celery_app.start()
