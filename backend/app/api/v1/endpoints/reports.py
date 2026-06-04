from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.schemas import ReportCreate, ReportResponse, ReportDetailResponse, ReportUpdate
from app.services.services import ReportService

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=201, summary="Create report")
async def create_report(data: ReportCreate, db: DBSession, current_user: CurrentUser) -> ReportResponse:
    service = ReportService(db)
    report = await service.create(data, current_user)
    return ReportResponse.model_validate(report)


@router.get("", response_model=PaginatedResponse[ReportResponse], summary="List reports for a job")
async def list_reports(
    db: DBSession,
    current_user: CurrentUser,
    job_id: uuid.UUID = Query(...),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ReportResponse]:
    service = ReportService(db)
    reports, total = await service.list(job_id, current_user, offset=(page - 1) * page_size, limit=page_size)
    return PaginatedResponse.create(
        items=[ReportResponse.model_validate(r) for r in reports],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportDetailResponse, summary="Get full report content")
async def get_report(report_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> ReportDetailResponse:
    service = ReportService(db)
    report = await service.get(report_id, current_user)
    return ReportDetailResponse.model_validate(report)


@router.patch("/{report_id}", response_model=ReportResponse, summary="Update report")
async def update_report(
    report_id: uuid.UUID, data: ReportUpdate, db: DBSession, current_user: CurrentUser
) -> ReportResponse:
    service = ReportService(db)
    report = await service.update(report_id, data, current_user)
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}", status_code=204, summary="Delete report")
async def delete_report(report_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> None:
    service = ReportService(db)
    await service.delete(report_id, current_user)
