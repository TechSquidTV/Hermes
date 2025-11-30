"""
System settings service with caching.

Provides cached access to system settings stored in the database,
with fallback to environment variables if database is unavailable.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.db.base import async_session_maker
from app.db.repositories import SystemSettingsRepository

logger = logging.getLogger(__name__)


class SystemSettingsService:
    """
    Service for managing system settings with caching.

    Uses a 10-second cache to balance between freshness and database load.
    Falls back to environment variables if database is unavailable.
    """

    def __init__(self):
        self._cache: Optional[dict] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=10)  # 10-second cache

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_timestamp is None:
            return False
        return datetime.now(timezone.utc) - self._cache_timestamp < self._cache_ttl

    def _invalidate_cache(self):
        """Invalidate the cache."""
        self._cache = None
        self._cache_timestamp = None
        logger.info("[SystemSettingsService] Cache invalidated")

    async def _load_from_db(self) -> Optional[dict]:
        """Load settings from database."""
        try:
            async with async_session_maker() as session:
                repo = SystemSettingsRepository(session)
                settings_obj = await repo.get_settings()

                if settings_obj:
                    return {
                        "allow_public_signup": settings_obj.allow_public_signup,
                        "updated_at": settings_obj.updated_at,
                        "updated_by_user_id": settings_obj.updated_by_user_id,
                    }

                return None
        except Exception as e:
            logger.error(f"[SystemSettingsService] Failed to load from DB: {e}")
            return None

    async def get_allow_public_signup(self) -> bool:
        """
        Get the allow_public_signup setting.

        Returns cached value if available, otherwise loads from database.
        Falls back to environment variable if database is unavailable.
        """
        # Check cache first
        if self._is_cache_valid() and self._cache:
            logger.debug("[SystemSettingsService] Returning cached allow_public_signup")
            return self._cache.get("allow_public_signup", settings.allow_public_signup)

        # Load from database
        db_settings = await self._load_from_db()

        if db_settings:
            # Update cache
            self._cache = db_settings
            self._cache_timestamp = datetime.now(timezone.utc)
            logger.info(
                "[SystemSettingsService] Loaded from DB",
                extra={"allow_public_signup": db_settings["allow_public_signup"]},
            )
            return db_settings["allow_public_signup"]

        # Fallback to environment variable
        logger.warning(
            "[SystemSettingsService] DB unavailable, falling back to env var",
            extra={"fallback_value": settings.allow_public_signup},
        )
        return settings.allow_public_signup

    async def update_allow_public_signup(
        self, value: bool, user_id: Optional[str] = None
    ) -> dict:
        """
        Update the allow_public_signup setting.

        Immediately invalidates cache and updates database.
        """
        try:
            async with async_session_maker() as session:
                repo = SystemSettingsRepository(session)
                settings_obj = await repo.update_allow_public_signup(value, user_id)

                # Invalidate cache immediately
                self._invalidate_cache()

                logger.info(
                    "[SystemSettingsService] Updated allow_public_signup",
                    extra={
                        "value": value,
                        "user_id": user_id,
                        "updated_at": settings_obj.updated_at.isoformat(),
                    },
                )

                return {
                    "allow_public_signup": settings_obj.allow_public_signup,
                    "updated_at": settings_obj.updated_at,
                    "updated_by_user_id": settings_obj.updated_by_user_id,
                }
        except Exception as e:
            logger.error(
                f"[SystemSettingsService] Failed to update setting: {e}",
                exc_info=True,
            )
            raise

    async def get_all_settings(self) -> dict:
        """Get all system settings."""
        # Check cache first
        if self._is_cache_valid() and self._cache:
            logger.debug("[SystemSettingsService] Returning cached settings")
            return self._cache

        # Load from database
        db_settings = await self._load_from_db()

        if db_settings:
            # Update cache
            self._cache = db_settings
            self._cache_timestamp = datetime.now(timezone.utc)
            return db_settings

        # Fallback to environment variables
        return {
            "allow_public_signup": settings.allow_public_signup,
            "updated_at": None,
            "updated_by_user_id": None,
        }


# Global singleton instance
system_settings_service = SystemSettingsService()
