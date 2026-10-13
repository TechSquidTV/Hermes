"""
Health check endpoints.
"""

import time
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import engine
from app.models.pydantic.response import (
    DetailedHealthResponse,
    HealthDependency,
    HealthResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Get API health status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.api_version,
        environment="development" if settings.debug else "production",
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health() -> DetailedHealthResponse:
    """Get detailed health information including dependencies."""
    health_info = DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.api_version,
        environment="development" if settings.debug else "production",
    )

    # Check database connectivity
    try:
        start_time = time.time()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        response_time_ms = round((time.time() - start_time) * 1000, 2)
        health_info.dependencies["database"] = HealthDependency(
            status="healthy",
            response_time_ms=response_time_ms,
            message="Database connection successful",
        )
    except Exception as e:
        logger.error("Dependency health check failed", error=str(e))
        health_info.dependencies["database"] = HealthDependency(
            status="error",
            message="Database connection failed",
        )
        health_info.status = "unhealthy"

    # Check Redis connectivity
    try:
        start_time = time.time()
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()

        response_time_ms = round((time.time() - start_time) * 1000, 2)
        health_info.dependencies["redis"] = HealthDependency(
            status="healthy",
            response_time_ms=response_time_ms,
            message="Redis connection successful",
        )
    except Exception as e:
        logger.error("Dependency health check failed", error=str(e))
        health_info.dependencies["redis"] = HealthDependency(
            status="error",
            message="Redis connection failed",
        )
        health_info.status = "unhealthy"

    return health_info
