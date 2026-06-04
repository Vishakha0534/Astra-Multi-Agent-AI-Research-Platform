from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.research_job import ResearchJob
    from app.models.user import User


class AgentLog(Base):
    """Per-agent execution log entry. Maps to `agent_logs` (partitioned by week)."""

    __tablename__ = "agent_logs"

    __table_args__ = (
        Index("ix_agent_logs_job_id", "job_id"),
        Index("ix_agent_logs_org_id", "org_id"),
        Index("ix_agent_logs_agent_name", "agent_name"),
        Index("ix_agent_logs_level", "level"),
        Index("ix_agent_logs_created_at", "created_at"),
    )

    # ─── Ownership ────────────────────────────────────────────────────────────
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Agent Identity ───────────────────────────────────────────────────────
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    node_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ─── Log Entry ────────────────────────────────────────────────────────────
    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="INFO",
        server_default="INFO",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ─── Token & Cost Tracking ────────────────────────────────────────────────
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False, default=Decimal("0")
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ─── Execution Flags ──────────────────────────────────────────────────────
    is_fallback: Mapped[bool] = mapped_column(nullable=False, default=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    # ─── Structured Extras ────────────────────────────────────────────────────
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    job: Mapped["ResearchJob"] = relationship("ResearchJob", back_populates="agent_logs")
    user: Mapped["User"] = relationship("User", back_populates="agent_logs")
