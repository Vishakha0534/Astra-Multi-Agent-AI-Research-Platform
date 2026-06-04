from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyExistsError,
    PermissionDeniedError,
    UserNotFoundError,
)
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserPublic,
    UserUpdate,
)


class UserService:
    """Business logic for user management and authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def create_user(self, data: UserCreate, org_id: uuid.UUID | None = None) -> User:
        if await self.repo.email_exists(data.email):
            raise EmailAlreadyExistsError()

        user_data = {
            "email": data.email.lower(),
            "username": data.username.lower(),
            "hashed_password": hash_password(data.password),
            "full_name": data.full_name,
            "role": data.role,
            "org_id": org_id or data.org_id or uuid.uuid4(),
            "is_active": True,
            "is_verified": False,
        }
        return await self.repo.create(user_data)

    async def authenticate(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_active_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError("Invalid email or password")

        extra_claims = {"role": user.role, "org_id": str(user.org_id)}
        access_token = create_access_token(str(user.id), extra=extra_claims)
        refresh_token = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_by_email(self, email: str) -> User:
        user = await self.repo.get_by_email(email)
        if not user:
            raise UserNotFoundError()
        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        data: UserUpdate,
        *,
        requesting_user: User,
    ) -> User:
        user = await self.get_by_id(user_id)

        # Only admin or the user themselves can update
        if requesting_user.id != user_id and requesting_user.role != "admin":
            raise PermissionDeniedError()

        # Only admins can change roles
        if data.role is not None and requesting_user.role != "admin":
            raise PermissionDeniedError("Only admins can change user roles")

        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(user, update_data)

    async def list_users(
        self,
        org_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        users = await self.repo.list_by_org(org_id, offset=offset, limit=limit)
        total = await self.repo.count_by_org(org_id)
        return users, total

    async def deactivate_user(self, user_id: uuid.UUID, requesting_user: User) -> User:
        if requesting_user.role != "admin" and requesting_user.id != user_id:
            raise PermissionDeniedError()
        user = await self.get_by_id(user_id)
        return await self.repo.update(user, {"is_active": False})
