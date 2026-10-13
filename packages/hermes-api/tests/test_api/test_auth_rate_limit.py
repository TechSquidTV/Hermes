"""Authentication uses shared Redis budgets and verified proxy identities."""

from unittest.mock import AsyncMock

import pytest
from fastapi import Request
from redis.exceptions import ConnectionError

from app.core.config import settings
from app.core.rate_limit import auth_client_ip
from app.main import app


def request(peer, forwarded):
    return Request(
        {
            "type": "http",
            "client": (peer, 1234),
            "headers": [(b"x-forwarded-for", forwarded.encode())],
        }
    )


async def test_untrusted_forwarded_headers_are_ignored(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hosts", ["10.0.0.2"])
    assert await auth_client_ip(request("203.0.113.5", "1.2.3.4")) == "203.0.113.5"


async def test_trusted_proxy_chain_uses_nearest_untrusted_client(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hosts", ["10.0.0.2", "10.0.0.3"])
    assert (
        await auth_client_ip(request("10.0.0.2", "1.2.3.4, 203.0.113.5, 10.0.0.3"))
        == "203.0.113.5"
    )
    assert await auth_client_ip(request("10.0.0.2", "invalid-ip")) == "10.0.0.2"


@pytest.mark.parametrize(
    "path,body",
    [
        ("login", {"username": "wrong", "password": "wrong"}),
        (
            "signup",
            {
                "username": "new",
                "email": "new@example.com",
                "password": "strongpass123",
            },
        ),
        ("refresh", {"refreshToken": "invalid"}),
    ],
)
async def test_every_auth_entrypoint_enforces_redis_budget(
    client, monkeypatch, path, body
):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "enable_rate_limiting", True)
    redis = AsyncMock()
    redis.eval.return_value = [settings.max_login_attempts + 1, 120]
    monkeypatch.setattr(
        "app.core.rate_limit.redis_progress_service.get_async_redis",
        AsyncMock(return_value=redis),
    )
    response = await client.post(f"/api/v1/auth/{path}", json=body)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "120"
    call = redis.eval.await_args.args
    assert call[1] == 1
    assert call[2].startswith(f"hermes:rate-limit:/api/v1/auth/{path}:")
    assert call[3] == str(settings.login_attempt_window_minutes * 60)


async def test_disabled_limiter_never_contacts_redis(client, monkeypatch):
    redis = AsyncMock()
    monkeypatch.setattr(settings, "enable_rate_limiting", False)
    monkeypatch.setattr(
        "app.core.rate_limit.redis_progress_service.get_async_redis", redis
    )
    assert (
        await client.post(
            "/api/v1/auth/login", json={"username": "wrong", "password": "wrong"}
        )
    ).status_code == 401
    redis.assert_not_called()


async def test_redis_failure_does_not_disable_auth_limits(client, monkeypatch):
    monkeypatch.setattr(settings, "enable_rate_limiting", True)
    monkeypatch.setattr(
        "app.core.rate_limit.redis_progress_service.get_async_redis",
        AsyncMock(side_effect=ConnectionError("redis://sensitive.internal")),
    )
    response = await client.post(
        "/api/v1/auth/login", json={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 503
    assert "sensitive.internal" not in response.text


async def test_login_budget_rejects_sixth_attempt_and_ignores_spoofed_ips(
    client, monkeypatch
):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "enable_rate_limiting", True)
    redis = AsyncMock()
    redis.eval.side_effect = [[attempt, 900] for attempt in range(1, 7)]
    monkeypatch.setattr(
        "app.core.rate_limit.redis_progress_service.get_async_redis",
        AsyncMock(return_value=redis),
    )
    statuses = []
    for attempt in range(6):
        response = await client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": f"203.0.113.{attempt}"},
            json={"username": "wrong", "password": "wrong"},
        )
        statuses.append(response.status_code)
    assert statuses == [401] * 5 + [429]
    assert len({call.args[2] for call in redis.eval.await_args_list}) == 1
