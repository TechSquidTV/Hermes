"""
Tasks package - Celery task registration entry point.

This module serves as the entry point for Celery worker to discover tasks.
"""

# Now import task modules directly to register their decorated tasks
import app.tasks.cleanup_tasks
import app.tasks.download_tasks

# Import the celery_app OBJECT first
from app.tasks.celery_app import celery_app

# Make celery_app available when importing from app.tasks
__all__ = ["celery_app"]
