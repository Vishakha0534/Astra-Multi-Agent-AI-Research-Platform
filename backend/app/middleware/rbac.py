from __future__ import annotations

"""RBAC dependency factories.

Usage in an endpoint:
    @router.get("/admin/stats")
    async def admin_stats(user: CurrentUser = Depends(require_permission(Permission.ADMIN_DASHBOARD))):
        ...
"""

from typing import Annotated

import structlog
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError, InvalidTokenError
from app.core.permissions import Permission, PermissionsEngine
from app.core.security import decode_token
from app.database.redis import get_redis_cache, RedisCache
from app.database.session import get_db
from app.models.user import User
from app.services.api_key_service import ApiKeyService
from app.services.token_manager import TokenManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# ─── Raw JWT extraction ───────────────────────────────────────────────────────


async def _get_jwt_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    cache: RedisCache = Depends(get_redis_cache),
) -> dict:
    """Extract and validate the JWT payload from the Authorization header."""
    if not credentials:
        raise AuthenticationError("Authorization header is missing")

    try:
        payload = decode_token(credentials.credentials)
    except InvalidTokenError:
        raise
    except Exception:
        raise AuthenticationError("Token is invalid or malformed")

    jti = payload.get("jti")
    if not jti:
        raise AuthenticationError("Token is missing required claims")

    # Check blocklist
    token_manager = TokenManager(cache)
    if await token_manager.is_jti_blocked(jti):
        raise AuthenticationError("Token has been revoked")

    return payload


# ─── Current user resolution ──────────────────────────────────────────────────


async def get_current_user(
    payload: dict = Depends(_get_jwt_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the JWT payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token is missing subject claim")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthenticationError("User account not found")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Attach claims to user object for convenience
    user._jti = payload.get("jti")  # type: ignore[attr-defined]
    return user


# ─── API Key authentication (alternative to JWT) ─────────────────────────────


async def get_current_user_or_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
) -> User:
    """Support both Bearer JWT and X-API-Key authentication."""
    if x_api_key:
        api_key_service = ApiKeyService(db)
        api_key_record = await api_key_service.validate_key(x_api_key)
        result = await db.execute(select(User).where(User.id == api_key_record.user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User associated with API key is inactive")
        user._api_key_scopes = api_key_record.scopes  # type: ignore[attr-defined]
        return user

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        try:
            payload = decode_token(token)
        except Exception:
            raise AuthenticationError("Invalid token")
        jti = payload.get("jti")
        token_manager = TokenManager(cache)
        if jti and await token_manager.is_jti_blocked(jti):
            raise AuthenticationError("Token has been revoked")
        result = await db.execute(select(User).where(User.id == payload.get("sub")))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return user

    raise AuthenticationError("Authentication credentials missing")


# ─── Permission guards ────────────────────────────────────────────────────────


def require_permission(permission: Permission):
    """FastAPI dependency factory that enforces a single permission."""

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if not PermissionsEngine.has_permission(user.role, permission):
            raise AuthorizationError(
                f"Your role '{user.role}' does not have permission: {permission.value}"
            )
        return user

    return _guard


def require_any_permission(*permissions: Permission):
    """Guard that passes if the user has ANY of the given permissions."""

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if not PermissionsEngine.has_any(user.role, *permissions):
            needed = ", ".join(p.value for p in permissions)
            raise AuthorizationError(
                f"Insufficient permissions. Requires any of: {needed}"
            )
        return user

    return _guard


def require_all_permissions(*permissions: Permission):
    """Guard that passes only if the user has ALL the given permissions."""

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if not PermissionsEngine.has_all(user.role, *permissions):
            needed = ", ".join(p.value for p in permissions)
            raise AuthorizationError(
                f"Insufficient permissions. Requires all of: {needed}"
            )
        return user

    return _guard


# ─── Role shortcuts ───────────────────────────────────────────────────────────


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.is_superuser:
        raise AuthorizationError("Admin access required")
    return user


async def require_researcher(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("researcher", "admin") and not user.is_superuser:
        raise AuthorizationError("Researcher access required")
    return user


# ─── Typed annotation aliases ─────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
ResearcherUser = Annotated[User, Depends(require_researcher)]
AnyAuthUser = Annotated[User, Depends(get_current_user_or_api_key)]
