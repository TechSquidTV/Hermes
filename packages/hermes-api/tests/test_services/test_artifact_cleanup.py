"""Cleanup owns only task-prefixed regular files and respects preview/budgets."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.cleanup import cleanup_downloads
from app.core.config import settings
from app.core.security import AuthPrincipal
from app.db.repositories import DownloadRepository
from app.models.pydantic.cleanup import CleanupRequest
from app.services.file_cleanup import remove_download_artifacts
from app.tasks.cleanup_tasks import (
    _cleanup_old_downloads_async,
    _cleanup_temp_files_async,
)


@pytest.mark.parametrize("shared_roots", [False, True])
async def test_temp_cleanup_reclaims_old_terminal_artifacts_only(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shared_roots: bool,
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    monkeypatch.setattr(
        settings,
        "temp_dir",
        str(tmp_path if shared_roots else tmp_path / "absent-temp"),
    )
    old = (datetime.now(timezone.utc) - timedelta(days=3)).timestamp()
    removable: list[Path] = []
    protected: list[Path] = []
    for status in ("failed", "cancelled", "pending", "downloading", "completed"):
        download = await DownloadRepository(db_session).create(
            "https://example.test/video", status=status
        )
        path = tmp_path / f"{download.id}_video.mp4.part"
        path.write_bytes(b"partial")
        os.utime(path, (old, old))
        (removable if status in {"failed", "cancelled"} else protected).append(path)
        if status == "failed":
            fresh = tmp_path / f"{download.id}_fresh.mp4.part"
            fresh.write_bytes(b"fresh")
            protected.append(fresh)
            outside = tmp_path.parent / f"{download.id}-outside"
            outside.write_bytes(b"outside")
            link = tmp_path / f"{download.id}_escape"
            link.symlink_to(outside)
            protected.extend([outside, link])
    preview = await _cleanup_temp_files_async(dry_run=True)
    assert preview["would_delete_files"] == 2
    assert all(path.exists() for path in removable + protected)
    result = await _cleanup_temp_files_async()
    assert result["deleted_files"] == 2
    assert all(not path.exists() for path in removable)
    assert all(path.exists() for path in protected)


async def test_retention_includes_unregistered_task_outputs(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        "https://example.test/video",
        status="failed",
        completed_at=datetime.now(timezone.utc) - timedelta(days=40),
    )
    download_id = download.id
    path = tmp_path / f"{download_id}_video.mp4.part"
    path.write_bytes(b"partial")
    preview = await _cleanup_old_downloads_async(dry_run=True)
    assert preview["would_delete_files"] == 1 and path.exists()
    result = await _cleanup_old_downloads_async()
    assert result["deleted_files"] == 1 and not path.exists()
    assert await DownloadRepository(db_session).get_by_id(download_id) is None


async def test_manual_failed_cleanup_keeps_record_until_artifacts_fit_budget(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        "https://example.test/video", status="failed"
    )
    path = tmp_path / f"{download.id}_video.mp4.part"
    path.write_bytes(b"partial")
    admin = AuthPrincipal(kind="api_key", subject="test", permissions=["admin"])
    for budget, dry_run in ((1, True), (2, True), (1, False), (1, False)):
        result = await cleanup_downloads(
            CleanupRequest(
                delete_failed_downloads=True,
                delete_temp_files=False,
                max_files_to_delete=budget,
                dry_run=dry_run,
            ),
            db_session,
            admin,
        )
        if dry_run:
            assert result.files_previewed == 1 and path.exists()
            assert result.records_previewed == (1 if budget == 2 else 0)
        elif result.files_deleted:
            assert (
                result.files_deleted == 1
                and result.records_deleted == 0
                and not path.exists()
            )
            assert (
                await DownloadRepository(db_session).get_by_id(download.id) is not None
            )
        else:
            assert result.records_deleted == 1 and not path.exists()


async def test_manual_preview_does_not_count_a_partial_file_twice(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    download = await DownloadRepository(db_session).create(
        "https://example.test/video", status="failed"
    )
    partial = tmp_path / f"{download.id}_video.part"
    partial.write_bytes(b"partial")
    old = (datetime.now(timezone.utc) - timedelta(days=3)).timestamp()
    os.utime(partial, (old, old))
    result = await cleanup_downloads(
        CleanupRequest(
            delete_temp_files=True, delete_failed_downloads=True, dry_run=True
        ),
        db_session,
        AuthPrincipal(kind="api_key", subject="test", permissions=["admin"]),
    )
    assert result.files_previewed == result.records_previewed == 1
    assert result.space_freed == len(b"partial") and partial.exists()


def test_artifact_cleanup_accounts_for_files_removed_before_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "task_first.part", tmp_path / "task_second.part"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    unlink = Path.unlink

    def deny_second(path: Path, missing_ok: bool = False) -> None:
        if path == second:
            raise PermissionError("busy")
        unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", deny_second)
    result = remove_download_artifacts("task", paths=[first, second])
    assert result.files == 1 and result.bytes_freed == 3
    assert result.failed and not result.complete
    assert not first.exists() and second.exists()
