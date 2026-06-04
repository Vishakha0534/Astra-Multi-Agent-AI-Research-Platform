from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Connection Pool ──────────────────────────────────────────────────────────

_pool: ConnectionPool | None = None
_client: Redis | None = None  # type: ignore[type-arg]


def get_redis_pool() -> ConnectionPool:
    """Return (or create) the global async Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _pool


def get_redis() -> Redis:  # type: ignore[type-arg]
    """Return a Redis client bound to the shared pool."""
    global _client
    if _client is None:
        _client = Redis(connection_pool=get_redis_pool())
    return _client


# ─── FastAPI Dependency ───────────────────────────────────────────────────────

async def get_redis_client() -> AsyncGenerator[Redis, None]:  # type: ignore[type-arg]
    """FastAPI dependency that yields a Redis client per request."""
    client = get_redis()
    try:
        yield client
    except RedisError as exc:
        logger.error("Redis operation failed", error=str(exc))
        raise


# ─── Health Check ─────────────────────────────────────────────────────────────

async def check_redis_connection() -> bool:
    """Ping Redis. Returns True if healthy."""
    try:
        client = get_redis()
        return await client.ping()  # type: ignore[return-value]
    except Exception as exc:
        logger.error("Redis health check failed", error=str(exc))
        return False


# ─── Lifecycle ───────────────────────────────────────────────────────────────

async def close_redis_connections() -> None:
    """Close all Redis connections — called on application shutdown."""
    global _pool, _client
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.aclose()
        _pool = None
    logger.info("Redis connection pool closed")


# ─── Cache Helpers ────────────────────────────────────────────────────────────

class RedisCache:
    """Thin async cache wrapper with type-safe get/set/delete operations."""

    def __init__(self, client: Redis) -> None:  # type: ignore[type-arg]
        self._client = client

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        if ttl_seconds:
            await self._client.setex(key, ttl_seconds, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns number of deleted keys."""
        keys = await self._client.keys(pattern)
        if not keys:
            return 0
        return await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self._client.expire(key, ttl_seconds)

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._client.incrby(key, amount)  # type: ignore[return-value]

    async def publish(self, channel: str, message: str) -> None:
        await self._client.publish(channel, message)
