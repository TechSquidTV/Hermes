"""Atomic Redis rate limits shared across API workers."""

import asyncio
import hashlib
import ipaddress
import socket
from typing import Awaitable, cast

from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger
from app.services.redis_progress import redis_progress_service

logger = get_logger(__name__)
_INCREMENT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


async def auth_client_ip(request: Request) -> str:
    """Use forwarded IPs only when the direct peer is an explicitly trusted proxy."""
    peer = request.client.host if request.client else "unavailable"
    trusted_addresses: set[str] = set()
    for host in settings.trusted_proxy_hosts:
        try:
            trusted_addresses.add(str(ipaddress.ip_address(host)))
        except ValueError:
            try:
                addresses = await asyncio.to_thread(
                    socket.getaddrinfo, host, 0, type=socket.SOCK_STREAM
                )
                trusted_addresses.update(
                    address[4][0]
                    for address in addresses
                    if isinstance(address[4][0], str)
                )
            except OSError:
                continue
    if peer not in trusted_addresses:
        return peer
    chain = request.headers.get("x-forwarded-for", "").split(",")
    for forwarded in reversed(chain):
        try:
            address = str(ipaddress.ip_address(forwarded.strip()))
        except ValueError:
            return peer
        if address not in trusted_addresses:
            return address
    return peer


async def limit_auth_requests(request: Request) -> None:
    if not settings.enable_rate_limiting:
        return
    client = await auth_client_ip(request)
    identity = hashlib.sha256(client.encode()).hexdigest()
    key = f"hermes:rate-limit:{request.url.path}:{identity}"
    try:
        redis = await redis_progress_service.get_async_redis()
        count, ttl = await cast(
            Awaitable[list[int]],
            redis.eval(
                _INCREMENT, 1, key, str(settings.login_attempt_window_minutes * 60)
            ),
        )
    except RedisError as error:
        logger.error("Authentication rate limiter unavailable", error=str(error))
        raise HTTPException(
            status_code=503, detail="Authentication temporarily unavailable"
        ) from error
    if count > settings.max_login_attempts:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(max(ttl, 1))},
        )
