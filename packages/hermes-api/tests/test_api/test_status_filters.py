"""Status filters have the same contract on SQLite and PostgreSQL."""

from datetime import datetime, timezone
from typing import get_args

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DownloadHistory
from app.db.repositories import DownloadRepository
from app.models.status import DownloadState, HistoryStatus


@pytest.mark.parametrize(
    ("endpoint", "valid_statuses"),
    [
        ("/api/v1/queue/", get_args(DownloadState)),
        ("/api/v1/history/", get_args(HistoryStatus)),
        ("/api/v1/timeline/", get_args(HistoryStatus)),
    ],
)
async def test_status_filters_validate_values(
    client: AsyncClient, endpoint: str, valid_statuses: tuple[str, ...]
) -> None:
    for status in valid_statuses:
        response = await client.get(endpoint, params={"status": status})
        assert response.status_code == 200, (status, response.text)

    for status in ("invalid", "", "COMPLETED"):
        response = await client.get(endpoint, params={"status": status})
        assert response.status_code == 422, (status, response.text)


async def test_status_filters_select_matching_records(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    repository = DownloadRepository(db_session)
    for status in ("completed", "failed"):
        await repository.create(url=f"https://example.test/{status}", status=status)
        db_session.add(
            DownloadHistory(
                id=status,
                download_id=status,
                url=f"https://example.test/{status}",
                status=status,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        )
    await db_session.commit()

    queue = await client.get("/api/v1/queue/", params={"status": "failed"})
    assert queue.status_code == 200
    assert [item["status"] for item in queue.json()["items"]] == ["failed"]

    history = await client.get("/api/v1/history/", params={"status": "failed"})
    assert history.status_code == 200
    assert [item["status"] for item in history.json()["items"]] == ["failed"]

    timeline = await client.get("/api/v1/timeline/", params={"status": "failed"})
    assert timeline.status_code == 200
    assert timeline.json()[0]["downloads"] == 1
    assert timeline.json()[0]["successRate"] == 0
