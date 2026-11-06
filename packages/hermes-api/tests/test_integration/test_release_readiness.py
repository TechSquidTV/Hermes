"""Regression contracts for release-blocking authorization and cleanup bugs."""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.cleanup import cleanup_downloads
from app.api.v1.endpoints.users import UserUpdateAdmin, update_user_admin_status
from app.core.config import settings
from app.core.security import (
    AuthPrincipal,
    credential_id,
    hash_api_key,
    validate_sse_token,
)
from app.db.base import async_session_maker
from app.db.models import Download, User
from app.db.repositories import ApiKeyRepository, TokenBlacklistRepository
from app.models.auth import AuthenticatedUser
from app.models.pydantic.cleanup import CleanupRequest
from app.services.event_service import EventService
from app.services.redis_progress import redis_progress_service


def principal(user: User) -> AuthenticatedUser:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar": None,
        "is_admin": True,
        "preferences": None,
        "created_at": None,
        "last_login": None,
        "token_id": "jti",
        "session_id": "sid",
    }


async def test_last_active_admin_cannot_demote_self(
    db_session: AsyncSession, test_admin_user: User, test_user: User
) -> None:
    test_user.is_admin = True
    test_user.is_active = False
    await db_session.commit()
    with pytest.raises(HTTPException, match="last admin"):
        await update_user_admin_status(
            test_admin_user.id,
            UserUpdateAdmin(is_admin=False),
            principal(test_admin_user),
            db_session,
        )
    assert (
        await db_session.scalar(
            select(func.count()).select_from(User).where(User.is_active, User.is_admin)
        )
        == 1
    )


async def test_cleanup_preserves_fresh_active_and_symlink_files(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temporary = tmp_path / "temp"
    temporary.mkdir()
    monkeypatch.setattr(settings, "temp_dir", str(temporary))
    monkeypatch.setattr(settings, "download_dir", str(tmp_path / "downloads"))
    db_session.add(
        Download(id="active", url="https://example.com", status="downloading")
    )
    await db_session.commit()
    for name in ("fresh.part", "active_old.part", "abandoned.part"):
        (temporary / name).write_bytes(b"temporary")
    old = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    for name in ("active_old.part", "abandoned.part"):
        os.utime(temporary / name, (old, old))
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    (temporary / "link").symlink_to(outside)
    preview = await cleanup_downloads(
        CleanupRequest(dry_run=True),
        db_session,
        AuthPrincipal(kind="api_key", subject="test", permissions=["admin"]),
    )
    assert preview.files_previewed == 1
    result = await cleanup_downloads(
        CleanupRequest(),
        db_session,
        AuthPrincipal(kind="api_key", subject="test", permissions=["admin"]),
    )
    assert result.files_deleted == 1
    assert not (temporary / "abandoned.part").exists()
    assert (temporary / "fresh.part").exists()
    assert (temporary / "active_old.part").exists()
    assert outside.exists()


async def test_failed_record_cleanup_obeys_preview_and_limit(
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            Download(id=f"failed-{i}", url="https://example.com", status="failed")
            for i in range(3)
        ]
    )
    await db_session.commit()
    request = CleanupRequest(
        delete_failed_downloads=True,
        delete_temp_files=False,
        max_files_to_delete=2,
        dry_run=True,
    )
    preview = await cleanup_downloads(
        request,
        db_session,
        AuthPrincipal(kind="api_key", subject="test", permissions=["admin"]),
    )
    assert preview.records_previewed == 2
    assert await db_session.scalar(select(func.count()).select_from(Download)) == 3
    request.dry_run = False
    result = await cleanup_downloads(
        request,
        db_session,
        AuthPrincipal(kind="api_key", subject="test", permissions=["admin"]),
    )
    assert result.records_deleted == 2
    assert await db_session.scalar(select(func.count()).select_from(Download)) == 1


async def test_sse_rechecks_account_and_logout(
    db_session: AsyncSession, test_user: User
) -> None:
    data: dict[str, Any] = {
        "scope": "downloads",
        "user_id": test_user.id,
        "credential_kind": "user",
        "credential_id": credential_id(test_user),
        "session_id": "sid",
        "token_id": "jti",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    with patch.object(
        redis_progress_service, "get_sse_token", AsyncMock(return_value=data)
    ):
        await validate_sse_token("sse_test", "downloads")
        test_user.is_active = False
        await db_session.commit()
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")
        test_user.is_active = True
        await db_session.commit()
        await TokenBlacklistRepository(db_session).add_to_blacklist(
            "sid",
            test_user.id,
            datetime.now(timezone.utc) + timedelta(days=1),
            "logout",
        )
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")
        data["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")


async def test_idle_stream_revalidates_and_closes_pubsub() -> None:
    closed = asyncio.Event()

    async def idle(channels: list[str]) -> AsyncGenerator[dict[str, Any], None]:
        try:
            await asyncio.Event().wait()
            yield {}
        finally:
            closed.set()

    authorize = AsyncMock(side_effect=[None, HTTPException(status_code=401)])
    service = EventService()
    with patch.object(redis_progress_service, "subscribe_to_channels", idle):
        stream = service.event_stream(["channel"], authorize=authorize)
        assert (await anext(stream))["event"] == "connected"
        assert (await asyncio.wait_for(anext(stream), 3))["event"] == "error"
        with pytest.raises(StopAsyncIteration):
            await anext(stream)
    assert closed.is_set()
    assert service.active_connections == 0


async def test_concurrent_demotions_preserve_one_active_admin(
    db_session: AsyncSession, test_admin_user: User, test_user: User
) -> None:
    test_user.is_admin = True
    await db_session.commit()
    actors = [principal(test_admin_user), principal(test_user)]

    async def demote(actor: AuthenticatedUser) -> int:
        async with async_session_maker() as session:
            try:
                await update_user_admin_status(
                    actor["id"], UserUpdateAdmin(is_admin=False), actor, session
                )
                return 200
            except HTTPException as error:
                return error.status_code

    assert sorted(await asyncio.gather(*(demote(actor) for actor in actors))) == [
        200,
        400,
    ]
    db_session.expire_all()
    assert (
        await db_session.scalar(
            select(func.count()).select_from(User).where(User.is_active, User.is_admin)
        )
        == 1
    )


async def test_sse_database_key_revocation_and_permission_changes(
    db_session: AsyncSession, test_user: User
) -> None:
    key = await ApiKeyRepository(db_session).create(
        test_user.id, "stream", hash_api_key("key"), ["read"]
    )
    data: dict[str, Any] = {
        "scope": "downloads",
        "user_id": test_user.id,
        "credential_kind": "db_api_key",
        "api_key_id": key.id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    with patch.object(
        redis_progress_service, "get_sse_token", AsyncMock(return_value=data)
    ):
        await validate_sse_token("sse_test", "downloads")
        key.permissions = ["write"]
        await db_session.commit()
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")
        key.permissions = ["read"]
        key.is_active = False
        await db_session.commit()
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")


async def test_sse_configured_key_removal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "api_keys", ["service-key"])
    data: dict[str, Any] = {
        "scope": "downloads",
        "credential_kind": "configured_api_key",
        "credential_subject": f"configured_api_key:{hash_api_key('service-key')[:12]}",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    with patch.object(
        redis_progress_service, "get_sse_token", AsyncMock(return_value=data)
    ):
        await validate_sse_token("sse_test", "downloads")
        monkeypatch.setattr(settings, "api_keys", [])
        with pytest.raises(HTTPException):
            await validate_sse_token("sse_test", "downloads")
