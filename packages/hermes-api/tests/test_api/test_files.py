"""Tests for downloaded file management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories import DownloadFileRepository, DownloadRepository


async def _create_managed_file(
    db_session: AsyncSession,
    file_path,
    content: bytes = b"video",
):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)

    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch",
        status="completed",
        output_path=str(file_path),
    )
    await DownloadFileRepository(db_session).create(
        download_id=download.id,
        filename=file_path.name,
        filepath=str(file_path),
        file_size=len(content),
        file_type="video",
    )
    return download


@pytest.mark.asyncio
async def test_download_file_serves_managed_download(
    client: AsyncClient, db_session: AsyncSession, tmp_path, monkeypatch
):
    downloads_dir = tmp_path / "downloads"
    monkeypatch.setattr(settings, "download_dir", str(downloads_dir))
    media_path = downloads_dir / "example.mp4"
    await _create_managed_file(db_session, media_path, b"managed video")

    response = await client.get(
        "/api/v1/files/download", params={"path": str(media_path)}
    )

    assert response.status_code == 200
    assert response.content == b"managed video"
    assert "example.mp4" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_download_file_rejects_untracked_file_inside_download_dir(
    client: AsyncClient, tmp_path, monkeypatch
):
    downloads_dir = tmp_path / "downloads"
    monkeypatch.setattr(settings, "download_dir", str(downloads_dir))
    untracked_file = downloads_dir / "untracked.mp4"
    untracked_file.parent.mkdir(parents=True, exist_ok=True)
    untracked_file.write_bytes(b"not managed")

    response = await client.get(
        "/api/v1/files/download", params={"path": str(untracked_file)}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_files_rejects_path_outside_download_dir(
    client: AsyncClient, tmp_path, monkeypatch
):
    downloads_dir = tmp_path / "downloads"
    monkeypatch.setattr(settings, "download_dir", str(downloads_dir))
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret")

    response = await client.request(
        "DELETE",
        "/api/v1/files/",
        json={"files": [str(outside_file)], "confirm": True},
    )

    assert response.status_code == 200
    assert response.json()["deletedFiles"] == 0
    assert response.json()["failedDeletions"]
    assert outside_file.exists()


@pytest.mark.asyncio
async def test_file_listing_paginates_all_matches_and_reports_full_totals(
    client: AsyncClient, db_session: AsyncSession, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    for index in range(5):
        await _create_managed_file(db_session, tmp_path / f"{index}.mp4", b"video")

    response = await client.get("/api/v1/files/", params={"limit": 1, "offset": 3})

    assert response.status_code == 200
    data = response.json()
    assert data["totalFiles"] == 5
    assert data["totalSize"] == 25
    assert [file["filename"] for file in data["files"]] == ["1.mp4"]


@pytest.mark.asyncio
async def test_file_listing_respects_zero_max_size_and_directory_boundaries(
    client: AsyncClient, db_session: AsyncSession, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    await _create_managed_file(db_session, tmp_path / "videos" / "empty.mp4", b"")
    await _create_managed_file(db_session, tmp_path / "videos" / "full.mp4")
    await _create_managed_file(db_session, tmp_path / "videos-other" / "empty.mp4", b"")

    response = await client.get(
        "/api/v1/files/",
        params={"directory": str(tmp_path / "videos"), "max_size": 0},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["totalFiles"] == 1
    assert data["files"][0]["filepath"] == str(tmp_path / "videos" / "empty.mp4")


@pytest.mark.asyncio
async def test_file_listing_rejects_inverted_size_range(client: AsyncClient):
    response = await client.get(
        "/api/v1/files/", params={"min_size": 10, "max_size": 0}
    )
    assert response.status_code == 422
