from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import create_access_token, decode_token
from app.database.redis import RedisCache

# ─── Key prefixes (Redis namespace isolation) ────────────────────────────────
_PREFIX_REFRESH = "auth:refresh:"
_PREFIX_BLOCKLIST = "auth:blocklist:"
_PREFIX_EMAIL_VERIFY = "auth:email_verify:"
_PREFIX_PASSWORD_RESET = "auth:pwd_reset:"
_PREFIX_SESSION = "auth:session:"

# ─── TTLs (seconds) ──────────────────────────────────────────────────────────
_TTL_REFRESH = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
_TTL_EMAIL_VERIFY = 86400        # 24 h
_TTL_PASSWORD_RESET = 3600       # 1 h
_TTL_SESSION_IDLE = 1800         # 30 min idle expiry (rolling)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class TokenManager:
    """Manages all token lifecycle operations via Redis."""

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    # ─── Access Tokens ────────────────────────────────────────────────────────

    def create_access_token(
        self,
        user_id: uuid.UUID,
        role: str,
        org_id: uuid.UUID,
        jti: str | None = None,
    ) -> tuple[str, str]:
        """Create a signed JWT access token.

        Returns:
            (token_string, jti) where jti is the JWT ID claim.
        """
        jti = jti or str(uuid.uuid4())
        token = create_access_token(
            subject=str(user_id),
            extra={
                "role": role,
                "org_id": str(org_id),
                "jti": jti,
            },
        )
        return token, jti

    # ─── Refresh Tokens ───────────────────────────────────────────────────────

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        jti: str,
        session_id: str,
    ) -> str:
        """Create an opaque refresh token stored in Redis.

        The token itself is a random UUID; only its SHA-256 hash is stored.
        The Redis key maps refresh_token_hash → session_id.

        Args:
            user_id:    Owner of the token.
            jti:        The access token JTI this refresh token pairs with.
            session_id: DB session UUID for cross-referencing.

        Returns:
            Plain refresh token string (shown to client ONCE).
        """
        token = str(uuid.uuid4())
        token_hash = _sha256(token)

        payload = json.dumps({
            "user_id": str(user_id),
            "jti": jti,
            "session_id": session_id,
            "created_at": datetime.now(UTC).isoformat(),
        })
        await self._cache.set(f"{_PREFIX_REFRESH}{token_hash}", payload, ttl_seconds=_TTL_REFRESH)
        return token

    async def validate_refresh_token(self, token: str) -> dict[str, str]:
        """Validate an opaque refresh token.

        Returns:
            Payload dict with user_id, jti, session_id.

        Raises:
            InvalidTokenError: If token does not exist in Redis.
            TokenExpiredError: If token has been consumed or expired.
        """
        token_hash = _sha256(token)
        raw = await self._cache.get(f"{_PREFIX_REFRESH}{token_hash}")
        if not raw:
            raise TokenExpiredError("Refresh token expired or already used")
        return json.loads(raw)

    async def revoke_refresh_token(self, token: str) -> None:
        """Delete refresh token from Redis (logout / rotation)."""
        token_hash = _sha256(token)
        await self._cache.delete(f"{_PREFIX_REFRESH}{token_hash}")

    async def rotate_refresh_token(
        self,
        old_token: str,
        user_id: uuid.UUID,
        jti: str,
        session_id: str,
    ) -> str:
        """Atomically revoke old token and issue a new one (token rotation)."""
        await self.revoke_refresh_token(old_token)
        return await self.create_refresh_token(user_id, jti, session_id)

    # ─── Access Token Blocklist ───────────────────────────────────────────────

    async def blocklist_jti(self, jti: str, ttl_seconds: int) -> None:
        """Add a JWT ID to the blocklist (logout, password change, etc.)."""
        await self._cache.set(f"{_PREFIX_BLOCKLIST}{jti}", "1", ttl_seconds=ttl_seconds)

    async def is_jti_blocked(self, jti: str) -> bool:
        """Return True if the JTI has been revoked."""
        return await self._cache.exists(f"{_PREFIX_BLOCKLIST}{jti}")

    # ─── Email Verification Tokens ────────────────────────────────────────────

    async def create_email_verification_token(self, user_id: uuid.UUID) -> str:
        """Create a one-time email verification token."""
        token = str(uuid.uuid4())
        await self._cache.set(
            f"{_PREFIX_EMAIL_VERIFY}{token}",
            str(user_id),
            ttl_seconds=_TTL_EMAIL_VERIFY,
        )
        return token

    async def consume_email_verification_token(self, token: str) -> uuid.UUID:
        """Validate and consume (delete) an email verification token.

        Returns:
            user_id associated with the token.

        Raises:
            InvalidTokenError: If token is invalid or expired.
        """
        key = f"{_PREFIX_EMAIL_VERIFY}{token}"
        raw = await self._cache.get(key)
        if not raw:
            raise InvalidTokenError("Email verification link is invalid or has expired")
        await self._cache.delete(key)
        return uuid.UUID(raw)

    # ─── Password Reset Tokens ────────────────────────────────────────────────

    async def create_password_reset_token(self, user_id: uuid.UUID) -> str:
        """Create a short-lived password reset token."""
        token = str(uuid.uuid4())
        await self._cache.set(
            f"{_PREFIX_PASSWORD_RESET}{token}",
            str(user_id),
            ttl_seconds=_TTL_PASSWORD_RESET,
        )
        return token

    async def consume_password_reset_token(self, token: str) -> uuid.UUID:
        key = f"{_PREFIX_PASSWORD_RESET}{token}"
        raw = await self._cache.get(key)
        if not raw:
            raise InvalidTokenError("Password reset link is invalid or has expired")
        await self._cache.delete(key)
        return uuid.UUID(raw)

    # ─── Session Heartbeat ────────────────────────────────────────────────────

    async def touch_session(self, session_id: str) -> None:
        """Extend session idle TTL on each authenticated request."""
        await self._cache.expire(
            f"{_PREFIX_SESSION}{session_id}", _TTL_SESSION_IDLE
        )

    async def store_session_meta(self, session_id: str, meta: dict[str, Any]) -> None:
        """Persist lightweight session metadata in Redis for fast lookups."""
        await self._cache.set(
            f"{_PREFIX_SESSION}{session_id}",
            json.dumps(meta),
            ttl_seconds=_TTL_REFRESH,
        )

    async def get_session_meta(self, session_id: str) -> dict[str, Any] | None:
        raw = await self._cache.get(f"{_PREFIX_SESSION}{session_id}")
        return json.loads(raw) if raw else None

    async def invalidate_session(self, session_id: str) -> None:
        await self._cache.delete(f"{_PREFIX_SESSION}{session_id}")
