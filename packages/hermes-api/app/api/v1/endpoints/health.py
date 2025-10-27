"""
Health check endpoints.
"""

import time
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.db.base import engine
from app.models.pydantic.response import HealthResponse

router = APIRouter()


@router.get("/")
async def get_health():
    """Get API health status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.api_version,
        environment="development" if settings.debug else "production",
    )


@router.get("/detailed")
async def get_detailed_health():
    """Get detailed health information including dependencies."""
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.api_version,
        "environment": "development" if settings.debug else "production",
        "dependencies": {},
    }

    # Check database connectivity
    try:
        start_time = time.time()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        response_time_ms = round((time.time() - start_time) * 1000, 2)
        health_info["dependencies"]["database"] = {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "message": "Database connection successful",
        }
    except Exception as e:
        health_info["dependencies"]["database"] = {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
        }
        health_info["status"] = "unhealthy"

    # Check Redis connectivity
    try:
        start_time = time.time()
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()

        response_time_ms = round((time.time() - start_time) * 1000, 2)
        health_info["dependencies"]["redis"] = {
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "message": "Redis connection successful",
        }
    except Exception as e:
        health_info["dependencies"]["redis"] = {
            "status": "error",
            "message": f"Redis connection failed: {str(e)}",
        }
        health_info["status"] = "unhealthy"

    return health_info
