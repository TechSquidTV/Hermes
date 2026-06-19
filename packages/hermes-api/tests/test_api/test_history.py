"""Tests for download history endpoints."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import history as history_endpoint
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


@pytest.mark.asyncio
async def test_history_statistics_are_zero_without_matching_records(
    client: AsyncClient, db_session: AsyncSession
):
    db_session.add(
        DownloadHistory(
            id="history-other-extractor",
            download_id="download-other-extractor",
            url="https://example.test/other",
            status="completed",
            duration=12,
            file_size=120,
            extractor="youtube",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/v1/history/", params={"extractor": "vimeo", "limit": 1}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["totalDownloads"] == 0
    assert data["totalItems"] == 0
    assert data["successRate"] == 0
    assert data["averageDownloadTime"] == 0
    assert data["totalSize"] == 0
    assert data["popularExtractors"] == []


@pytest.mark.asyncio
async def test_history_endpoint_maps_aggregate_query_results(monkeypatch):
    now = datetime.now(timezone.utc)
    history_record = SimpleNamespace(
        download_id="download-aggregate",
        url="https://example.test/aggregate",
        status="completed",
        started_at=now - timedelta(minutes=1),
        completed_at=now,
        duration=None,
        file_size=25,
        extractor=None,
        error_message=None,
    )

    count_result = SimpleNamespace(scalar=lambda: 1)
    history_result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [history_record])
    )
    stats_result = SimpleNamespace(
        one=lambda: SimpleNamespace(
            total=1,
            successful=1,
            avg_duration=None,
            total_size=25,
        )
    )
    extractor_result = SimpleNamespace(all=lambda: [(None, 1)])
    db_session = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[count_result, history_result, stats_result, extractor_result]
        )
    )
    monkeypatch.setattr(
        history_endpoint, "calculate_daily_stats", AsyncMock(return_value=[])
    )

    history = await history_endpoint.get_download_history(
        start_date=None,
        end_date=None,
        extractor="youtube",
        status="completed",
        limit=1,
        offset=0,
        db_session=db_session,
        principal=SimpleNamespace(),
    )

    assert history.total_downloads == 1
    assert history.total_items == 1
    assert history.success_rate == 1
    assert history.average_download_time == 0
    assert history.total_size == 25
    assert history.items[0].duration == 0
    assert history.items[0].extractor == "unknown"
    assert history.popular_extractors[0].extractor == "unknown"
    assert history.popular_extractors[0].percentage == 100
