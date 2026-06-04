from __future__ import annotations

from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard HTTP security headers on every response."""

    _HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Cache-Control": "no-store",                       # API responses — never cache
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers[header] = value
        # Remove server fingerprint header
        response.headers.pop("server", None)
        return response


class SensitiveRouteLoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured event whenever a sensitive path is accessed."""

    _SENSITIVE_PREFIXES = (
        "/api/v1/auth/",
        "/api/v1/users/",
        "/api/v1/api-keys/",
        "/api/v1/admin/",
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        is_sensitive = any(
            request.url.path.startswith(prefix) for prefix in self._SENSITIVE_PREFIXES
        )
        response = await call_next(request)

        if is_sensitive:
            user_id = getattr(getattr(request.state, "user", None), "id", None)
            logger.info(
                "sensitive_route_accessed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                user_id=str(user_id) if user_id else None,
                ip=request.client.host if request.client else None,
            )
        return response
