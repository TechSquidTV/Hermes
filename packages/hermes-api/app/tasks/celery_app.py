"""
Celery configuration for background task processing.
"""

import os

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "hermes",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.download_tasks", "app.tasks.cleanup_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Queue settings
    task_default_queue="hermes.default",
    task_create_missing_queues=True,
    # Routing
    task_routes={
        "app.tasks.download_tasks.*": {"queue": "hermes.downloads"},
        "app.tasks.cleanup_tasks.*": {"queue": "hermes.cleanup"},
    },
    # Retry settings
    task_default_retry_delay=30,
    task_max_retries=3,
    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        "cleanup-old-downloads": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_downloads",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-temp-files": {
            "task": "app.tasks.cleanup_tasks.cleanup_temp_files",
            "schedule": 1800.0,  # Every 30 minutes
        },
    },
)

# Configure Redis connection for Celery
celery_app.conf.broker_url = settings.redis_url
celery_app.conf.result_backend = settings.redis_url

if __name__ == "__main__":
    celery_app.start()
