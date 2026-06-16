"""
Download history endpoint.

Provides historical download information and statistics.
"""

from datetime import date as date_type
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import ApiKeyPermission, AuthPrincipal, require_api_permission
from app.db.models import DownloadHistory as DownloadHistoryModel
from app.db.session import get_database_session
from app.models.pydantic.history import (
    DailyStats,
    DownloadHistory,
    HistoryItem,
    PopularExtractor,
)

router = APIRouter(prefix="/history", tags=["history"])
logger = get_logger(__name__)


async def calculate_daily_stats(
    filters: list,
    db_session: AsyncSession,
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None,
) -> list:
    """
    Calculate daily statistics for downloads within the given filters and date range.
    """
    try:
        # Build date filter
        date_filters = []
        if start_date:
            start_datetime = datetime.combine(
                start_date, datetime.min.time(), timezone.utc
            )
            date_filters.append(DownloadHistoryModel.completed_at >= start_datetime)
        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time(), timezone.utc)
            date_filters.append(DownloadHistoryModel.completed_at <= end_datetime)

        # Combine all filters
        all_filters = filters + date_filters if filters else date_filters

        # Get daily aggregated data
        query = select(
            func.date(DownloadHistoryModel.completed_at).label("date"),
            func.count().label("downloads"),
            func.sum(
                func.cast(DownloadHistoryModel.status == "completed", type_=Integer)
            ).label("successful"),
            func.sum(DownloadHistoryModel.file_size).label("total_size"),
            func.avg(DownloadHistoryModel.duration).label("avg_duration"),
        ).select_from(DownloadHistoryModel)

        if all_filters:
            query = query.where(and_(*all_filters))

        query = query.group_by(func.date(DownloadHistoryModel.completed_at))
        query = query.order_by(func.date(DownloadHistoryModel.completed_at).desc())

        result = await db_session.execute(query)
        daily_records = result.all()

        # Convert to DailyStats objects
        daily_stats = []
        for record in daily_records:
            successful = record.successful or 0
            total = record.downloads or 0
            success_rate = successful / total if total > 0 else 0.0

            daily_stats.append(
                DailyStats(
                    date=record.date,
                    downloads=total,
                    success_rate=round(success_rate, 3),
                    total_size=record.total_size or 0,
                )
            )

        return daily_stats

    except Exception as e:
        logger.error("Failed to calculate daily stats", error=str(e))
        return []


@router.get("/", response_model=DownloadHistory)
async def get_download_history(
    start_date: Optional[date_type] = Query(
        None, description="Start date for history query"
    ),
    end_date: Optional[date_type] = Query(
        None, description="End date for history query"
    ),
    extractor: Optional[str] = Query(
        None, description="Filter by extractor (youtube, vimeo, etc.)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by status (completed, failed, cancelled)"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of items to return"
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db_session: AsyncSession = Depends(get_database_session),
    principal: AuthPrincipal = Depends(require_api_permission(ApiKeyPermission.READ)),
):
    """
    Get download history with statistics.

    Returns comprehensive download history including:
    - Individual download records with pagination
    - Overall statistics (success rate, average time, total size)
    - Daily breakdown of downloads
    - Popular extractors analysis

    Filters:
    - `start_date`: Only include downloads after this date
    - `end_date`: Only include downloads before this date
    - `extractor`: Filter by specific extractor (e.g., youtube, vimeo)
    - `status`: Filter by final status (completed, failed, cancelled)

    Returns paginated results with comprehensive statistics.
    """
    try:
        # Build query filters
        filters = []
        if start_date:
            filters.append(
                DownloadHistoryModel.started_at
                >= datetime.combine(start_date, datetime.min.time())
            )
        if end_date:
            filters.append(
                DownloadHistoryModel.completed_at
                <= datetime.combine(end_date, datetime.max.time())
            )
        if extractor:
            filters.append(DownloadHistoryModel.extractor == extractor)
        if status:
            filters.append(DownloadHistoryModel.status == status)

        # Get total count
        count_query = select(func.count()).select_from(DownloadHistoryModel)
        if filters:
            count_query = count_query.where(and_(*filters))
        result = await db_session.execute(count_query)
        total_count = result.scalar() or 0

        # Get history items
        query = select(DownloadHistoryModel)
        if filters:
            query = query.where(and_(*filters))
        query = (
            query.order_by(DownloadHistoryModel.completed_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db_session.execute(query)
        history_records = result.scalars().all()

        # Convert to response items
        items = [
            HistoryItem(
                download_id=record.download_id,
                url=record.url,
                status=record.status,
                started_at=record.started_at,
                completed_at=record.completed_at,
                duration=record.duration or 0,
                file_size=record.file_size,
                extractor=record.extractor or "unknown",
                title=None,  # Not stored in history table
                error_message=record.error_message,
            )
            for record in history_records
        ]

        # Calculate statistics for all matching records, not just current page.
        stats_query = select(
            func.count().label("total"),
            func.avg(DownloadHistoryModel.duration).label("avg_duration"),
            func.sum(DownloadHistoryModel.file_size).label("total_size"),
            func.sum(
                func.cast(DownloadHistoryModel.status == "completed", type_=Integer)
            ).label("successful"),
        ).select_from(DownloadHistoryModel)
        if filters:
            stats_query = stats_query.where(and_(*filters))

        stats_result = await db_session.execute(stats_query)
        stats = stats_result.one()

        total_downloads = stats.total or 0
        successful_downloads = stats.successful or 0
        success_rate = (
            successful_downloads / total_downloads if total_downloads > 0 else 0.0
        )
        avg_time = stats.avg_duration or 0.0
        total_size = stats.total_size or 0

        # Get popular extractors for all matching records.
        extractor_query = select(
            DownloadHistoryModel.extractor,
            func.count().label("count"),
        ).select_from(DownloadHistoryModel)
        if filters:
            extractor_query = extractor_query.where(and_(*filters))
        extractor_query = (
            extractor_query.group_by(DownloadHistoryModel.extractor)
            .order_by(func.count().desc())
            .limit(5)
        )

        extractor_result = await db_session.execute(extractor_query)
        popular_extractors = []
        for extractor, count in extractor_result.all():
            popular_extractors.append(
                PopularExtractor(
                    extractor=extractor or "unknown",
                    count=count,
                    percentage=(
                        round((count / total_downloads) * 100, 2)
                        if total_downloads
                        else 0
                    ),
                )
            )

        # Calculate daily stats
        daily_stats = await calculate_daily_stats(
            filters, db_session, start_date, end_date
        )

        return DownloadHistory(
            total_downloads=total_downloads,
            success_rate=round(success_rate, 3),
            average_download_time=round(avg_time, 2),
            total_size=total_size,
            popular_extractors=popular_extractors,
            daily_stats=daily_stats,
            items=items,
            total_items=total_count,
            page=(offset // limit) + 1,
            per_page=limit,
        )

    except Exception as e:
        logger.error("Failed to get download history", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
