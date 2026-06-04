from __future__ import annotations

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database.redis import get_redis_cache

logger = structlog.get_logger(__name__)

# ─── Rate limit rules (path_prefix → (requests, window_seconds)) ─────────────
_RATE_RULES: list[tuple[str, int, int]] = [
    ("/api/v1/auth/login", 10, 60),          # 10 req/min — brute force guard
    ("/api/v1/auth/register", 5, 60),         # 5 reg/min per IP
    ("/api/v1/auth/reset-password", 3, 300),  # 3 per 5-min
    ("/api/v1/", 300, 60),                    # Global default: 300 req/min
]


def _match_rule(path: str) -> tuple[int, int]:
    """Return (limit, window_seconds) for the best-matching rule."""
    for prefix, limit, window in _RATE_RULES:
        if path.startswith(prefix):
            return limit, window
    return 300, 60  # fallback


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter backed by Redis sorted sets.

    Key: ``ratelimit:{ip}:{path_prefix}``
    Algorithm: each request adds a member with score = current timestamp (ms).
    Stale members (outside the window) are pruned on each check.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health probes — no need to rate-limit k8s health checks
        if request.url.path in ("/api/v1/health/live", "/api/v1/health/ready"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        limit, window = _match_rule(path)

        try:
            cache = await get_redis_cache()
            allowed, remaining, reset_at = await self._check_sliding_window(
                cache._client, ip, path, limit, window
            )
        except Exception as exc:
            # Redis unavailable → fail open (don't block requests)
            logger.warning("rate_limit_redis_error", error=str(exc))
            return await call_next(request)

        response = await call_next(request)

        # Attach rate-limit headers (RFC-style)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_at)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {limit} requests per {window}s.",
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        return response

    @staticmethod
    async def _check_sliding_window(
        redis_client,
        ip: str,
        path: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """Returns (is_allowed, remaining_requests, reset_timestamp)."""
        now_ms = int(time.time() * 1000)
        window_ms = window * 1000
        key = f"ratelimit:{ip}:{path[:64]}"

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)  # prune stale
        pipe.zadd(key, {str(now_ms): now_ms})               # add current
        pipe.zcard(key)                                      # count in window
        pipe.expire(key, window)
        results = await pipe.execute()

        request_count = results[2]
        remaining = max(0, limit - request_count)
        reset_at = int(time.time()) + window
        is_allowed = request_count <= limit
        return is_allowed, remaining, reset_at
