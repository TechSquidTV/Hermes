"""Tests for download history endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DownloadHistory


@pytest.mark.asyncio
async def test_history_statistics_use_all_matching_records_not_current_page(
    client: AsyncClient, db_session: AsyncSession
):
    now = datetime.now(timezone.utc)
    records = [
        DownloadHistory(
            id="history-1",
            download_id="download-1",
            url="https://example.test/one",
            status="completed",
            duration=10,
            file_size=100,
            extractor="youtube",
            started_at=now - timedelta(minutes=3),
            completed_at=now - timedelta(minutes=2),
        ),
        DownloadHistory(
            id="history-2",
            download_id="download-2",
            url="https://example.test/two",
            status="failed",
            duration=20,
            file_size=0,
            extractor="youtube",
            started_at=now - timedelta(minutes=2),
            completed_at=now - timedelta(minutes=1),
        ),
        DownloadHistory(
            id="history-3",
            download_id="download-3",
            url="https://example.test/three",
            status="completed",
            duration=30,
            file_size=300,
            extractor="vimeo",
            started_at=now - timedelta(minutes=1),
            completed_at=now,
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    response = await client.get("/api/v1/history/", params={"limit": 1})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["totalDownloads"] == 3
    assert data["totalItems"] == 3
    assert data["successRate"] == 0.667
    assert data["averageDownloadTime"] == 20
    assert data["totalSize"] == 400
    assert data["popularExtractors"][0] == {
        "extractor": "youtube",
        "count": 2,
        "percentage": 66.67,
    }
