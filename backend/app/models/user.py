from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent_log import AgentLog
    from app.models.project import Project
    from app.models.research_job import ResearchJob


class User(Base):
    """Platform user. Maps to the `users` table."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_email", "email"),
        Index("ix_users_org_id", "org_id"),
        Index("ix_users_is_active", "is_active"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)

    # ─── Organization & Role ──────────────────────────────────────────────────
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="researcher",
        server_default="researcher",
    )

    # ─── Status ───────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ─── Relationships ────────────────────────────────────────────────────────
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        lazy="select",
    )
    research_jobs: Mapped[list["ResearchJob"]] = relationship(
        "ResearchJob",
        back_populates="user",
        lazy="select",
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog",
        back_populates="user",
        lazy="select",
    )
