"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    cleanup,
    config,
    downloads,
    events,
    files,
    formats,
    health,
    history,
    info,
    queue,
    stats,
    storage,
    timeline,
)

# Create the main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    info.router,
    prefix="/info",
    tags=["information"],
)

api_router.include_router(
    downloads.router,
    prefix="/download",
    tags=["downloads"],
)

api_router.include_router(
    files.router,
    prefix="/files",
    tags=["files"],
)

api_router.include_router(
    queue.router,
    prefix="/queue",
    tags=["queue"],
)

api_router.include_router(
    formats.router,
    prefix="/formats",
    tags=["formats"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"],
)

# New endpoints
api_router.include_router(
    history.router,
    tags=["history"],
)

api_router.include_router(
    storage.router,
    tags=["storage"],
)

api_router.include_router(
    stats.router,
    tags=["statistics"],
)

api_router.include_router(
    timeline.router,
    tags=["timeline"],
)

api_router.include_router(
    cleanup.router,
    tags=["cleanup"],
)

api_router.include_router(
    config.router,
    tags=["configuration"],
)

api_router.include_router(
    events.router,
    prefix="/events",
    tags=["events"],
)
