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


class ResearchReport(Base):
    """Generated research report. Maps to the `research_reports` table."""

    __tablename__ = "research_reports"

    __table_args__ = (
        Index("ix_reports_job_id", "job_id"),
        Index("ix_reports_org_id", "org_id"),
        Index("ix_reports_status", "status"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Ownership ────────────────────────────────────────────────────────────
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Status ───────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # ─── Quality ──────────────────────────────────────────────────────────────
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ─── Structured Data ──────────────────────────────────────────────────────
    citations: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    key_findings: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    job: Mapped["ResearchJob"] = relationship("ResearchJob", back_populates="reports")


class Source(Base):
    """Evidence source discovered during research. Maps to the `sources` table."""

    __tablename__ = "sources"

    __table_args__ = (
        Index("ix_sources_job_id", "job_id"),
        Index("ix_sources_org_id", "org_id"),
        Index("ix_sources_tier", "tier"),
    )

    # ─── Identity ─────────────────────────────────────────────────────────────
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Ownership ────────────────────────────────────────────────────────────
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ─── Classification ───────────────────────────────────────────────────────
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="web",
        server_default="web",
    )
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)

    # ─── Quality Scores ───────────────────────────────────────────────────────
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    # ─── Metadata ─────────────────────────────────────────────────────────────
    authors: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    job: Mapped["ResearchJob"] = relationship("ResearchJob", back_populates="sources")
