"""Serialize first-user decisions across processes in the database transaction."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_user_registration(session: AsyncSession) -> None:
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        await session.execute(text("BEGIN IMMEDIATE"))
    elif dialect == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(726384102)"))
    else:
        raise RuntimeError("User registration requires SQLite or PostgreSQL")
