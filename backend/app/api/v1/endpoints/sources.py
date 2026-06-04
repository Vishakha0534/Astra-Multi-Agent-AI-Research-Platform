from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.schemas import SourceCreate, SourceResponse
from app.services.services import SourceService

router = APIRouter()


@router.post("/bulk", response_model=list[SourceResponse], status_code=201, summary="Bulk create sources")
async def create_sources(
    sources: list[SourceCreate], db: DBSession, current_user: CurrentUser
) -> list[SourceResponse]:
    service = SourceService(db)
    created = await service.create_bulk(sources, current_user)
    return [SourceResponse.model_validate(s) for s in created]


@router.get("", response_model=PaginatedResponse[SourceResponse], summary="List sources for a job")
async def list_sources(
    db: DBSession,
    current_user: CurrentUser,
    job_id: uuid.UUID = Query(...),
    tier: Annotated[int | None, Query(ge=1, le=3)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaginatedResponse[SourceResponse]:
    service = SourceService(db)
    sources, total = await service.list(
        job_id, current_user, tier=tier,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return PaginatedResponse.create(
        items=[SourceResponse.model_validate(s) for s in sources],
        total=total, page=page, page_size=page_size,
    )
