from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ApiKey(Base):
    """Hashed API key for programmatic access. Maps to `api_keys`."""

    __tablename__ = "api_keys"

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
        Index("ix_api_keys_is_active", "is_active"),
        UniqueConstraint("key_hash", name="uq_api_keys_hash"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ─── Key Storage (only hash is persisted) ─────────────────────────────────
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)   # e.g. "astra_abcd12"
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)     # SHA-256 hex

    # ─── Ownership ────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Access Control ───────────────────────────────────────────────────────
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )

    # ─── Usage Tracking ───────────────────────────────────────────────────────
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ─── Expiry ───────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserSession(Base):
    """Server-side session metadata. Maps to `user_sessions`."""

    __tablename__ = "user_sessions"

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_jti", "jti"),
        Index("ix_sessions_is_active", "is_active"),
    )

    # ─── Token Identity ───────────────────────────────────────────────────────
    jti: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)  # JWT ID
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # ─── Ownership ────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Device Info ──────────────────────────────────────────────────────────
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # ─── State ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditLog(Base):
    """Immutable security event log. Maps to `audit_logs`."""

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_org_id", "org_id"),
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_created_at", "created_at"),
        Index("ix_audit_ip_address", "ip_address"),
    )

    # ─── Actor ────────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ─── Event ────────────────────────────────────────────────────────────────
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # success / failure
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ─── Context ──────────────────────────────────────────────────────────────
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
