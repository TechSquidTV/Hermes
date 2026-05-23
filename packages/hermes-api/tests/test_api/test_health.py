"""Tests for health endpoints."""

import pytest
from httpx import AsyncClient


class TestHealth:
    """Test cases for health endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
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
    ):
        """Test health check prefers CI-provided build version."""
        monkeypatch.setenv("HERMES_BUILD_VERSION", "v0.4.0")

        response = await client.get("/api/v1/health/")

        assert response.status_code == 200
        assert response.json()["version"] == "v0.4.0"

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient):
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
