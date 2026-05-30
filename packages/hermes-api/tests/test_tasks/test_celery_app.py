"""Tests for Celery app queue configuration."""

from app.tasks.celery_app import celery_app


def test_worker_consumes_routed_queues_by_default():
    queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert "hermes.default" in queue_names
    assert "hermes.downloads" in queue_names
    assert "hermes.cleanup" in queue_names


def test_download_and_cleanup_tasks_route_to_dedicated_queues():
    task_routes = celery_app.conf.task_routes

    assert task_routes["app.tasks.download_tasks.*"]["queue"] == "hermes.downloads"
    assert task_routes["app.tasks.cleanup_tasks.*"]["queue"] == "hermes.cleanup"
