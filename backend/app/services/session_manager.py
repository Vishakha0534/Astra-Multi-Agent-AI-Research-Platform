from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import UserSession
from app.database.redis import RedisCache


class SessionManager:
    """Manages server-side session records in PostgreSQL + Redis cache."""

    def __init__(self, db: AsyncSession, cache: RedisCache) -> None:
        self.db = db
        self.cache = cache

    async def create_session(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        jti: str,
        refresh_token_hash: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> UserSession:
        """Create a new session record in the DB and cache the metadata."""
        expires_at = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        session = UserSession(
            jti=jti,
            refresh_token_hash=refresh_token_hash,
            user_id=user_id,
            org_id=org_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            is_active=True,
            last_seen_at=datetime.now(UTC),
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        # Mirror in Redis for fast lookup
        await self.cache.store_session_meta(
            str(session.id),
            {
                "user_id": str(user_id),
                "org_id": str(org_id),
                "jti": jti,
                "ip": ip_address,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        return session

    async def get_session_by_jti(self, jti: str) -> UserSession | None:
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.jti == jti,
                UserSession.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def touch_session(self, session_id: uuid.UUID) -> None:
        """Update last_seen_at on the DB record (best-effort, async-safe)."""
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_seen_at=datetime.now(UTC))
        )
        await self.cache.touch_session(str(session_id))

    async def revoke_session(self, jti: str) -> None:
        """Mark a session as revoked by JTI."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.jti == jti)
        )
        session = result.scalar_one_or_none()
        if session:
            session.is_active = False
            session.revoked_at = datetime.now(UTC)
            self.db.add(session)
            await self.db.flush()
            await self.cache.invalidate_session(str(session.id))

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke all active sessions for a user (forced logout everywhere)."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,  # noqa: E712
            )
        )
        sessions = result.scalars().all()
        now = datetime.now(UTC)
        for s in sessions:
            s.is_active = False
            s.revoked_at = now
            self.db.add(s)
            await self.cache.invalidate_session(str(s.id))
        await self.db.flush()
        return len(sessions)

    async def list_active_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,  # noqa: E712
                UserSession.expires_at > datetime.now(UTC),
            ).order_by(UserSession.created_at.desc())
        )
        return list(result.scalars().all())
