"""
Timeline analytics endpoint for charts and data visualization.
"""

from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_api_key
from app.db.models import DownloadHistory as DownloadHistoryModel
from app.db.session import get_database_session
from app.models.pydantic.history import DailyStats

router = APIRouter(prefix="/timeline", tags=["timeline"])
logger = get_logger(__name__)


@router.get("/", response_model=list[DailyStats])
async def get_timeline_stats(
    period: str = Query("week", description="Time period (day, week, month, year)"),
    start_date: Optional[date_type] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[date_type] = Query(None, description="End date (YYYY-MM-DD)"),
    extractor: Optional[str] = Query(None, description="Filter by extractor"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
):
    """
    Get timeline data for charts and visualizations.

    Returns daily aggregated statistics for the specified period or date range.
    Perfect for creating charts showing downloads over time.

    Time periods:
    - `day`: Last 24 hours
    - `week`: Last 7 days (default)
    - `month`: Last 30 days
    - `year`: Last 365 days

    Date filters override period selection.
    """
    try:
        # Calculate date range based on period or use provided dates
        if start_date or end_date:
            date_filters = []
            if start_date:
                start_datetime = datetime.combine(
                    start_date, datetime.min.time(), timezone.utc
                )
                date_filters.append(DownloadHistoryModel.completed_at >= start_datetime)
            if end_date:
                end_datetime = datetime.combine(
                    end_date, datetime.max.time(), timezone.utc
                )
                date_filters.append(DownloadHistoryModel.completed_at <= end_datetime)
        else:
            # Use period-based calculation
            now = datetime.now(timezone.utc)
            period_map = {
                "day": timedelta(days=1),
                "week": timedelta(days=7),
                "month": timedelta(days=30),
                "year": timedelta(days=365),
            }
            start_datetime = now - period_map.get(period, timedelta(days=7))
            date_filters = [DownloadHistoryModel.completed_at >= start_datetime]

        # Build additional filters
        filters = date_filters
        if extractor:
            filters.append(DownloadHistoryModel.extractor == extractor)
        if status:
            filters.append(DownloadHistoryModel.status == status)

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

        if len(filters) > 1:
            query = query.where(and_(*filters))
        else:
            query = query.where(filters[0])

        query = query.group_by(func.date(DownloadHistoryModel.completed_at))
        query = query.order_by(func.date(DownloadHistoryModel.completed_at))

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
        logger.error("Failed to get timeline stats", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get timeline stats: {str(e)}"
        )


@router.get("/summary", response_model=dict)
async def get_timeline_summary(
    period: str = Query("week", description="Time period (day, week, month, year)"),
    start_date: Optional[date_type] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[date_type] = Query(None, description="End date (YYYY-MM-DD)"),
    db_session: AsyncSession = Depends(get_database_session),
    api_key: str = Depends(get_current_api_key),
):
    """
    Get summary statistics for the timeline period.

    Returns aggregated metrics including totals, averages, and trends
    for the specified time period.
    """
    try:
        # Get daily stats first
        daily_stats = await get_timeline_stats(
            period=period,
            start_date=start_date,
            end_date=end_date,
            db_session=db_session,
            api_key=api_key,
        )

        if not daily_stats:
            return {
                "total_downloads": 0,
                "success_rate": 0.0,
                "total_size": 0,
                "avg_daily_downloads": 0,
                "trend": "stable",
                "peak_day": None,
                "period": period,
            }

        # Calculate summary statistics
        total_downloads = sum(stat.downloads for stat in daily_stats)
        total_successful = sum(
            int(stat.downloads * stat.success_rate) for stat in daily_stats
        )
        total_size = sum(stat.total_size for stat in daily_stats)

        success_rate = (
            total_successful / total_downloads if total_downloads > 0 else 0.0
        )
        avg_daily_downloads = total_downloads / len(daily_stats) if daily_stats else 0

        # Find peak day (day with most downloads)
        peak_day = max(daily_stats, key=lambda x: x.downloads) if daily_stats else None

        # Calculate trend (simplified - compare first half vs second half)
        if len(daily_stats) >= 4:
            mid_point = len(daily_stats) // 2
            first_half = daily_stats[:mid_point]
            second_half = daily_stats[mid_point:]

            first_half_avg = sum(s.downloads for s in first_half) / len(first_half)
            second_half_avg = sum(s.downloads for s in second_half) / len(second_half)

            if second_half_avg > first_half_avg * 1.2:
                trend = "increasing"
            elif second_half_avg < first_half_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "total_downloads": total_downloads,
            "success_rate": round(success_rate, 3),
            "total_size": total_size,
            "avg_daily_downloads": round(avg_daily_downloads, 2),
            "trend": trend,
            "peak_day": peak_day.date.isoformat() if peak_day else None,
            "peak_downloads": peak_day.downloads if peak_day else 0,
            "period": period,
            "days_count": len(daily_stats),
        }

    except Exception as e:
        logger.error("Failed to get timeline summary", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get timeline summary: {str(e)}"
        )
