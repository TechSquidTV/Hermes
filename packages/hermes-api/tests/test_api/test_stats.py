"""Statistics must distinguish current storage from historical activity."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DownloadHistory


@pytest.mark.parametrize("early_count,expected", [(1, 14), (2, 8)])
async def test_peak_hour_uses_utc_completions_and_deterministic_ties(
    client: AsyncClient, db_session: AsyncSession, early_count: int, expected: int
) -> None:
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    # 16:00 at UTC+02 is 14:00 UTC. An out-of-period peak must not count.
    hours = [(14, 0, 0), (16, 2, 0), *[(8, 0, 0)] * early_count, *[(23, 0, 30)] * 3]
    for hour, offset, age in hours:
        completed = yesterday.replace(
            hour=hour, tzinfo=timezone(timedelta(hours=offset))
        )
        completed -= timedelta(days=age)
        db_session.add(
            DownloadHistory(
                id=str(uuid.uuid4()),
                download_id=str(uuid.uuid4()),
                url="https://example.com/video",
                status="completed",
                started_at=completed,
                completed_at=completed,
            )
        )
    await db_session.commit()
    response = await client.get("/api/v1/stats/?period=week")
    assert response.status_code == 200, response.text
    assert response.json()["peakHour"] == expected
    assert response.json()["totalDownloads"] == 2 + early_count


async def test_storage_tracks_existing_files_without_history(
    client: AsyncClient, tmp_path: Path
) -> None:
    root = Path(settings.download_dir)
    nested = root / "nested"
    nested.mkdir()
    media = nested / "media.mp4"
    media.write_bytes(b"media")
    (root / "subtitle.vtt").write_bytes(b"subtitle")
    outside = tmp_path.parent / f"outside-{uuid.uuid4()}"
    outside.write_bytes(b"outside storage")
    try:
        (root / "external-link").symlink_to(outside)
        response = await client.get("/api/v1/stats/?period=day")
        assert response.status_code == 200, response.text
        assert response.json()["totalBandwidthUsed"] == 0
        assert response.json()["totalStorageUsed"] == 13
        assert response.json()["peakHour"] == 0
        media.unlink()
        response = await client.get("/api/v1/stats/?period=year")
        assert response.json()["totalStorageUsed"] == 8
    finally:
        outside.unlink(missing_ok=True)


async def test_deleted_historical_media_does_not_count_as_current_storage(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    completed = datetime.now(timezone.utc)
    db_session.add(
        DownloadHistory(
            id=str(uuid.uuid4()),
            download_id=str(uuid.uuid4()),
            url="https://example.com/video",
            status="completed",
            file_size=1000000,
            started_at=completed,
            completed_at=completed,
        )
    )
    await db_session.commit()
    response = await client.get("/api/v1/stats/")
    assert response.status_code == 200, response.text
    assert response.json()["totalBandwidthUsed"] == 1000000
    assert response.json()["totalStorageUsed"] == 0
