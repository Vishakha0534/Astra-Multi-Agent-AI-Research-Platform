from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async CRUD repository.

    Provides create, get, update, delete, list, and count
    operations for any SQLAlchemy model.
    """

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by PK. Returns None if not found."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *,
        filters: list[Any] | None = None,
        order_by: Any | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        """Fetch multiple records with optional filtering and pagination."""
        stmt = select(self.model)
        if filters:
            stmt = stmt.where(*filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: list[Any] | None = None) -> int:
        """Return total count for a query — used for pagination."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = stmt.where(*filters)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Insert a new record and return the persisted instance."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()  # Flush to get DB-generated values (e.g., id, created_at)
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        """Apply a partial update to an existing instance."""
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Hard delete a record from the database."""
        await self.db.delete(instance)
        await self.db.flush()

    async def exists(self, filters: list[Any]) -> bool:
        """Return True if at least one record matches the given filters."""
        stmt = select(func.count()).select_from(self.model).where(*filters)
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0
