from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError as AstraValidationError,
)
from app.models.auth import ApiKey
from app.schemas.auth import ApiKeyCreateRequest, ApiKeyResponse


# ─── Key format: "astra_<prefix12>.<secret48>" ────────────────────────────────
_KEY_PREFIX_LENGTH = 12
_KEY_SECRET_LENGTH = 48


def _generate_raw_key() -> tuple[str, str, str]:
    """Generate a raw API key.

    Returns:
        (full_key, prefix, sha256_hash)
    """
    prefix = secrets.token_urlsafe(_KEY_PREFIX_LENGTH)[:_KEY_PREFIX_LENGTH]
    secret = secrets.token_urlsafe(_KEY_SECRET_LENGTH)
    full_key = f"astra_{prefix}.{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, f"astra_{prefix}", key_hash


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class ApiKeyService:
    """Manage API keys — create, validate, revoke, list."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Create ───────────────────────────────────────────────────────────────

    async def create_key(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: ApiKeyCreateRequest,
    ) -> tuple[ApiKey, str]:
        """Create a new API key.

        Returns:
            (ApiKey ORM object, plain_key_string)
            The plain key is ONLY available at this moment — store it safely.
        """
        full_key, prefix, key_hash = _generate_raw_key()

        api_key = ApiKey(
            name=payload.name,
            description=payload.description,
            key_prefix=prefix,
            key_hash=key_hash,
            user_id=user_id,
            org_id=org_id,
            scopes=payload.scopes,
            rate_limit_per_minute=payload.rate_limit_per_minute,
            expires_at=payload.expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key, full_key

    # ─── Validate ─────────────────────────────────────────────────────────────

    async def validate_key(self, raw_key: str) -> ApiKey:
        """Validate a raw API key and return the associated ApiKey record.

        Raises:
            AuthorizationError: If key is invalid, inactive, or expired.
        """
        if not raw_key.startswith("astra_"):
            raise AuthorizationError("Invalid API key format")

        key_hash = _hash_key(raw_key)
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise AuthorizationError("API key not found")
        if not api_key.is_active:
            raise AuthorizationError("API key has been revoked")
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
            raise AuthorizationError("API key has expired")

        # Bump usage counters (fire-and-forget; flush in caller)
        await self.db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key.id)
            .values(
                last_used_at=datetime.now(UTC),
                request_count=ApiKey.request_count + 1,
            )
        )
        return api_key

    # ─── List ─────────────────────────────────────────────────────────────────

    async def list_user_keys(self, user_id: uuid.UUID) -> list[ApiKey]:
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_org_keys(self, org_id: uuid.UUID) -> list[ApiKey]:
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.org_id == org_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    # ─── Revoke ───────────────────────────────────────────────────────────────

    async def revoke_key(
        self, key_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> ApiKey:
        """Revoke a key — only the owner or admin may do so."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise NotFoundError("API key not found")
        if api_key.user_id != requesting_user_id:
            raise AuthorizationError("Cannot revoke another user's API key")

        api_key.is_active = False
        self.db.add(api_key)
        await self.db.flush()
        return api_key

    async def admin_revoke_key(self, key_id: uuid.UUID) -> ApiKey:
        """Admin-level revocation (no ownership check)."""
        result = await self.db.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise NotFoundError("API key not found")
        api_key.is_active = False
        self.db.add(api_key)
        await self.db.flush()
        return api_key
