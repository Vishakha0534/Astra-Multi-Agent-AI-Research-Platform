from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.services import ProjectService

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=201, summary="Create project")
async def create_project(data: ProjectCreate, db: DBSession, current_user: CurrentUser) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.create(data, current_user)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=PaginatedResponse[ProjectResponse], summary="List my projects")
async def list_projects(
    db: DBSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ProjectResponse]:
    service = ProjectService(db)
    projects, total = await service.list(current_user, offset=(page - 1) * page_size, limit=page_size)
    return PaginatedResponse.create(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project")
async def get_project(project_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.get(project_id, current_user)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse, summary="Update project")
async def update_project(
    project_id: uuid.UUID, data: ProjectUpdate, db: DBSession, current_user: CurrentUser
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.update(project_id, data, current_user)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204, summary="Archive project")
async def delete_project(project_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> None:
    service = ProjectService(db)
    await service.delete(project_id, current_user)
