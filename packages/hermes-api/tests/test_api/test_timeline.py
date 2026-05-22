"""Tests for timeline analytics endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DownloadHistory


class TestTimeline:
    """Test cases for timeline endpoints."""

    @pytest.mark.asyncio
    async def test_timeline_stats_uses_camelcase_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Timeline stats should serialize DailyStats with API camelCase aliases."""
        completed_at = datetime.now(timezone.utc)
        db_session.add(
            DownloadHistory(
                id=str(uuid.uuid4()),
                download_id=str(uuid.uuid4()),
                url="https://example.com/video",
                status="completed",
                duration=10.0,
                file_size=2048,
                extractor="youtube",
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
            )
        )
        await db_session.commit()

        response = await client.get("/api/v1/timeline/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["successRate"] == 1.0
        assert data[0]["totalSize"] == 2048
        assert "success_rate" not in data[0]
        assert "total_size" not in data[0]

    @pytest.mark.asyncio
    async def test_timeline_summary_uses_camelcase_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Timeline summary should expose the typed camelCase API contract."""
        completed_at = datetime.now(timezone.utc)
        db_session.add(
            DownloadHistory(
                id=str(uuid.uuid4()),
                download_id=str(uuid.uuid4()),
                url="https://example.com/video",
                status="completed",
                duration=10.0,
                file_size=4096,
                extractor="youtube",
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
            )
        )
        await db_session.commit()

        response = await client.get("/api/v1/timeline/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["totalDownloads"] == 1
        assert data["successRate"] == 1.0
        assert data["totalSize"] == 4096
        assert data["avgDailyDownloads"] == 1.0
        assert data["peakDownloads"] == 1
        assert data["daysCount"] == 1
        assert "total_downloads" not in data
        assert "success_rate" not in data
        assert "avg_daily_downloads" not in data
