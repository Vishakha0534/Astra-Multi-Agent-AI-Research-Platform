from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def get_active_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower(),
                User.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        return await self.exists([User.email == email.lower()])

    async def username_exists(self, username: str) -> bool:
        return await self.exists([User.username == username.lower()])

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[User]:
        return await self.get_many(
            filters=[User.org_id == org_id],
            offset=offset,
            limit=limit,
        )

    async def count_by_org(self, org_id: uuid.UUID) -> int:
        return await self.count([User.org_id == org_id])
