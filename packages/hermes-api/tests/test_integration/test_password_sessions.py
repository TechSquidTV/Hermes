"""Password changes invalidate every JWT/SSE session at the database commit."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.endpoints.auth import AuthResponse
from app.core.security import create_access_token, validate_sse_token
from app.db.models import User
from app.main import app
from app.services.redis_progress import redis_progress_service


async def login(client: AsyncClient, password: str = "testpass123") -> AuthResponse:
    response = await client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": password}
    )
    assert response.status_code == 200, response.text
    return AuthResponse.model_validate(response.json())


async def test_password_change_revokes_all_sessions_and_sse(
    client: AsyncClient, test_user: User
) -> None:
    app.dependency_overrides.clear()
    sessions = [await login(client), await login(client)]
    stored = AsyncMock()
    headers = {"Authorization": "Bearer " + sessions[0].access_token}
    with patch.object(redis_progress_service, "store_sse_token", stored):
        minted = await client.post(
            "/api/v1/events/token", headers=headers, json={"scope": "queue"}
        )
    assert minted.status_code == 200, minted.text
    assert stored.await_args is not None
    data = stored.await_args.kwargs["data"]
    assert data["credential_id"]
    with patch.object(
        redis_progress_service, "get_sse_token", AsyncMock(return_value=data)
    ):
        await validate_sse_token("synthetic-sse", "queue")
        changed = await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "currentPassword": "testpass123",
                "newPassword": "NewPasswordForAllDevices123",
            },
        )
        assert changed.status_code == 200, changed.text
        with pytest.raises(HTTPException) as revoked:
            await validate_sse_token("synthetic-sse", "queue")
        assert revoked.value.status_code == 401
    for session in sessions:
        assert (
            await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer " + session.access_token},
            )
        ).status_code == 401
        assert (
            await client.post(
                "/api/v1/auth/refresh", json={"refreshToken": session.refresh_token}
            )
        ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
    ).status_code == 401
    fresh = await login(client, "NewPasswordForAllDevices123")
    assert (
        await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer " + fresh.access_token},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refreshToken": fresh.refresh_token}
        )
    ).status_code == 200


async def test_tokens_without_password_binding_are_rejected(
    client: AsyncClient, test_user: User
) -> None:
    app.dependency_overrides.clear()
    legacy = create_access_token({"sub": test_user.username, "user_id": test_user.id})
    assert (
        await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + legacy}
        )
    ).status_code == 401


async def test_simultaneous_password_changes_have_one_winner(
    client: AsyncClient, test_user: User
) -> None:
    app.dependency_overrides.clear()
    session = await login(client)
    passwords = ["ConcurrentPassword123", "ConcurrentPassword456"]
    responses = await asyncio.gather(
        *[
            client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer " + session.access_token},
                json={"currentPassword": "testpass123", "newPassword": password},
            )
            for password in passwords
        ]
    )
    assert sum(response.status_code == 200 for response in responses) == 1
    assert all(response.status_code in {200, 401, 409} for response in responses)
    winner = next(
        password
        for password, response in zip(passwords, responses, strict=True)
        if response.status_code == 200
    )
    await login(client, winner)
