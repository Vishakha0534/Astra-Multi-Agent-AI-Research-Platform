from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import AstraBaseSchema, IDMixin, TimestampMixin

ProjectStatus = Literal["active", "archived", "deleted"]
JobStatus = Literal[
    "pending", "planning", "researching", "reviewing",
    "verifying", "generating", "completed", "failed", "cancelled"
]
ReportStatus = Literal["draft", "review", "published"]
SourceType = Literal["web", "arxiv", "journal", "book", "preprint", "conference", "other"]


# ─── Project Schemas ─────────────────────────────────────────────────────────

class ProjectCreate(AstraBaseSchema):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    settings: dict[str, Any] | None = None


class ProjectUpdate(AstraBaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    status: ProjectStatus | None = None
    settings: dict[str, Any] | None = None


class ProjectResponse(IDMixin, TimestampMixin, AstraBaseSchema):
    name: str
    description: str | None
    owner_id: uuid.UUID
    org_id: uuid.UUID
    status: str
    settings: dict[str, Any] | None


# ─── Research Job Schemas ─────────────────────────────────────────────────────

class ResearchJobCreate(AstraBaseSchema):
    title: str = Field(min_length=1, max_length=512)
    query: str = Field(min_length=10, max_length=4000)
    project_id: uuid.UUID
    token_budget: int | None = Field(default=None, ge=1000, le=500000)


class ResearchJobUpdate(AstraBaseSchema):
    status: JobStatus | None = None
    current_node: str | None = None
    completion_percent: int | None = Field(default=None, ge=0, le=100)
    orchestration_plan: dict[str, Any] | None = None
    state_checkpoint: dict[str, Any] | None = None
    quality_score: Decimal | None = None
    total_tokens_used: int | None = None
    total_cost_usd: Decimal | None = None
    error_message: str | None = None
    human_review_required: bool | None = None


class ResearchJobResponse(IDMixin, TimestampMixin, AstraBaseSchema):
    title: str
    query: str
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    org_id: uuid.UUID
    status: str
    current_node: str | None
    completion_percent: int
    quality_score: Decimal | None
    total_tokens_used: int
    total_cost_usd: Decimal
    token_budget: int | None
    error_message: str | None
    human_review_required: bool
    started_at: Any | None
    completed_at: Any | None


# ─── Report Schemas ───────────────────────────────────────────────────────────

class ReportCreate(AstraBaseSchema):
    title: str = Field(min_length=1, max_length=512)
    job_id: uuid.UUID
    content: str | None = None
    summary: str | None = None


class ReportUpdate(AstraBaseSchema):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    status: ReportStatus | None = None
    quality_score: Decimal | None = None
    citations: dict[str, Any] | None = None
    key_findings: list[Any] | None = None
    recommendations: list[Any] | None = None


class ReportResponse(IDMixin, TimestampMixin, AstraBaseSchema):
    title: str
    summary: str | None
    job_id: uuid.UUID
    org_id: uuid.UUID
    status: str
    quality_score: Decimal | None
    word_count: int
    citation_count: int
    key_findings: list[Any] | None
    recommendations: list[Any] | None


class ReportDetailResponse(ReportResponse):
    content: str | None
    citations: dict[str, Any] | None
    metadata: dict[str, Any] | None


# ─── Source Schemas ───────────────────────────────────────────────────────────

class SourceCreate(AstraBaseSchema):
    url: str = Field(max_length=2048)
    title: str | None = Field(default=None, max_length=512)
    job_id: uuid.UUID
    source_type: SourceType = "web"
    tier: int = Field(default=2, ge=1, le=3)
    content_preview: str | None = None
    relevance_score: Decimal | None = None
    authors: list[Any] | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    doi: str | None = None
    extra_metadata: dict[str, Any] | None = None


class SourceResponse(IDMixin, AstraBaseSchema):
    url: str
    title: str | None
    job_id: uuid.UUID
    source_type: str
    tier: int
    relevance_score: Decimal | None
    quality_score: Decimal | None
    authors: list[Any] | None
    year: int | None
    doi: str | None
    created_at: Any


# ─── Agent Log Schemas ────────────────────────────────────────────────────────

class AgentLogCreate(AstraBaseSchema):
    job_id: uuid.UUID
    agent_name: str = Field(max_length=64)
    model_id: str | None = Field(default=None, max_length=128)
    node_name: str | None = Field(default=None, max_length=64)
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    message: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0"), ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    is_fallback: bool = False
    quality_score: Decimal | None = None
    extra_data: dict[str, Any] | None = None


class AgentLogResponse(IDMixin, AstraBaseSchema):
    job_id: uuid.UUID
    agent_name: str
    model_id: str | None
    node_name: str | None
    level: str
    message: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int | None
    is_fallback: bool
    quality_score: Decimal | None
    created_at: Any
