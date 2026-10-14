"""Tests for Celery app queue configuration."""

from __future__ import annotations

from app.tasks.celery_app import celery_app


def test_worker_consumes_routed_queues_by_default() -> None:
    queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert "hermes.default" in queue_names
    assert "hermes.downloads" in queue_names
    assert "hermes.cleanup" in queue_names


def test_download_and_cleanup_tasks_route_to_dedicated_queues() -> None:
    task_routes = celery_app.conf.task_routes

    assert task_routes["app.tasks.download_tasks.*"]["queue"] == "hermes.downloads"
    assert task_routes["app.tasks.cleanup_tasks.*"]["queue"] == "hermes.cleanup"


def test_periodic_maintenance_keeps_retention_opt_in() -> None:
    from app.core.config import settings

    schedule = celery_app.conf.beat_schedule
    assert (
        schedule["cleanup-temp-files"]["task"]
        == "app.tasks.cleanup_tasks.cleanup_temp_files"
    )
    assert schedule["cleanup-temp-files"]["schedule"] == 1800.0
    assert (
        schedule["cleanup-expired-tokens"]["task"]
        == "app.tasks.cleanup_tasks.cleanup_expired_tokens"
    )
    assert schedule["cleanup-expired-tokens"]["schedule"] == 3600.0
    if settings.download_retention_days is None:
        assert "cleanup-old-downloads" not in schedule
    else:
        assert schedule["cleanup-old-downloads"]["kwargs"] == {
            "days": settings.download_retention_days
        }
