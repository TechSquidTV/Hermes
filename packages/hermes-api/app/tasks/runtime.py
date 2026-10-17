"""Run synchronous Celery entrypoints with a bounded async resource lifetime."""

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from app.db.base import engine

T = TypeVar("T")


def run_async_task(operation: Awaitable[T]) -> T:
    """Close pooled connections on their owning loop before asyncio.run exits.

    Celery executes successive task calls in the same process, each with a new
    event loop. asyncpg connections cannot survive into the next task's loop.
    The API retains its normal pool on its long-lived application loop.
    """

    async def run_and_dispose() -> T:
        try:
            return await operation
        finally:
            await engine.dispose()

    return asyncio.run(run_and_dispose())
