"""
Database base configuration and session management.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

SQLITE_BUSY_TIMEOUT_SECONDS = 5


def create_database_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Configure the supported async backends, including in-memory SQLite."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (
        None,
        "",
        ":memory:",
    ):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        # File connections must not survive a request/task or cross worker loops.
        return create_async_engine(
            url,
            echo=echo,
            poolclass=NullPool,
            connect_args={"timeout": float(SQLITE_BUSY_TIMEOUT_SECONDS)},
        )
    if url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:"):
        return create_async_engine(
            url, echo=echo, pool_pre_ping=True, poolclass=StaticPool
        )
    return create_async_engine(
        url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine = create_database_engine(settings.database_url, echo=settings.database_echo)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


@asynccontextmanager
async def get_db() -> AsyncIterator[AsyncSession]:
    """Close the session, including unfinished transactions, before returning."""
    async with async_session_maker() as session:
        yield session


async def create_tables() -> None:
    """Create all database tables."""
    # Register models even when this helper runs before application startup.
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Drop all database tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
