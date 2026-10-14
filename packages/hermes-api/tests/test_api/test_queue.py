"""Queue pagination, global filters and download snapshot regression tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories import DownloadRepository


@pytest.mark.asyncio
async def test_queue_pages_cover_all_statuses_without_duplicates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    repo = DownloadRepository(db_session)
    statuses = [
        "pending",
        "downloading",
        "processing",
        "completed",
        "failed",
        "cancelled",
    ]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(47):
        download = await repo.create(
            url=f"https://example.test/{index}",
            title=f"Video {index:02}",
            status=statuses[index % len(statuses)],
            output_path="/missing.mp4" if index % 6 == 3 else None,
        )
        download.created_at = start + timedelta(seconds=index)
        await db_session.commit()
    seen: list[str] = []
    for offset in (0, 20, 40):
        response = await client.get("/api/v1/queue/", params={"offset": offset})
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 47
        seen.extend(item["downloadId"] for item in data["items"])
    assert len(seen) == len(set(seen)) == 47
    active = (
        await client.get("/api/v1/queue/", params={"view_mode": "active", "limit": 100})
    ).json()
    assert active["totalItems"] == 39
    assert {item["status"] for item in active["items"]} == set(statuses) - {"completed"}
    history = (
        await client.get("/api/v1/queue/", params={"view_mode": "history"})
    ).json()
    assert history["totalItems"] == 8
    assert all(item["status"] == "completed" for item in history["items"])


@pytest.mark.asyncio
async def test_queue_search_sort_and_filter_apply_before_pagination(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    repo = DownloadRepository(db_session)
    for index in range(30):
        await repo.create(
            url=f"https://example.test/{index}",
            title=f"Match {index:02}",
            status="failed",
            file_size=index,
        )
    await repo.create(
        url="https://example.test/other", title="Other", status="completed"
    )
    response = await client.get(
        "/api/v1/queue/",
        params={
            "status": "failed",
            "search": "Match",
            "sort_by": "title",
            "sort_order": "asc",
            "offset": 20,
            "limit": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["totalItems"] == 30
    assert [item["result"]["title"] for item in data["items"]] == [
        f"Match {index}" for index in range(20, 25)
    ]
    assert data["completed"] == 1  # Summary counts describe the full library.
    empty = await client.get("/api/v1/queue/", params={"search": "%"})
    assert empty.json()["totalItems"] == 0  # SQL wildcards are literal search text.


@pytest.mark.asyncio
async def test_queue_and_status_expose_nested_relative_paths_and_byte_progress(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        url="https://example.test/video",
        title="Nested",
        status="processing",
        output_path=str(tmp_path / "nested/video.mp4"),
        progress=75,
        downloaded_bytes=750,
        total_bytes=1000,
        download_speed=100,
        eta=3,
    )
    for endpoint in ("/api/v1/queue/", f"/api/v1/download/{download.id}"):
        response = await client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        item = data["items"][0] if "items" in data else data
        assert item["currentFilename"] == "nested/video.mp4"
        assert item["progress"]["downloadedBytes"] == 750
        assert item["progress"]["totalBytes"] == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"offset": -1},
        {"limit": 0},
        {"limit": 101},
        {"sort_by": "invalid"},
        {"view_mode": "invalid"},
    ],
)
async def test_queue_rejects_invalid_pagination_and_sort(
    client: AsyncClient, params: dict[str, str | int]
) -> None:
    assert (await client.get("/api/v1/queue/", params=params)).status_code == 422
