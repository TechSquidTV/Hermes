"""
Storage management service.

Provides disk usage information and cleanup recommendations.
"""

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from app.core.config import settings
from app.core.logging import get_logger
from app.models.pydantic.storage import CleanupRecommendation, StorageInfo

logger = get_logger(__name__)


class StorageService:
    """Service for storage management and monitoring."""

    @staticmethod
    async def get_storage_info() -> StorageInfo:
        """
        Get comprehensive storage information.

        Returns:
            StorageInfo: Storage usage and cleanup recommendations
        """
        try:
            # Get disk usage for download directory
            download_dir = Path(settings.download_dir)
            temp_dir = Path(settings.temp_dir)

            # Ensure directories exist
            download_dir.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Get disk usage statistics
            stat = shutil.disk_usage(download_dir)

            # Calculate directory sizes
            downloads_size = await StorageService._get_directory_size(download_dir)
            temp_size = await StorageService._get_directory_size(temp_dir)

            # Get cleanup recommendations
            recommendations = await StorageService._get_recommendations(
                download_dir, temp_dir
            )

            return StorageInfo(
                total_space=stat.total,
                used_space=stat.used,
                free_space=stat.free,
                usage_percentage=round((stat.used / stat.total) * 100, 2),
                download_directory=str(download_dir),
                temp_directory=str(temp_dir),
                downloads_size=downloads_size,
                temp_size=temp_size,
                cleanup_recommendations=recommendations,
            )

        except Exception as e:
            logger.error("Failed to get storage info", error=str(e))
            raise

    @staticmethod
    async def _get_directory_size(directory: Path) -> int:
        """Calculate total size of directory."""
        total_size = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(
                "Error calculating directory size",
                directory=str(directory),
                error=str(e),
            )
        return total_size

    @staticmethod
    async def _get_recommendations(
        download_dir: Path, temp_dir: Path
    ) -> List[CleanupRecommendation]:
        """Generate cleanup recommendations."""
        recommendations = []

        # Check for old files (>30 days)
        old_files_info = await StorageService._check_old_files(download_dir, days=30)
        if old_files_info["size"] > 0:
            recommendations.append(
                CleanupRecommendation(
                    type="old_files",
                    description="Files older than 30 days in download directory",
                    potential_savings=old_files_info["size"],
                    file_count=old_files_info["count"],
                )
            )

        # Check for temporary files
        temp_files_info = await StorageService._check_temp_files(temp_dir)
        if temp_files_info["size"] > 0:
            recommendations.append(
                CleanupRecommendation(
                    type="temp_files",
                    description="Temporary download files that can be safely removed",
                    potential_savings=temp_files_info["size"],
                    file_count=temp_files_info["count"],
                )
            )

        # Check for partial downloads
        partial_files_info = await StorageService._check_partial_files(download_dir)
        if partial_files_info["size"] > 0:
            recommendations.append(
                CleanupRecommendation(
                    type="partial_downloads",
                    description="Incomplete or failed download files",
                    potential_savings=partial_files_info["size"],
                    file_count=partial_files_info["count"],
                )
            )

        return recommendations

    @staticmethod
    async def _check_old_files(directory: Path, days: int) -> dict:
        """Check for files older than specified days."""
        total_size = 0
        count = 0
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    mtime = datetime.fromtimestamp(
                        item.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < cutoff_time:
                        total_size += item.stat().st_size
                        count += 1
        except Exception as e:
            logger.warning("Error checking old files", error=str(e))

        return {"size": total_size, "count": count}

    @staticmethod
    async def _check_temp_files(temp_dir: Path) -> dict:
        """Check for temporary files."""
        total_size = 0
        count = 0

        try:
            for item in temp_dir.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    count += 1
        except Exception as e:
            logger.warning("Error checking temp files", error=str(e))

        return {"size": total_size, "count": count}

    @staticmethod
    async def _check_partial_files(directory: Path) -> dict:
        """Check for partial/incomplete download files."""
        total_size = 0
        count = 0

        try:
            # Look for common partial download extensions
            partial_extensions = [
                ".part",
                ".download",
                ".tmp",
                ".crdownload",
                ".partial",
            ]
            for item in directory.rglob("*"):
                if item.is_file() and any(
                    item.suffix == ext for ext in partial_extensions
                ):
                    total_size += item.stat().st_size
                    count += 1
        except Exception as e:
            logger.warning("Error checking partial files", error=str(e))

        return {"size": total_size, "count": count}
