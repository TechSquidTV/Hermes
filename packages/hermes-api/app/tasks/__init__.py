"""
Tasks package - Celery task registration entry point.

This module serves as the entry point for Celery worker to discover tasks.

Import order is important to avoid circular dependencies:
1. Import task modules first (which internally import celery_app to decorate functions)
2. Then import celery_app to make it available to external code
This ensures celery_app is created before task decorators use it.
"""

# Import task modules to register their decorated tasks
# These modules will import celery_app from celery_app.py to use @celery_app.task()
import app.tasks.cleanup_tasks
import app.tasks.download_tasks

# Import celery_app to make it available when importing from app.tasks
from app.tasks.celery_app import celery_app

# Make celery_app available when importing from app.tasks
__all__ = ["celery_app"]
