"""Tests for standard API error response wrappers."""

import pytest
from httpx import AsyncClient


class TestErrorResponses:
    """Test cases for consistent HTTP error response bodies."""

    @pytest.mark.asyncio
    async def test_http_exception_uses_standard_error_wrapper(
        self, client: AsyncClient
    ):
        """HTTPException responses should use the documented ErrorResponse shape."""
        response = await client.get("/api/v1/download/missing-download-id")

        assert response.status_code == 404
        data = response.json()
        assert data == {
            "error": {
                "code": "http_404",
                "message": "Download not found",
                "details": None,
            }
        }
