from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.schemas import ResearchJobCreate, ResearchJobResponse, ResearchJobUpdate
from app.services.services import ResearchJobService

router = APIRouter()


@router.post("", response_model=ResearchJobResponse, status_code=201, summary="Create research job")
async def create_job(data: ResearchJobCreate, db: DBSession, current_user: CurrentUser) -> ResearchJobResponse:
    service = ResearchJobService(db)
    job = await service.create(data, current_user)
    return ResearchJobResponse.model_validate(job)


@router.get("", response_model=PaginatedResponse[ResearchJobResponse], summary="List research jobs")
async def list_jobs(
    db: DBSession,
    current_user: CurrentUser,
    project_id: uuid.UUID = Query(..., description="Filter by project"),
    status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ResearchJobResponse]:
    service = ResearchJobService(db)
    jobs, total = await service.list(
        project_id, current_user,
        status=status,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[ResearchJobResponse.model_validate(j) for j in jobs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{job_id}", response_model=ResearchJobResponse, summary="Get research job")
async def get_job(job_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> ResearchJobResponse:
    service = ResearchJobService(db)
    job = await service.get(job_id, current_user)
    return ResearchJobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=ResearchJobResponse, summary="Update job status/progress")
async def update_job(
    job_id: uuid.UUID, data: ResearchJobUpdate, db: DBSession, current_user: CurrentUser
) -> ResearchJobResponse:
    service = ResearchJobService(db)
    job = await service.update_status(job_id, data, current_user)
    return ResearchJobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=ResearchJobResponse, summary="Cancel a running job")
async def cancel_job(job_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> ResearchJobResponse:
    service = ResearchJobService(db)
    job = await service.cancel(job_id, current_user)
    return ResearchJobResponse.model_validate(job)
