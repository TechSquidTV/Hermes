"""
API statistics endpoint.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.db.models import DownloadHistory
from app.db.session import get_database_session
from app.models.pydantic.stats import ApiStatistics, ErrorBreakdown, ExtractorStats

router = APIRouter(prefix="/stats", tags=["statistics"])
logger = get_logger(__name__)


@router.get("/", response_model=ApiStatistics)
async def get_api_statistics(
    period: str = Query(
        "week", description="Time period for statistics (day, week, month, year)"
    ),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
):
    """
    Get API usage statistics.

    Returns comprehensive statistics including:
    - Total downloads and success rates
    - Average download times
    - Bandwidth usage
    - Popular extractors
    - Error breakdown
    - Peak usage hours

    Time periods:
    - `day`: Last 24 hours
    - `week`: Last 7 days (default)
    - `month`: Last 30 days
    - `year`: Last 365 days
    """
    try:
        # Calculate time range
        now = datetime.now(timezone.utc)
        period_map = {
            "day": timedelta(days=1),
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "year": timedelta(days=365),
        }
        start_time = now - period_map.get(period, timedelta(days=7))

        # Get all history records in period
        query = select(DownloadHistory).where(
            DownloadHistory.completed_at >= start_time
        )
        result = await db_session.execute(query)
        records = result.scalars().all()

        total_downloads = len(records)
        successful = sum(1 for r in records if r.status == "completed")
        failed = sum(1 for r in records if r.status == "failed")
        success_rate = successful / total_downloads if total_downloads > 0 else 0.0

        # Calculate average download time
        durations = [r.duration for r in records if r.duration]
        avg_time = sum(durations) / len(durations) if durations else 0.0

        # Calculate total bandwidth
        sizes = [r.file_size for r in records if r.file_size]
        total_bandwidth = sum(sizes)

        # Popular extractors
        extractor_counts = {}
        for record in records:
            ext = record.extractor or "unknown"
            extractor_counts[ext] = extractor_counts.get(ext, 0) + 1

        popular_extractors = [
            ExtractorStats(
                extractor=ext,
                count=count,
                percentage=(
                    round((count / total_downloads) * 100, 2) if total_downloads else 0
                ),
            )
            for ext, count in sorted(
                extractor_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # Error breakdown
        error_types = {}
        failed_records = [r for r in records if r.status == "failed"]
        for record in failed_records:
            # Categorize errors (simplified)
            error_msg = record.error_message or "Unknown error"
            error_type = (
                "network_error"
                if "network" in error_msg.lower()
                else (
                    "format_error"
                    if "format" in error_msg.lower()
                    else (
                        "permission_error"
                        if "permission" in error_msg.lower()
                        else "unknown_error"
                    )
                )
            )
            error_types[error_type] = error_types.get(error_type, 0) + 1

        error_breakdown = [
            ErrorBreakdown(
                error_type=error_type,
                count=count,
                percentage=round((count / failed) * 100, 2) if failed else 0,
            )
            for error_type, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            )
        ]

        # Peak hour (simplified - just return 0 for now)
        peak_hour = 0

        return ApiStatistics(
            period=period,
            total_downloads=total_downloads,
            successful_downloads=successful,
            failed_downloads=failed,
            success_rate=round(success_rate, 3),
            average_download_time=round(avg_time, 2),
            total_bandwidth_used=total_bandwidth,
            popular_extractors=popular_extractors,
            error_breakdown=error_breakdown,
            peak_hour=peak_hour,
            total_storage_used=total_bandwidth,
        )

    except Exception as e:
        logger.error("Failed to get API statistics", error=str(e))
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )
