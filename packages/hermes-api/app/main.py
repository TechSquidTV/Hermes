"""
Main FastAPI application for Hermes API server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
logger = logging.getLogger(__name__)
setup_logging()


async def initialize_admin_user() -> None:
    """
    Initialize admin user from environment variables if configured.

    This function checks if:
    1. No users exist in the database
    2. Initial admin credentials are provided in settings

    If both conditions are met, creates the first admin user.
    """
    # Check if initial admin credentials are configured
    if not all(
        [
            settings.initial_admin_username,
            settings.initial_admin_email,
            settings.initial_admin_password,
        ]
    ):
        logger.info("No initial admin credentials configured, skipping admin creation")
        return

    # Import here to avoid circular imports
    import uuid

    from sqlalchemy import select

    from app.core.security import get_password_hash
    from app.db.base import async_session_maker
    from app.db.models import User

    # Get database session using the session factory directly
    async with async_session_maker() as db:
        try:
            # Check if any users exist
            result = await db.execute(select(User))
            existing_users = result.scalars().all()

            if existing_users:
                logger.info(
                    f"Users already exist ({len(existing_users)}), skipping admin creation"
                )
                return

            # Create admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                username=settings.initial_admin_username,
                email=settings.initial_admin_email,
                password_hash=get_password_hash(settings.initial_admin_password),
                is_active=True,
                is_admin=True,
            )

            db.add(admin_user)
            await db.commit()

            logger.info(
                f"Initial admin user created successfully: {settings.initial_admin_username}",
                extra={
                    "admin_username": settings.initial_admin_username,
                    "admin_email": settings.initial_admin_email,
                    "security_event": "admin_user_created",
                },
            )

        except Exception as e:
            logger.error(f"Failed to create initial admin user: {e}")
            await db.rollback()
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Hermes API server...")
    logger.info(f"Debug mode: {settings.debug}")

    # Create directories if they don't exist
    import os

    os.makedirs(settings.download_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    # Create data directory for SQLite database
    os.makedirs("./data", exist_ok=True)

    # Initialize database tables
    try:
        from app.db.base import create_tables

        logger.info("Creating database tables...")
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

    # Initialize admin user if configured
    try:
        await initialize_admin_user()
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")
        # Don't raise - allow server to start even if admin creation fails

    yield

    # Shutdown
    logger.info("Shutting down Hermes API server...")

    # Close Redis connections
    try:
        from app.services.redis_progress import redis_progress_service

        logger.info("Closing Redis connections...")
        await redis_progress_service.close()
        logger.info("Redis connections closed successfully")
    except Exception as e:
        logger.error(f"Failed to close Redis connections: {e}")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS middleware with enhanced security
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        max_age=86400,  # Cache preflight for 24 hours
    )

    # Global exception handler for consistent error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent error response format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": exc.detail,
                    "details": None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions with consistent error response format."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An internal server error occurred",
                    "details": str(exc) if settings.debug else None,
                }
            },
        )

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Allow Swagger UI to load assets from CDN while keeping other resources restricted
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data: cdn.jsdelivr.net"
        )

        return response

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_application()


@app.get("/health")
async def health():
    """Basic health check endpoint (alias for health-check)."""
    return {"status": "healthy", "version": settings.api_version}


@app.get("/health-check")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "version": settings.api_version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
    )
