from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserPublic, UserProfile, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserPublic], summary="List users in org")
async def list_users(
    db: DBSession,
    current_user: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[UserPublic]:
    service = UserService(db)
    users, total = await service.list_users(
        current_user.org_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PaginatedResponse.create(
        items=[UserPublic.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserPublic, summary="Get user by ID")
async def get_user(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return UserPublic.model_validate(user)


@router.patch("/{user_id}", response_model=UserPublic, summary="Update user")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> UserPublic:
    service = UserService(db)
    user = await service.update_user(user_id, data, requesting_user=current_user)
    return UserPublic.model_validate(user)


@router.delete("/{user_id}", status_code=204, summary="Deactivate user")
async def deactivate_user(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: AdminUser,
) -> None:
    service = UserService(db)
    await service.deactivate_user(user_id, current_user)
