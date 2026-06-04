from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.research_job import ResearchJob
    from app.models.user import User


class Project(Base):
    """Research project container. Maps to the `projects` table."""

    __tablename__ = "projects"

    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_org_id", "org_id"),
        Index("ix_projects_status", "status"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Ownership ────────────────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # ─── State ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )

    # ─── Configuration ────────────────────────────────────────────────────────
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    research_jobs: Mapped[list["ResearchJob"]] = relationship(
        "ResearchJob",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
