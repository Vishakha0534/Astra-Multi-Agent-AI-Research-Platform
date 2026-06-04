from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, InvalidTokenError, PermissionDeniedError
from app.core.security import decode_token
from app.database.session import get_db
from app.database.redis import get_redis_client, RedisCache
from app.models.user import User
from app.repositories.user_repository import UserRepository
from redis.asyncio import Redis

# ─── HTTP Bearer extractor ────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode JWT, load user from DB, ensure they are active."""
    if not credentials:
        raise AuthenticationError("Authorization header missing")

    payload = decode_token(credentials.credentials)

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenError("Token subject missing")

    if payload.get("type") != "access":
        raise InvalidTokenError("Expected access token")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidTokenError("Invalid user ID in token")

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise InvalidTokenError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


# ─── Role-based guards ────────────────────────────────────────────────────────

async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user has the admin role."""
    if current_user.role != "admin" and not current_user.is_superuser:
        raise PermissionDeniedError("Admin role required")
    return current_user


async def require_researcher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user has at least the researcher role."""
    if current_user.role not in ("admin", "researcher") and not current_user.is_superuser:
        raise PermissionDeniedError("Researcher role required")
    return current_user


# ─── Convenience type aliases ─────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
ResearcherUser = Annotated[User, Depends(require_researcher)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis_client)]
