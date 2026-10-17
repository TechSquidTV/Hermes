"""Owner entitlements through real ASGI endpoints without auth overrides."""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.models import User
from app.db.repositories import ApiKeyRepository
from app.main import app


@pytest_asyncio.fixture
async def real_client() -> AsyncIterator[AsyncClient]:
    assert not app.dependency_overrides
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def login(client: AsyncClient, username: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def mint(
    client: AsyncClient, headers: dict[str, str], permissions: list[str]
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/api-keys",
        headers=headers,
        json={"name": "entitlements", "permissions": permissions},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['key']}"}


async def test_admin_grants_follow_current_owner_role(
    real_client: AsyncClient,
    test_user: User,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    user = await login(real_client, test_user.username, "testpass123")
    admin = await login(real_client, test_admin_user.username, "adminpass123")
    endpoint = "/api/v1/cleanup/tokens?dry_run=true"
    assert (await real_client.post(endpoint, headers=user)).status_code == 403
    rejected = await real_client.post(
        "/api/v1/auth/api-keys",
        headers=user,
        json={"name": "escalation", "permissions": ["admin"]},
    )
    assert rejected.status_code == 403
    assert (await real_client.get("/api/v1/auth/api-keys", headers=user)).json() == []
    await ApiKeyRepository(db_session).create(
        user_id=test_user.id,
        name="legacy",
        key_hash=hash_api_key("legacy-key"),
        permissions=["admin", "read"],
    )
    legacy = {"Authorization": "Bearer legacy-key"}
    assert (await real_client.post(endpoint, headers=legacy)).status_code == 403
    assert (
        await real_client.get("/api/v1/history/", headers=legacy)
    ).status_code == 200
    key = await mint(real_client, admin, ["admin", "read"])
    assert (await real_client.post(endpoint, headers=key)).status_code == 200
    assert (await real_client.post(endpoint, headers=admin)).status_code == 200
    assert (
        await real_client.patch(
            f"/api/v1/users/{test_user.id}/admin", headers=admin, json={"isAdmin": True}
        )
    ).status_code == 200
    demoted = await real_client.patch(
        f"/api/v1/users/{test_admin_user.id}/admin",
        headers=user,
        json={"isAdmin": False},
    )
    assert demoted.status_code == 200, demoted.text
    assert (await real_client.post(endpoint, headers=key)).status_code == 403
    assert (await real_client.post(endpoint, headers=admin)).status_code == 403
    assert (await real_client.get("/api/v1/history/", headers=key)).status_code == 200


@pytest.mark.parametrize("permissions", [["read"], ["write"], ["download"], ["admin"]])
async def test_disable_and_reenable_owner(
    real_client: AsyncClient,
    test_user: User,
    test_admin_user: User,
    permissions: list[str],
) -> None:
    user = await login(real_client, test_user.username, "testpass123")
    admin = await login(real_client, test_admin_user.username, "adminpass123")
    if permissions == ["admin"]:
        assert (
            await real_client.patch(
                f"/api/v1/users/{test_user.id}/admin",
                headers=admin,
                json={"isAdmin": True},
            )
        ).status_code == 200
    key = await mint(real_client, user, permissions)
    if permissions == ["write"]:
        method, endpoint, active_status = "POST", "/api/v1/download/missing/cancel", 404
    elif permissions == ["download"]:
        method, endpoint, active_status = (
            "GET",
            "/api/v1/files/download?path=missing",
            404,
        )
    elif permissions == ["admin"]:
        method, endpoint, active_status = (
            "POST",
            "/api/v1/cleanup/tokens?dry_run=true",
            200,
        )
    else:
        method, endpoint, active_status = "GET", "/api/v1/history/", 200
    assert (
        await real_client.request(method, endpoint, headers=key)
    ).status_code == active_status
    for enabled in (False, True):
        result = await real_client.patch(
            f"/api/v1/users/{test_user.id}/active",
            headers=admin,
            json={"isActive": enabled},
        )
        assert result.status_code == 200, result.text
        for credential in (user, key):
            assert (
                await real_client.request(method, endpoint, headers=credential)
            ).status_code == (active_status if enabled else 401)


@pytest.mark.parametrize("state", ["expired", "revoked", "missing_owner"])
async def test_invalid_key_states(
    real_client: AsyncClient, test_user: User, db_session: AsyncSession, state: str
) -> None:
    key = await ApiKeyRepository(db_session).create(
        user_id=test_user.id,
        name=state,
        key_hash=hash_api_key("invalid-key"),
        permissions=["read"],
        expires_at=(
            datetime.now(timezone.utc) - timedelta(days=1)
            if state == "expired"
            else None
        ),
    )
    if state == "revoked":
        key.is_active = False
    elif state == "missing_owner":
        await db_session.delete(test_user)
    await db_session.commit()
    assert (
        await real_client.get(
            "/api/v1/history/", headers={"Authorization": "Bearer invalid-key"}
        )
    ).status_code == 401


async def test_configured_service_key_is_owner_independent(
    real_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "api_keys", ["service-key"])
    headers = {"Authorization": "Bearer service-key"}
    assert (
        await real_client.get("/api/v1/history/", headers=headers)
    ).status_code == 200
    assert (
        await real_client.post("/api/v1/cleanup/tokens?dry_run=true", headers=headers)
    ).status_code == 200
    assert (
        await real_client.post(
            "/api/v1/auth/api-keys",
            headers=headers,
            json={"name": "no-owner", "permissions": ["admin"]},
        )
    ).status_code == 401
