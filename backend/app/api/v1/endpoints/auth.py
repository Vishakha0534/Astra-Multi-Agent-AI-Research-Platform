from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.redis import get_redis_cache, RedisCache
from app.database.session import get_db
from app.middleware.rbac import CurrentUser, get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.session_manager import SessionManager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> str:
    # Respect X-Forwarded-For from reverse proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _auth_service(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
) -> AuthService:
    return AuthService(db, cache)


# ─── Registration ─────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    svc: AuthService = Depends(_auth_service),
):
    user = await svc.register(
        payload,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return user


# ─── Email Verification ───────────────────────────────────────────────────────


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address with one-time token",
)
async def verify_email(
    payload: VerifyEmailRequest,
    svc: AuthService = Depends(_auth_service),
):
    await svc.verify_email(payload.token)
    return MessageResponse(message="Email verified successfully")


# ─── Login ────────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access + refresh tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    svc: AuthService = Depends(_auth_service),
):
    return await svc.login(
        payload,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


# ─── Refresh ──────────────────────────────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue a new access token",
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    svc: AuthService = Depends(_auth_service),
):
    return await svc.refresh_tokens(
        payload.refresh_token,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


# ─── Logout ───────────────────────────────────────────────────────────────────


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke current session (or all devices)",
)
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: CurrentUser,
    svc: AuthService = Depends(_auth_service),
):
    jti = getattr(current_user, "_jti", None)
    if not jti:
        return MessageResponse(message="Logged out")

    await svc.logout(
        jti=jti,
        refresh_token=payload.refresh_token,
        user_id=current_user.id,
        all_devices=payload.all_devices,
        ip=_get_client_ip(request),
    )
    return MessageResponse(message="Logged out successfully")


# ─── Current User ─────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
async def get_me(current_user: CurrentUser):
    return current_user


# ─── Password Change ──────────────────────────────────────────────────────────


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the authenticated user's password",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser,
    svc: AuthService = Depends(_auth_service),
):
    await svc.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip=_get_client_ip(request),
    )
    return MessageResponse(message="Password changed. All sessions have been terminated.")


# ─── Password Reset ───────────────────────────────────────────────────────────


@router.post(
    "/reset-password/request",
    response_model=MessageResponse,
    summary="Request a password reset email (silent if email unknown)",
)
async def request_password_reset(
    payload: PasswordResetRequestSchema,
    svc: AuthService = Depends(_auth_service),
):
    await svc.request_password_reset(payload.email)
    # Always return same message to prevent email enumeration
    return MessageResponse(
        message="If that email is registered, a reset link has been sent."
    )


@router.post(
    "/reset-password/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset with one-time token",
)
async def confirm_password_reset(
    payload: PasswordResetConfirmSchema,
    svc: AuthService = Depends(_auth_service),
):
    await svc.reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password reset successfully. Please log in again.")


# ─── Sessions ─────────────────────────────────────────────────────────────────


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List all active sessions for the current user",
)
async def list_sessions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    mgr = SessionManager(db, cache)
    return await mgr.list_active_sessions(current_user.id)


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Revoke a specific session by ID",
)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis_cache),
):
    from sqlalchemy import select
    from app.models.auth import UserSession
    from app.core.exceptions import NotFoundError, AuthorizationError

    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")
    if session.user_id != current_user.id and current_user.role != "admin":
        raise AuthorizationError("Cannot revoke another user's session")

    mgr = SessionManager(db, cache)
    await mgr.revoke_session(session.jti)
    return MessageResponse(message="Session revoked")
