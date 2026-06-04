from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class AstraBaseSchema(BaseModel):
    """Base schema with strict mode and ORM support."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


class IDMixin(BaseModel):
    id: uuid.UUID


# ─── Generic paginated response ──────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(AstraBaseSchema, Generic[T]):
    """Standard paginated list wrapper returned by all list endpoints."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        pages = max(1, (total + page_size - 1) // page_size)
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ─── Standard API response envelope ──────────────────────────────────────────

class SuccessResponse(AstraBaseSchema, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class ErrorDetail(AstraBaseSchema):
    field: str | None = None
    message: str


class ErrorResponse(AstraBaseSchema):
    success: bool = False
    error_code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None


# ─── Pagination query params ──────────────────────────────────────────────────

class PaginationParams(AstraBaseSchema):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
