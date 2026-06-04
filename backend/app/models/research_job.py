from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent_log import AgentLog
    from app.models.project import Project
    from app.models.report import ResearchReport
    from app.models.source import Source
    from app.models.user import User


class ResearchJob(Base):
    """A single async research execution. Maps to the `research_jobs` table."""

    __tablename__ = "research_jobs"

    __table_args__ = (
        Index("ix_rjobs_project_id", "project_id"),
        Index("ix_rjobs_user_id", "user_id"),
        Index("ix_rjobs_org_id", "org_id"),
        Index("ix_rjobs_status", "status"),
        Index("ix_rjobs_created_at", "created_at"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # ─── Ownership ────────────────────────────────────────────────────────────
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Pipeline State ───────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completion_percent: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )

    # ─── Planner Output ───────────────────────────────────────────────────────
    orchestration_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    state_checkpoint: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ─── Quality & Cost ───────────────────────────────────────────────────────
    quality_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    total_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )
    token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ─── Timing ───────────────────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ─── Error Handling ───────────────────────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    human_review_required: Mapped[bool] = mapped_column(nullable=False, default=False)

    # ─── Relationships ────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship("Project", back_populates="research_jobs")
    user: Mapped["User"] = relationship("User", back_populates="research_jobs")
    reports: Mapped[list["ResearchReport"]] = relationship(
        "ResearchReport",
        back_populates="job",
        lazy="select",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list["Source"]] = relationship(
        "Source",
        back_populates="job",
        lazy="select",
        cascade="all, delete-orphan",
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog",
        back_populates="job",
        lazy="select",
        cascade="all, delete-orphan",
    )
