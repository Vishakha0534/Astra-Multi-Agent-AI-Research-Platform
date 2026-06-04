from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Validators ───────────────────────────────────────────────────────────────

_PASSWORD_RE = re.compile(
    r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&^#()_+=\-]).{8,128}$"
)


def _validate_password(v: str) -> str:
    if not _PASSWORD_RE.match(v):
        raise ValueError(
            "Password must be 8-128 characters and include: uppercase, lowercase, "
            "digit, and special character (@$!%*?&^#()_+=-)"
        )
    return v


# ─── Request Schemas ──────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_-]+$")]
    password: str
    full_name: Annotated[str, Field(min_length=2, max_length=256)]
    role: str = "researcher"
    org_id: uuid.UUID | None = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("admin", "researcher", "viewer"):
            raise ValueError("Role must be one of: admin, researcher, viewer")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
    all_devices: bool = False


class VerifyEmailRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password(v)


class ApiKeyCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=128)]
    description: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    rate_limit_per_minute: Annotated[int, Field(ge=1, le=1000)] = 60
    expires_at: datetime | None = None


# ─── Response Schemas ─────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    role: str
    org_id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    is_active: bool
    rate_limit_per_minute: int
    last_used_at: datetime | None
    request_count: int
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(BaseModel):
    """Returned ONCE at creation — plain key never shown again."""
    key: ApiKeyResponse
    plain_key: str


class SessionResponse(BaseModel):
    id: uuid.UUID
    jti: str
    ip_address: str | None
    user_agent: str | None
    device_name: str | None
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
    success: bool = True
