"""
SSE Token models for ephemeral, scoped authentication.

SSE tokens are short-lived, read-only tokens used for Server-Sent Events
connections. They solve the security issue of passing JWT tokens in query
parameters by providing:

1. Scoped access (e.g., download:abc-123, queue, system)
2. Short TTL (default 5 minutes, max 1 hour)
3. Read-only permissions
4. Easy revocation via Redis TTL
"""

import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SSETokenScope(str, Enum):
    """Available SSE token scopes."""

    DOWNLOAD = "download"  # download:download_id format
    QUEUE = "queue"  # Queue updates (all queue events)
    SYSTEM = "system"  # System notifications


class SSETokenPermission(str, Enum):
    """Permissions for SSE tokens (currently only read)."""

    READ = "read"


class SSETokenData(BaseModel):
    """Data stored in Redis for SSE token validation."""

    token: str = Field(..., description="The SSE token string")
    scope: str = Field(
        ...,
        description="Token scope (e.g., 'download:abc-123', 'queue', 'system')",
    )
    user_id: str = Field(..., description="User ID who owns this token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    permissions: list[SSETokenPermission] = Field(
        default_factory=lambda: [SSETokenPermission.READ],
        description="Token permissions (read-only)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Token creation timestamp",
    )

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """
        Validate scope format.

        Valid formats:
        - download:<download_id>
        - queue
        - system
        """
        if v == "queue" or v == "system":
            return v

        if v.startswith("download:"):
            download_id = v.split(":", 1)[1]
            if not download_id:
                raise ValueError("Download scope must include download_id")
            return v

        raise ValueError(
            f"Invalid scope format: {v}. Must be 'download:<id>', 'queue', or 'system'"
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def matches_scope(self, required_scope: str) -> bool:
        """
        Check if this token's scope matches the required scope.

        Args:
            required_scope: Scope to check (e.g., 'download:abc-123', 'download:*')

        Returns:
            True if scope matches
        """
        # Exact match
        if self.scope == required_scope:
            return True

        # Wildcard match (e.g., download:* matches any download:xxx)
        if required_scope.endswith(":*"):
            scope_prefix = required_scope[:-2]  # Remove :*
            return self.scope.startswith(scope_prefix + ":")

        return False

    def has_permission(self, permission: SSETokenPermission) -> bool:
        """Check if token has specific permission."""
        return permission in self.permissions


class CreateSSETokenRequest(BaseModel):
    """Request to create a new SSE token."""

    scope: str = Field(
        ...,
        description="Token scope (e.g., 'download:abc-123', 'queue', 'system')",
        examples=["download:abc-123", "queue", "system"],
    )
    ttl: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Token TTL in seconds (min 60s, max 3600s/1 hour)",
    )


class SSETokenResponse(BaseModel):
    """Response containing created SSE token."""

    token: str = Field(..., description="The ephemeral SSE token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    scope: str = Field(..., description="Token scope")
    permissions: list[SSETokenPermission] = Field(..., description="Token permissions")
    ttl: int = Field(..., description="Time to live in seconds")


def generate_sse_token(
    scope: str,
    user_id: str,
    ttl: int = 300,
) -> SSETokenData:
    """
    Generate a new SSE token.

    Args:
        scope: Token scope (e.g., 'download:abc-123', 'queue')
        user_id: User ID who owns this token
        ttl: Time to live in seconds (default 5 minutes)

    Returns:
        SSETokenData with generated token
    """
    token = f"sse_{secrets.token_urlsafe(32)}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    return SSETokenData(
        token=token,
        scope=scope,
        user_id=user_id,
        expires_at=expires_at,
        permissions=[SSETokenPermission.READ],
    )
