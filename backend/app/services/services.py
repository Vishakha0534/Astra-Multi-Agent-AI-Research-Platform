from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    JobAlreadyRunningError,
    JobNotCancellableError,
    NotFoundError,
    PermissionDeniedError,
    ProjectNotFoundError,
    ResearchJobNotFoundError,
    ReportNotFoundError,
    SourceNotFoundError,
)
from app.models.project import Project
from app.models.research_job import ResearchJob
from app.models.report import ResearchReport, Source
from app.models.agent_log import AgentLog
from app.models.user import User
from app.repositories.repositories import (
    AgentLogRepository,
    ProjectRepository,
    ReportRepository,
    ResearchJobRepository,
    SourceRepository,
)
from app.schemas.schemas import (
    AgentLogCreate,
    ProjectCreate,
    ProjectUpdate,
    ReportCreate,
    ReportUpdate,
    ResearchJobCreate,
    ResearchJobUpdate,
    SourceCreate,
)


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ProjectRepository(db)

    async def create(self, data: ProjectCreate, user: User) -> Project:
        return await self.repo.create({
            "name": data.name,
            "description": data.description,
            "owner_id": user.id,
            "org_id": user.org_id,
            "settings": data.settings,
            "status": "active",
        })

    async def get(self, project_id: uuid.UUID, user: User) -> Project:
        project = await self.repo.get(project_id)
        if not project or project.org_id != user.org_id:
            raise ProjectNotFoundError()
        return project

    async def list(self, user: User, *, offset: int = 0, limit: int = 20) -> tuple[list[Project], int]:
        projects = await self.repo.list_by_owner(user.id, org_id=user.org_id, offset=offset, limit=limit)
        total = await self.repo.count_by_owner(user.id, user.org_id)
        return projects, total

    async def update(self, project_id: uuid.UUID, data: ProjectUpdate, user: User) -> Project:
        project = await self.get(project_id, user)
        if project.owner_id != user.id and user.role != "admin":
            raise PermissionDeniedError()
        return await self.repo.update(project, data.model_dump(exclude_unset=True))

    async def delete(self, project_id: uuid.UUID, user: User) -> None:
        project = await self.get(project_id, user)
        if project.owner_id != user.id and user.role != "admin":
            raise PermissionDeniedError()
        await self.repo.update(project, {"status": "deleted"})


class ResearchJobService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ResearchJobRepository(db)
        self.project_repo = ProjectRepository(db)

    async def create(self, data: ResearchJobCreate, user: User) -> ResearchJob:
        # Validate project ownership
        project = await self.project_repo.get(data.project_id)
        if not project or project.org_id != user.org_id:
            raise ProjectNotFoundError()

        if await self.repo.has_running_job(data.project_id):
            raise JobAlreadyRunningError()

        return await self.repo.create({
            "title": data.title,
            "query": data.query,
            "project_id": data.project_id,
            "user_id": user.id,
            "org_id": user.org_id,
            "status": "pending",
            "completion_percent": 0,
            "total_tokens_used": 0,
            "total_cost_usd": Decimal("0"),
            "token_budget": data.token_budget,
        })

    async def get(self, job_id: uuid.UUID, user: User) -> ResearchJob:
        job = await self.repo.get(job_id)
        if not job or job.org_id != user.org_id:
            raise ResearchJobNotFoundError()
        return job

    async def list(
        self,
        project_id: uuid.UUID,
        user: User,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ResearchJob], int]:
        jobs = await self.repo.list_by_project(
            project_id, user.org_id, offset=offset, limit=limit, status=status
        )
        total = await self.repo.count_by_project(project_id, user.org_id, status=status)
        return jobs, total

    async def update_status(self, job_id: uuid.UUID, data: ResearchJobUpdate, user: User) -> ResearchJob:
        job = await self.get(job_id, user)
        update_data = data.model_dump(exclude_unset=True)
        if data.status == "researching" and not job.started_at:
            update_data["started_at"] = datetime.now(UTC)
        if data.status in ("completed", "failed", "cancelled"):
            update_data["completed_at"] = datetime.now(UTC)
        return await self.repo.update(job, update_data)

    async def cancel(self, job_id: uuid.UUID, user: User) -> ResearchJob:
        job = await self.get(job_id, user)
        cancellable = ("pending", "planning", "researching", "reviewing", "verifying", "generating")
        if job.status not in cancellable:
            raise JobNotCancellableError()
        return await self.repo.update(job, {"status": "cancelled", "completed_at": datetime.now(UTC)})


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportRepository(db)
        self.job_repo = ResearchJobRepository(db)

    async def create(self, data: ReportCreate, user: User) -> ResearchReport:
        job = await self.job_repo.get(data.job_id)
        if not job or job.org_id != user.org_id:
            raise ResearchJobNotFoundError()
        return await self.repo.create({
            "title": data.title,
            "job_id": data.job_id,
            "org_id": user.org_id,
            "content": data.content,
            "summary": data.summary,
            "status": "draft",
            "word_count": len((data.content or "").split()),
            "citation_count": 0,
        })

    async def get(self, report_id: uuid.UUID, user: User) -> ResearchReport:
        report = await self.repo.get(report_id)
        if not report or report.org_id != user.org_id:
            raise ReportNotFoundError()
        return report

    async def list(
        self,
        job_id: uuid.UUID,
        user: User,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ResearchReport], int]:
        reports = await self.repo.list_by_job(job_id, user.org_id, offset=offset, limit=limit)
        total = await self.repo.count_by_job(job_id, user.org_id)
        return reports, total

    async def update(self, report_id: uuid.UUID, data: ReportUpdate, user: User) -> ResearchReport:
        report = await self.get(report_id, user)
        update_data = data.model_dump(exclude_unset=True)
        if "content" in update_data and update_data["content"]:
            update_data["word_count"] = len(update_data["content"].split())
        return await self.repo.update(report, update_data)

    async def delete(self, report_id: uuid.UUID, user: User) -> None:
        report = await self.get(report_id, user)
        await self.repo.delete(report)


class SourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SourceRepository(db)
        self.job_repo = ResearchJobRepository(db)

    async def create_bulk(self, sources: list[SourceCreate], user: User) -> list[Source]:
        results = []
        for s in sources:
            created = await self.repo.create({
                "url": s.url,
                "title": s.title,
                "job_id": s.job_id,
                "org_id": user.org_id,
                "source_type": s.source_type,
                "tier": s.tier,
                "content_preview": s.content_preview,
                "relevance_score": s.relevance_score,
                "authors": s.authors,
                "year": s.year,
                "doi": s.doi,
                "extra_metadata": s.extra_metadata,
            })
            results.append(created)
        return results

    async def list(
        self,
        job_id: uuid.UUID,
        user: User,
        *,
        tier: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Source], int]:
        sources = await self.repo.list_by_job(job_id, user.org_id, tier=tier, offset=offset, limit=limit)
        total = await self.repo.count_by_job(job_id, user.org_id)
        return sources, total


class AgentLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AgentLogRepository(db)

    async def log(self, data: AgentLogCreate, user: User) -> AgentLog:
        return await self.repo.create({
            "job_id": data.job_id,
            "user_id": user.id,
            "org_id": user.org_id,
            "agent_name": data.agent_name,
            "model_id": data.model_id,
            "node_name": data.node_name,
            "level": data.level,
            "message": data.message,
            "input_tokens": data.input_tokens,
            "output_tokens": data.output_tokens,
            "cost_usd": data.cost_usd,
            "latency_ms": data.latency_ms,
            "is_fallback": data.is_fallback,
            "quality_score": data.quality_score,
            "extra_data": data.extra_data,
        })

    async def list(
        self,
        job_id: uuid.UUID,
        user: User,
        *,
        agent_name: str | None = None,
        level: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[AgentLog], int]:
        logs = await self.repo.list_by_job(
            job_id, user.org_id, agent_name=agent_name, level=level,
            offset=offset, limit=limit
        )
        total = await self.repo.count_by_job(job_id, user.org_id)
        return logs, total
