"""
Celery worker entry point.

This module serves as the entry point for the Celery worker command.
It imports the celery app and all task modules to register tasks.
"""

# Import all task modules to register their decorated tasks
import app.tasks.cleanup_tasks  # noqa: F401
import app.tasks.download_tasks  # noqa: F401

# Import celery app first
from app.tasks.celery_app import celery_app

# This is the app that Celery worker will use
app = celery_app

__all__ = ["app", "celery_app"]
