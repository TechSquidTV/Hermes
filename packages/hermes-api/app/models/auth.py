"""Internal authentication contracts shared by dependencies and endpoints."""

from typing import Literal, TypedDict

from pydantic import JsonValue


class AuthenticatedUser(TypedDict):
    id: str
    username: str
    email: str
    avatar: str | None
    is_admin: bool
    preferences: dict[str, JsonValue] | None
    created_at: str | None
    last_login: str | None
    token_id: str | None
    session_id: str


class TokenClaims(TypedDict):
    sub: str
    user_id: str
    jti: str
    sid: str
    type: Literal["access", "refresh"]
    exp: int | float
    iat: int | float
