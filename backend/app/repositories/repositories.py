from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.research_job import ResearchJob
from app.models.report import ResearchReport, Source
from app.models.agent_log import AgentLog
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Project, db)

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        *,
        org_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Project]:
        return await self.get_many(
            filters=[Project.owner_id == owner_id, Project.org_id == org_id],
            offset=offset,
            limit=limit,
        )

    async def count_by_owner(self, owner_id: uuid.UUID, org_id: uuid.UUID) -> int:
        return await self.count([Project.owner_id == owner_id, Project.org_id == org_id])


class ResearchJobRepository(BaseRepository[ResearchJob]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ResearchJob, db)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> list[ResearchJob]:
        filters = [
            ResearchJob.project_id == project_id,
            ResearchJob.org_id == org_id,
        ]
        if status:
            filters.append(ResearchJob.status == status)
        return await self.get_many(filters=filters, offset=offset, limit=limit)

    async def count_by_project(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        status: str | None = None,
    ) -> int:
        filters = [
            ResearchJob.project_id == project_id,
            ResearchJob.org_id == org_id,
        ]
        if status:
            filters.append(ResearchJob.status == status)
        return await self.count(filters)

    async def has_running_job(self, project_id: uuid.UUID) -> bool:
        running_statuses = ("pending", "planning", "researching", "reviewing", "verifying", "generating")
        result = await self.db.execute(
            select(ResearchJob).where(
                ResearchJob.project_id == project_id,
                ResearchJob.status.in_(running_statuses),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None


class ReportRepository(BaseRepository[ResearchReport]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ResearchReport, db)

    async def list_by_job(
        self,
        job_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ResearchReport]:
        return await self.get_many(
            filters=[ResearchReport.job_id == job_id, ResearchReport.org_id == org_id],
            offset=offset,
            limit=limit,
        )

    async def count_by_job(self, job_id: uuid.UUID, org_id: uuid.UUID) -> int:
        return await self.count([ResearchReport.job_id == job_id, ResearchReport.org_id == org_id])


class SourceRepository(BaseRepository[Source]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Source, db)

    async def list_by_job(
        self,
        job_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        tier: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Source]:
        filters = [Source.job_id == job_id, Source.org_id == org_id]
        if tier is not None:
            filters.append(Source.tier == tier)
        return await self.get_many(filters=filters, offset=offset, limit=limit)

    async def count_by_job(self, job_id: uuid.UUID, org_id: uuid.UUID) -> int:
        return await self.count([Source.job_id == job_id, Source.org_id == org_id])


class AgentLogRepository(BaseRepository[AgentLog]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AgentLog, db)

    async def list_by_job(
        self,
        job_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        agent_name: str | None = None,
        level: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AgentLog]:
        filters = [AgentLog.job_id == job_id, AgentLog.org_id == org_id]
        if agent_name:
            filters.append(AgentLog.agent_name == agent_name)
        if level:
            filters.append(AgentLog.level == level)
        return await self.get_many(
            filters=filters,
            order_by=AgentLog.created_at.asc(),
            offset=offset,
            limit=limit,
        )

    async def count_by_job(self, job_id: uuid.UUID, org_id: uuid.UUID) -> int:
        return await self.count([AgentLog.job_id == job_id, AgentLog.org_id == org_id])
