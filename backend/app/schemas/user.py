from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import AstraBaseSchema, IDMixin, TimestampMixin

UserRole = Literal["admin", "researcher", "viewer"]


# ─── Create ───────────────────────────────────────────────────────────────────

class UserCreate(AstraBaseSchema):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=256)
    role: UserRole = "researcher"
    org_id: uuid.UUID | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ─── Update ───────────────────────────────────────────────────────────────────

class UserUpdate(AstraBaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=256)
    role: UserRole | None = None
    is_active: bool | None = None


class UserPasswordChange(AstraBaseSchema):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ─── Read ─────────────────────────────────────────────────────────────────────

class UserPublic(IDMixin, TimestampMixin, AstraBaseSchema):
    """Safe user representation — no password hash exposed."""

    email: str
    username: str
    full_name: str
    role: str
    org_id: uuid.UUID
    is_active: bool
    is_verified: bool


class UserProfile(UserPublic):
    """Extended user profile for the authenticated user's own view."""

    is_superuser: bool


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(AstraBaseSchema):
    email: EmailStr
    password: str


class TokenResponse(AstraBaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(AstraBaseSchema):
    refresh_token: str
