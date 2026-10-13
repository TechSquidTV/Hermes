"""Security regressions using real API authentication and database transactions."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.db.base import async_session_maker
from app.db.models import User
from app.db.repositories import ApiKeyRepository, DownloadRepository
from app.main import app
from app.tasks import download_tasks


async def test_refresh_tokens_cannot_authenticate_and_access_tokens_cannot_refresh(
    client, test_user
):
    app.dependency_overrides.clear()
    data = {"sub": test_user.username, "user_id": test_user.id}
    refresh = create_refresh_token(data)
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401
    response = await client.post(
        "/api/v1/auth/refresh", json={"refreshToken": create_access_token(data)}
    )
    assert response.status_code == 401


async def test_rotation_is_single_use_and_logout_revokes_the_whole_session(
    client, test_user
):
    app.dependency_overrides.clear()
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "testpass123"},
    )
    assert login.status_code == 200
    original = login.json()
    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refreshToken": original["refreshToken"]}
    )
    assert refresh.status_code == 200
    rotated = refresh.json()
    assert (
        verify_token(rotated["refreshToken"])["sid"]
        == verify_token(original["accessToken"])["sid"]
    )
    replay = await client.post(
        "/api/v1/auth/refresh", json={"refreshToken": original["refreshToken"]}
    )
    assert replay.status_code == 401
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {original['accessToken']}"},
    )
    assert logout.status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refreshToken": rotated["refreshToken"]}
        )
    ).status_code == 401
    for token in (original["accessToken"], rotated["accessToken"]):
        assert (
            await client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
        ).status_code == 401


async def test_concurrent_refresh_has_only_one_successor(client, test_user):
    app.dependency_overrides.clear()
    refresh = create_refresh_token({"sub": test_user.username, "user_id": test_user.id})
    responses = await asyncio.gather(
        *(
            client.post("/api/v1/auth/refresh", json={"refreshToken": refresh})
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 401]


@pytest.mark.parametrize(
    "delta,expected", [(timedelta(days=1), 200), (timedelta(days=-1), 401)]
)
async def test_api_key_expiry_survives_sqlite_roundtrip(
    client, test_user, auth_token, db_session, delta, expected
):
    app.dependency_overrides.clear()
    created = await client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "expiring",
            "permissions": ["read"],
            "expiresAt": (datetime.now(timezone.utc) + delta).isoformat(),
        },
    )
    assert created.status_code == 200
    key = created.json()
    stored = await ApiKeyRepository(db_session).get_by_id(key["id"])
    assert stored.expires_at.tzinfo is None
    response = await client.get(
        "/api/v1/queue/", headers={"Authorization": f"Bearer {key['key']}"}
    )
    assert response.status_code == expected


async def test_info_requires_authentication_before_extraction(client, monkeypatch):
    app.dependency_overrides.clear()
    extract = AsyncMock()
    monkeypatch.setattr("app.api.v1.endpoints.info.yt_service.extract_info", extract)
    response = await client.get(
        "/api/v1/info/", params={"url": "https://example.test/watch"}
    )
    assert response.status_code in {401, 403}
    extract.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "file:///etc/passwd",
        "https://user:secret@example.test/",
    ],
)
async def test_unsafe_urls_never_queue_or_extract(client, monkeypatch, url):
    enqueue = Mock()
    extract = AsyncMock()
    monkeypatch.setattr(
        "app.api.v1.endpoints.downloads.download_video_task.apply_async", enqueue
    )
    monkeypatch.setattr("app.api.v1.endpoints.info.yt_service.extract_info", extract)
    for path, body in [
        ("/api/v1/download/", {"url": url}),
        ("/api/v1/download/batch", {"urls": ["https://example.test/valid", url]}),
    ]:
        assert (await client.post(path, json=body)).status_code == 422
    assert (await client.get("/api/v1/info/", params={"url": url})).status_code == 422
    enqueue.assert_not_called()
    extract.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("outputDirectory", "/etc"),
        ("cookieFile", "/etc/passwd"),
        ("browserCookies", {"browser": "firefox", "profile": "/home/service"}),
    ],
)
async def test_local_path_inputs_cannot_reach_workers(
    client, monkeypatch, field, value
):
    enqueue = Mock()
    monkeypatch.setattr(
        "app.api.v1.endpoints.downloads.download_video_task.apply_async", enqueue
    )
    response = await client.post(
        "/api/v1/download/", json={"url": "https://example.test/watch", field: value}
    )
    assert response.status_code == 422
    enqueue.assert_not_called()


async def test_output_directory_symlink_escape_is_rejected(
    client, tmp_path, monkeypatch
):
    outside = tmp_path / "outside"
    root = tmp_path / "downloads"
    outside.mkdir()
    root.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(settings, "download_dir", str(root))
    assert (
        await client.post(
            "/api/v1/download/",
            json={
                "url": "https://example.test/watch",
                "outputDirectory": str(root / "escape"),
            },
        )
    ).status_code == 422


@pytest.mark.parametrize("password", ["", "short", "a" * 73, "é" * 37])
async def test_signup_password_policy(client, password):
    response = await client.post(
        "/api/v1/auth/signup",
        json={"username": "new", "email": "new@example.com", "password": password},
    )
    assert response.status_code == 422


async def test_profile_is_validated_and_bounded(client, auth_token):
    app.dependency_overrides.clear()
    for changes in [
        {"email": "invalid"},
        {"email": None},
        {"isAdmin": True},
        {"avatar": "x" * 65537},
        {"preferences": {"oversized": "x" * 16384}},
    ]:
        assert (
            await client.patch(
                "/api/v1/auth/profile",
                headers={"Authorization": f"Bearer {auth_token}"},
                json=changes,
            )
        ).status_code == 422


async def test_destructive_endpoints_require_admin_users(client, auth_token):
    app.dependency_overrides.clear()
    for method, path, body in [
        ("POST", "/api/v1/cleanup/", {}),
        ("DELETE", "/api/v1/files/", {"filePaths": ["video.mp4"], "confirm": True}),
    ]:
        response = await client.request(
            method, path, headers={"Authorization": f"Bearer {auth_token}"}, json=body
        )
        assert response.status_code == 403


async def test_first_user_decision_is_serialized(client, monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "allow_public_signup", False)
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/v1/auth/signup",
                json={
                    "username": f"first{i}",
                    "email": f"first{i}@example.com",
                    "password": "strongpass123",
                },
            )
            for i in range(2)
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 403]
    async with async_session_maker() as session:
        users = (await session.scalars(select(User))).all()
        assert len(users) == 1 and users[0].is_admin


async def test_cancelled_download_cannot_register_output_or_publish_completion(
    db_session, tmp_path, monkeypatch
):
    repo = DownloadRepository(db_session)
    download = await repo.create(url="https://example.test/watch", status="downloading")
    download_id = download.id
    await repo.update_status(download_id, "cancelled")
    output = tmp_path / "finished.mp4"
    output.write_bytes(b"media")
    progress = AsyncMock()
    monkeypatch.setattr(download_tasks, "redis_progress_service", progress)
    assert not await download_tasks._update_download_status(
        download_id, "completed", output_path=str(output)
    )
    async with async_session_maker() as session:
        stored = await DownloadRepository(session).get_by_id(download_id)
        assert stored.status == "cancelled" and not stored.files
    progress.publish_download_progress.assert_not_called()


async def test_cancelled_task_redelivery_does_not_download(db_session, monkeypatch):
    download = await DownloadRepository(db_session).create(
        url="https://example.test/watch", status="cancelled"
    )
    service = AsyncMock()
    monkeypatch.setattr(download_tasks, "yt_service", service)
    result = await download_tasks._download_video_task(download.id, download.url)
    assert not result["success"]
    service.extract_info.assert_not_called()
    service.download_video.assert_not_called()


def test_secure_configuration_defaults_and_cors_validation():
    config = Settings(secret_key="test", _env_file=None)
    assert config.allow_public_signup is False
    assert config.access_token_expire_minutes == 15
    assert config.refresh_token_expire_days == 7
    assert config.download_retention_days is None
    with pytest.raises(ValidationError):
        Settings(secret_key="test", allowed_origins=["*"], allow_credentials=True)
    assert Settings(secret_key="test", allowed_origins=["*"], allow_credentials=False)


async def test_api_key_expiration_with_offset_is_stored_as_utc(
    client, auth_token, db_session
):
    app.dependency_overrides.clear()
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    supplied = expiration.astimezone(timezone(timedelta(hours=-7)))
    created = await client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "offset",
            "permissions": ["read"],
            "expiresAt": supplied.isoformat(),
        },
    )
    assert created.status_code == 200
    key = created.json()
    stored = await ApiKeyRepository(db_session).get_by_id(key["id"])
    assert stored.expires_at == expiration.replace(tzinfo=None)
    assert datetime.fromisoformat(key["expiresAt"]) == expiration
    assert (
        await client.get(
            "/api/v1/queue/", headers={"Authorization": f"Bearer {key['key']}"}
        )
    ).status_code == 200
