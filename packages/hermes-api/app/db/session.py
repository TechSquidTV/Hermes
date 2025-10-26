"""
Database session management and FastAPI dependencies.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db


# FastAPI dependency for database sessions
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions."""
    async for session in get_db():
        yield session


# Type alias for dependency injection
DatabaseSession = Depends(get_database_session)
