"""Detect abandoned downloads independently of the worker's task queue."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from threading import Event

from sqlalchemy import func, update
from sqlalchemy.engine import CursorResult

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import async_session_maker
from app.db.models import Download
from app.db.repositories import terminal_history
from app.services.redis_progress import redis_progress_service
from app.utils.download_progress import build_download_progress_payload

logger = get_logger(__name__)
HEARTBEAT_INTERVAL = 30
ABANDONED_MESSAGE = "Download worker stopped responding; submit this URL again"
ACTIVE_STATES = ("downloading", "processing")


async def touch_download(download_id: str) -> bool:
    async with async_session_maker() as session:
        result = await session.execute(
            update(Download)
            .where(Download.id == download_id, Download.status.in_(ACTIVE_STATES))
            .values(last_heartbeat_at=datetime.now(timezone.utc))
        )
        assert isinstance(result, CursorResult)
        await session.commit()
        return result.rowcount == 1


@asynccontextmanager
async def download_heartbeat(download_id: str) -> AsyncIterator[Event]:
    stopped = Event()

    async def pulse() -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                if not await touch_download(download_id):
                    stopped.set()
                    return
            except Exception:
                logger.exception("Download heartbeat failed", download_id=download_id)

    heartbeat = asyncio.create_task(pulse())
    try:
        yield stopped
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat


async def recover_abandoned_downloads() -> list[str]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=settings.download_stale_after_seconds)
    async with async_session_maker() as session:
        abandoned = list(
            await session.scalars(
                update(Download)
                .where(
                    Download.status.in_(ACTIVE_STATES),
                    func.coalesce(
                        Download.last_heartbeat_at,
                        Download.started_at,
                        Download.created_at,
                    )
                    < cutoff,
                )
                .values(
                    status="failed", completed_at=now, error_message=ABANDONED_MESSAGE
                )
                .returning(Download)
                .execution_options(synchronize_session=False)
            )
        )
        for download in abandoned:
            session.add(terminal_history(download))
        await session.commit()
    ids = [download.id for download in abandoned]
    for download_id in ids:
        try:
            await redis_progress_service.delete_progress(download_id)
            await redis_progress_service.publish_download_progress(
                download_id,
                build_download_progress_payload(
                    status="failed",
                    error_message=ABANDONED_MESSAGE,
                    message=ABANDONED_MESSAGE,
                ),
            )
        except Exception:
            logger.exception(
                "Abandoned download notification failed", download_id=download_id
            )
    return ids


@asynccontextmanager
async def download_monitor() -> AsyncIterator[None]:
    async def monitor() -> None:
        while True:
            try:
                await recover_abandoned_downloads()
            except Exception:
                logger.exception("Abandoned download recovery failed")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    watcher = asyncio.create_task(monitor())
    try:
        yield
    finally:
        watcher.cancel()
        with suppress(asyncio.CancelledError):
            await watcher
