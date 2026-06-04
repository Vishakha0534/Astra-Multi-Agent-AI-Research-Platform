from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.session import get_db
from app.middleware.rbac import CurrentUser, AdminUser, require_permission
from app.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    MessageResponse,
)
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def _svc(db: AsyncSession = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(db)


@router.post(
    "/",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key (plain key shown ONCE)",
)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: CurrentUser,
    svc: ApiKeyService = Depends(_svc),
):
    api_key, plain_key = await svc.create_key(
        user_id=current_user.id,
        org_id=current_user.org_id,
        payload=payload,
    )
    return ApiKeyCreateResponse(
        key=ApiKeyResponse.model_validate(api_key),
        plain_key=plain_key,
    )


@router.get(
    "/",
    response_model=list[ApiKeyResponse],
    summary="List your API keys",
)
async def list_my_api_keys(
    current_user: CurrentUser,
    svc: ApiKeyService = Depends(_svc),
):
    return await svc.list_user_keys(current_user.id)


@router.get(
    "/org",
    response_model=list[ApiKeyResponse],
    summary="List all org API keys (admin only)",
    dependencies=[Depends(require_permission(Permission.API_KEY_REVOKE))],
)
async def list_org_api_keys(
    current_user: AdminUser,
    svc: ApiKeyService = Depends(_svc),
):
    return await svc.list_org_keys(current_user.org_id)


@router.delete(
    "/{key_id}",
    response_model=MessageResponse,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: CurrentUser,
    svc: ApiKeyService = Depends(_svc),
):
    # Owners can revoke their own; admins handled separately below
    if current_user.role == "admin":
        await svc.admin_revoke_key(key_id)
    else:
        await svc.revoke_key(key_id, requesting_user_id=current_user.id)
    return MessageResponse(message="API key revoked")
