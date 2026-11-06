"""Tests for health endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.endpoints import health
from app.models.pydantic.response import DetailedHealthResponse


class TestHealth:
    """Test cases for health endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """Test basic health check endpoint."""
        response = await client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_uses_build_version(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test health check prefers CI-provided build version."""
        monkeypatch.setenv("HERMES_BUILD_VERSION", "v0.4.0")

        response = await client.get("/api/v1/health/")

        assert response.status_code == 200
        assert response.json()["version"] == "v0.4.0"

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient) -> None:
        """Test detailed health check endpoint."""
        response = await client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "response_time_ms" not in data["dependencies"]["database"]
        if "responseTimeMs" in data["dependencies"]["database"]:
            assert isinstance(data["dependencies"]["database"]["responseTimeMs"], float)


@pytest.mark.parametrize(
    "dependencies_ok,schema_ok,expected",
    [(True, True, 200), (False, True, 503), (True, False, 503)],
)
async def test_readiness_checks_dependencies_and_schema(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    dependencies_ok: bool,
    schema_ok: bool,
    expected: int,
) -> None:
    monkeypatch.setattr(
        health,
        "get_detailed_health",
        AsyncMock(
            return_value=DetailedHealthResponse(
                status="healthy" if dependencies_ok else "unhealthy",
                timestamp=datetime.now(timezone.utc),
                version="1.2.3",
                environment="production",
            )
        ),
    )
    monkeypatch.setattr(
        health,
        "check_schema",
        AsyncMock(
            return_value="head",
            side_effect=None if schema_ok else RuntimeError("migration required"),
        ),
    )
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == expected
    assert response.json()["dependencies"]["schema"]["status"] == (
        "healthy" if schema_ok else "error"
    )


async def test_maintenance_blocks_direct_api_writes_but_allows_health(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.core import maintenance

    monkeypatch.setattr(maintenance, "MAINTENANCE_FILE", tmp_path / "maintenance")
    maintenance.set_maintenance(True)
    blocked = await client.post(
        "/api/v1/downloads/", json={"url": "https://example.test/watch"}
    )
    assert blocked.status_code == 503 and blocked.headers["Retry-After"] == "30"
    assert blocked.json()["error"]["code"] == "maintenance"
    assert (await client.get("/api/v1/health/")).status_code == 200
    maintenance.set_maintenance(False)
    assert (await client.get("/api/v1/queue/stats")).status_code != 503
