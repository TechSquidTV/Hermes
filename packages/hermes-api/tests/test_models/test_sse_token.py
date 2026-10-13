"""
Tests for SSE token models and validation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.sse_token import (
    CreateSSETokenRequest,
    SSETokenData,
    SSETokenPermission,
    generate_sse_token,
)


class TestSSETokenData:
    """Test SSE token data model."""

    def test_valid_download_scope(self) -> None:
        """Test valid download scope format."""
        token = SSETokenData(
            token="sse_test123",
            scope="download:abc-123",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.scope == "download:abc-123"
        assert token.user_id == "user123"
        assert token.permissions == [SSETokenPermission.READ]

    def test_valid_queue_scope(self) -> None:
        """Test valid queue scope."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.scope == "queue"

    def test_valid_system_scope(self) -> None:
        """Test valid system scope."""
        token = SSETokenData(
            token="sse_test123",
            scope="system",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.scope == "system"

    def test_invalid_scope_empty_download_id(self) -> None:
        """Test invalid scope with empty download ID."""
        with pytest.raises(ValidationError) as exc_info:
            SSETokenData(
                token="sse_test123",
                scope="download:",  # Empty download ID
                user_id="user123",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        assert "Download scope must include download_id" in str(exc_info.value)

    def test_invalid_scope_format(self) -> None:
        """Test invalid scope format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SSETokenData(
                token="sse_test123",
                scope="invalid:format:here",
                user_id="user123",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        assert "Invalid scope format" in str(exc_info.value)

    def test_invalid_scope_unknown(self) -> None:
        """Test unknown scope format."""
        with pytest.raises(ValidationError) as exc_info:
            SSETokenData(
                token="sse_test123",
                scope="unknown_scope",
                user_id="user123",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        assert "Invalid scope format" in str(exc_info.value)

    def test_is_expired_returns_false_for_valid_token(self) -> None:
        """Test is_expired returns False for non-expired token."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.is_expired() is False

    def test_is_expired_returns_true_for_expired_token(self) -> None:
        """Test is_expired returns True for expired token."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),  # Past
        )
        assert token.is_expired() is True

    def test_matches_scope_exact_match(self) -> None:
        """Test exact scope matching."""
        token = SSETokenData(
            token="sse_test123",
            scope="download:abc-123",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.matches_scope("download:abc-123") is True
        assert token.matches_scope("download:different") is False

    def test_matches_scope_wildcard(self) -> None:
        """Test wildcard scope matching."""
        token = SSETokenData(
            token="sse_test123",
            scope="download:abc-123",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.matches_scope("download:*") is True
        assert token.matches_scope("queue:*") is False

    def test_matches_scope_queue(self) -> None:
        """Test queue scope matching."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.matches_scope("queue") is True
        assert token.matches_scope("download:*") is False

    def test_has_permission_read(self) -> None:
        """Test has_permission for read permission."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.has_permission(SSETokenPermission.READ) is True

    def test_default_permissions_are_read_only(self) -> None:
        """Test that default permissions are read-only."""
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert token.permissions == [SSETokenPermission.READ]

    def test_created_at_is_set_automatically(self) -> None:
        """Test that created_at is set automatically."""
        before = datetime.now(timezone.utc)
        token = SSETokenData(
            token="sse_test123",
            scope="queue",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        after = datetime.now(timezone.utc)
        assert before <= token.created_at <= after


class TestCreateSSETokenRequest:
    """Test CreateSSETokenRequest model."""

    def test_valid_request_with_defaults(self) -> None:
        """Test valid request with default TTL."""
        request = CreateSSETokenRequest(scope="queue")
        assert request.scope == "queue"
        assert request.ttl == 300  # Default 5 minutes

    def test_valid_request_with_custom_ttl(self) -> None:
        """Test valid request with custom TTL."""
        request = CreateSSETokenRequest(scope="download:abc-123", ttl=600)
        assert request.scope == "download:abc-123"
        assert request.ttl == 600

    def test_ttl_minimum_validation(self) -> None:
        """Test TTL minimum value (60s)."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSSETokenRequest(scope="queue", ttl=30)  # Below minimum
        assert "greater than or equal to 60" in str(exc_info.value)

    def test_ttl_maximum_validation(self) -> None:
        """Test TTL maximum value (3600s)."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSSETokenRequest(scope="queue", ttl=7200)  # Above maximum
        assert "less than or equal to 3600" in str(exc_info.value)


class TestGenerateSSEToken:
    """Test token generation function."""

    def test_generate_token_format(self) -> None:
        """Test generated token has correct format."""
        token = generate_sse_token(scope="download:abc-123", user_id="user123", ttl=300)
        assert token.token.startswith("sse_")
        assert len(token.token) > 10  # Should be reasonably long

    def test_generate_token_unique(self) -> None:
        """Test that each generated token is unique."""
        token1 = generate_sse_token(scope="queue", user_id="user123", ttl=300)
        token2 = generate_sse_token(scope="queue", user_id="user123", ttl=300)
        assert token1.token != token2.token

    def test_generate_token_ttl_calculation(self) -> None:
        """Test that expires_at is calculated correctly."""
        before = datetime.now(timezone.utc)
        ttl = 600
        token = generate_sse_token(scope="queue", user_id="user123", ttl=ttl)
        after = datetime.now(timezone.utc)

        expected_min = before + timedelta(seconds=ttl)
        expected_max = after + timedelta(seconds=ttl)

        assert expected_min <= token.expires_at <= expected_max

    def test_generate_token_sets_scope(self) -> None:
        """Test that scope is set correctly."""
        scope = "download:test-123"
        token = generate_sse_token(scope=scope, user_id="user123", ttl=300)
        assert token.scope == scope

    def test_generate_token_sets_user_id(self) -> None:
        """Test that user_id is set correctly."""
        user_id = "user456"
        token = generate_sse_token(scope="queue", user_id=user_id, ttl=300)
        assert token.user_id == user_id

    def test_generate_token_default_permissions(self) -> None:
        """Test that default permissions are read-only."""
        token = generate_sse_token(scope="queue", user_id="user123", ttl=300)
        assert token.permissions == [SSETokenPermission.READ]

    def test_generate_token_with_download_scope(self) -> None:
        """Test token generation with download scope."""
        download_id = "video-download-789"
        token = generate_sse_token(
            scope=f"download:{download_id}", user_id="user123", ttl=600
        )
        assert token.scope == f"download:{download_id}"
        assert token.matches_scope(f"download:{download_id}")

    def test_generate_token_default_ttl(self) -> None:
        """Test token generation with default TTL (5 minutes)."""
        token = generate_sse_token(scope="queue", user_id="user123")
        # Should expire in approximately 300 seconds (5 minutes)
        time_until_expiry = (
            token.expires_at - datetime.now(timezone.utc)
        ).total_seconds()
        assert 295 <= time_until_expiry <= 305  # Allow small time variance
