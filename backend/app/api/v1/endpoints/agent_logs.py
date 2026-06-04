from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.schemas import AgentLogCreate, AgentLogResponse
from app.services.services import AgentLogService

router = APIRouter()


@router.post("", response_model=AgentLogResponse, status_code=201, summary="Write agent log entry")
async def create_log(data: AgentLogCreate, db: DBSession, current_user: CurrentUser) -> AgentLogResponse:
    service = AgentLogService(db)
    log = await service.log(data, current_user)
    return AgentLogResponse.model_validate(log)


@router.get("", response_model=PaginatedResponse[AgentLogResponse], summary="Get agent logs for a job")
async def list_logs(
    db: DBSession,
    current_user: CurrentUser,
    job_id: uuid.UUID = Query(...),
    agent_name: Annotated[str | None, Query()] = None,
    level: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PaginatedResponse[AgentLogResponse]:
    service = AgentLogService(db)
    logs, total = await service.list(
        job_id, current_user,
        agent_name=agent_name, level=level,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return PaginatedResponse.create(
        items=[AgentLogResponse.model_validate(l) for l in logs],
        total=total, page=page, page_size=page_size,
    )
